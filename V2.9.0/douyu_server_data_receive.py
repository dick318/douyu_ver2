#!/usr/bin/python3
# -*- coding: utf-8 -*-

# filename: douyu_server_data_receive.py
# version: 1.0.0
# date: 2017-12-01
# last date: 2018-11-13
# os: windows


import logging
import re
import socket
import time
from queue import Queue
from threading import Thread

import douyu_server_data_process as data_process


ABOUT = (u'Design by 枫轩\n'
         u'当前版本：2.8.1(2018-11-13)\n'
         u'联系方式：990761629(QQ)')

if __name__ == '__main__':
    LOG_FORMATTER = logging.Formatter(
        '[%(asctime)s][%(levelname)s]: <File: %(filename)s, ' +
        'Line: %(lineno)d, Func: %(funcName)s> %(message)s')    # 定义日志的输出格式
    WARNING_LOG = logging.FileHandler('WARNING.log')
    WARNING_LOG.setFormatter(LOG_FORMATTER)
    WARNING_FILTER = logging.Filter('WARNING')
    WARNING_LOG.addFilter(WARNING_FILTER)    
    ERROR_LOG = logging.FileHandler('ERROR.log')
    ERROR_LOG.setFormatter(LOG_FORMATTER)
    ERROR_FILTER = logging.Filter('ERROR')
    ERROR_LOG.addFilter(ERROR_FILTER)    
    PRINT_FORMATTER = logging.Formatter('%(message)s')
    PRINT_LOG = logging.StreamHandler()
    PRINT_LOG.setFormatter(PRINT_FORMATTER)
    LOGGER = logging.getLogger()
    LOGGER.addHandler(WARNING_LOG)
    LOGGER.addHandler(ERROR_LOG)
    LOGGER.addHandler(PRINT_LOG)
    
WARNING_LOGGER = logging.getLogger('WARNING')
ERROR_LOGGER = logging.getLogger('ERROR')
PRINT_LOGGER = logging.getLogger('PRINT')
PRINT_LOGGER.setLevel(logging.DEBUG)

def exception_message(exc):
    return str(exc.__class__.__name__) + ': ' + str(exc)

    
class GetDanmuServerData(object):    # 连接弹幕服务器并接收数据
    def __init__(self, queue_data, queue_recv_order=None, queue_send_order=None,
                 server='openbarrage.douyutv.com', port='8601', group='-9999'):
        self.queue_server_data = queue_data    # 存放来自弹幕服务器的数据，发送给数据处理线程
        self.queue_rid_order = queue_recv_order    # 接收来自主UI线程的直播间号或命令
        self.queue_send_order_except = queue_send_order    # 存放关闭命令或接收数据线程自身出现的异常消息，发送给处理数据线程
        
        self.roomid = ''    # 直播间号
        self.danmu_server = server    # 弹幕服务器名
        self.danmu_port = port    # 弹幕服务器端口
        self.danmu_group = group    # 弹幕组
        self.danmu_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.thread = Thread(target = self.start)    # 创建接收数据线程
        self.thread.setDaemon(True)
        self.islive = True    # 心跳线程运行控制，用于结束心跳线程
        self.send_live_time = 0

    def thread_start(self):
        self.thread.start()

    def start(self):
        if self.queue_rid_order:
            self.roomid = self.queue_rid_order.get(1)    # 获取来自主UI线程的直播间号
            data_queue = {
                'time': int(time.time()),
                'type': 'roomid',
                'rid': self.roomid
            }
            self.put_order_except(data_queue, 1)    # 将直播间号发送给处理线程
            self.put_server_data(data_queue, 1)            
        if self.connect_server(True):    # 连接弹幕服务器
            login_success = self.loginreq()    # 请求登录
            join_success = self.joingroup()    # 请求加入弹幕组
            if login_success and join_success:
                PRINT_LOGGER.debug('=' * 80)
                thread_keeplive = Thread(target = self.keeplive)    # 创建心跳线程
                thread_keeplive.setDaemon(True)
                thread_keeplive.start()
                self.receive_danmu_data()    # 进入接收数据循环
            else:
                self.client_close()
                if not login_success:
                    reason = u'登录直播间失败，重启中...'
                else:
                    reason = u'加入弹幕组失败，重启中...'
                tips = reason + u'(rid=%s)' % self.roomid
                exc_msg = '#' + tips
                WARNING_LOGGER.warning(exc_msg)
                PRINT_LOGGER.debug(tips)
                data_queue = {
                    'time': int(time.time()),
                    'type': 'exception',
                    'code': 'restart',
                    'reason': reason,
                    'rid': self.roomid
                }
                self.put_order_except(data_queue, 1)
                self.put_server_data(data_queue, 1)
                data_queue = {
                    'time': int(time.time()),
                    'type': 'close',
                    'from': 'GetDanmuServerData',
                    'rid': self.roomid
                }
                self.put_order_except(data_queue, 1)    # 通知处理数据线程结束线程
                self.put_server_data(data_queue, 1)
        else:
            PRINT_LOGGER.debug(u'已取消连接')

    def connect_server(self, send_error):    # 尝试连接弹幕服务器，失败则每10秒重试
        while True:
            PRINT_LOGGER.debug(u'开始连接...')            
            try:    # 出现异常则网络断开，每10秒重试一次连接
                socket.setdefaulttimeout(10)
                danmu_host = socket.gethostbyname(self.danmu_server)    # 获取弹幕服务器IP地址
                danmu_port = int(self.danmu_port)
                #socket.setdefaulttimeout(None)
                self.danmu_client.settimeout(10)    # 设置超时时间
                self.danmu_client.connect((danmu_host, danmu_port))    # 连接弹幕服务器
                self.danmu_client.settimeout(None)
                PRINT_LOGGER.debug(u'已连接弹幕服务器: (%s:%d)' % (danmu_host, danmu_port))
                return True
            except Exception as exc:
                if str(exc.__class__.__name__) == 'socket.timeout':
                    code = 'timeout'
                    reason = u'连接服务器超时，重新连接中...'
                else:
                    code = 'failed'
                    reason = u'连接服务器失败，重新连接中...'
                tips = reason + u'(10S后重试) (rid=%s)' % self.roomid
                exc_msg = exception_message(exc) + '#' + tips
                WARNING_LOGGER.warning(exc_msg)
                PRINT_LOGGER.debug(tips)
                if send_error:
                    send_error = False
                    data_queue = {
                        'time': int(time.time()),
                        'type': 'exception',
                        'code': code,
                        'reason': reason,
                        'rid': self.roomid
                    }
                    self.put_order_except(data_queue, 1)
                    self.put_server_data(data_queue, 1)
                for i in range(10):
                    if self.get_close_from_queue():
                        data_queue = {
                            'time': int(time.time()),
                            'type': 'close',
                            'from': 'GetDanmuServerData',
                            'rid': self.roomid
                        }
                        self.put_order_except(data_queue, 1)    # 通知处理数据线程结束线程
                        self.put_server_data(data_queue, 1)
                        return False    # 跳出循环，线束本线程
                    time.sleep(1)
                continue

    def receive_danmu_data(self):    # 接收来自弹幕服务器的数据，存放在队列中以发送给处理数据线程
        self.danmu_client.settimeout(1)    # 设置超时时间
        while True:
            if self.get_close_from_queue():
                self.logout()    # 登出弹幕服务器
                break    # 跳出循环，线束本线程
            try:    # 服务器断开连接会发生异常，发生异常则进行重连，并记录异常
                data_recv = self.danmu_client.recv(4096)    # 接收来自弹幕服务器的数据
            except socket.timeout as exc:
                pass
            except Exception as exc:
                tips = u'接收服务器数据时发生异常(rid=%s)' % self.roomid
                exc_msg = exception_message(exc) + '#' + tips
                WARNING_LOGGER.warning(exc_msg)
                PRINT_LOGGER.debug(tips)
                data_queue = {
                    'time': int(time.time()),
                    'type': 'exception',
                    'code': 'restart',
                    'reason': u'接收服务器数据时发生异常，重启中...',
                    'rid': self.roomid
                }    # 错误信息，进行重启
                self.put_order_except(data_queue, 1)    # 发送给处理数据线程，再由处理数据线程发送信息给主UI线程，以重新创建后台线程
                self.put_server_data(data_queue, 1)
                break    # 跳出循环，线束本线程
            else:
                if data_recv:
                    data_queue = {
                        'time': int(time.time()),
                        'type': 'message',
                        'data': data_recv,
                        'rid': self.roomid
                    }
                    self.put_server_data(data_queue, 1)    # 将接收的服务器数据放到队列中，以发送给处理数据线程
                else:
                    tips = u'接收到空的服务器数据(rid=%s)' % self.roomid
                    exc_msg = '#' + tips
                    WARNING_LOGGER.warning(exc_msg)
                    PRINT_LOGGER.debug(tips)
                    data_queue = {
                        'time': int(time.time()),
                        'type': 'exception',
                        'code': 'restart',
                        'reason': u'接收到空的服务器数据，重启中...',
                        'rid': self.roomid
                    }    # 错误信息，进行重连
                    self.put_order_except(data_queue, 1)    # 发送错误信息给处理数据线程，再由处理数据线程发送信息给主UI线程，以重新创建后台线程
                    self.put_server_data(data_queue, 1)
                    break
            if int(time.time()) - self.send_live_time >= 10:    # 每10秒发送一次程序内的心跳信息
                self.send_live_time = int(time.time())
                data_queue = {
                    'time': int(time.time()),
                    'type': 'live',
                    'rid': self.roomid
                }
                self.put_order_except(data_queue, 1)    # 发送给处理数据线程，再由处理数据线程发送信息给主UI线程，以重新创建后台线程
                self.put_server_data(data_queue, 1)                

        # 已跳出循环            
        self.islive = False    # 结束心跳线程
        #time.sleep(1)
        self.client_close()    # 关闭弹幕服务器连接
        data_queue = {
            'time': int(time.time()),
            'type': 'close',
            'from': 'GetDanmuServerData',
            'rid': self.roomid
        }
        self.put_order_except(data_queue, 1)    # 通知处理数据线程结束线程
        self.put_server_data(data_queue, 1)
        PRINT_LOGGER.debug('thread_GetDanmuServerData: closed!')

    def loginreq(self):    # 请求登录弹幕服务器
        msg_tosend = self.message_tosend('type@=loginreq/roomid@=%s/' % self.roomid)
        if self.client_send(msg_tosend):
            PRINT_LOGGER.debug(u'已登录直播间: %s' % self.roomid)
            return True
        else:
            return False

    def joingroup(self):    # 加入弹幕组
        msg_tosend = self.message_tosend(
            'type@=joingroup/rid@=%s/gid@=%s/' % (self.roomid, self.danmu_group))
        if self.client_send(msg_tosend):
            PRINT_LOGGER.debug(u'已加入弹幕组: %s' % self.danmu_group)
            return True
        else:
            return False

    def keeplive(self):    # 发送心跳消息，服务器在45s内没有收到心跳消息就会停止发送消息，并发送error消息: code=51
        #time_tosend = int(time.time())
        #msg_tosend = self.message_tosend(
        #    'type@=keeplive/tick@=' + str(time_tosend) + '/')    # 旧版心跳消息
        msg_keeplive = self.message_tosend('type@=mrkl/')    # 新版心跳消息
        while self.islive:
            self.client_send(msg_keeplive)
            n = 0
            while n <100 and self.islive:    # 每10秒发送一次心跳
                n += 1
                time.sleep(0.1)
        PRINT_LOGGER.debug('thread_keeplive: closed!')    # 已结束心跳线程

    def logout(self):    # 登出弹幕服务器
        msg_tosend = self.message_tosend('type@=logout/')
        if self.client_send(msg_tosend):
            PRINT_LOGGER.debug(u'已退出登录')

    def client_send(self, msg):    # 将信息发送给弹幕服务器
        try:    # 弹幕服务器断开连接会发生异常
            self.danmu_client.sendall(msg)
            return True
        except Exception as exc:
            try:
                time.sleep(1)
                self.danmu_client.sendall(msg)
                return True
            except Exception as exc:
                if str(exc.__class__.__name__) == 'socket.timeout':
                    reason = u'发送数据超时'
                else:
                    reason = u'发送数据时发生异常'
                tips = reason + u'(rid=%s)' % self.roomid
                exc_msg = exception_message(exc) + '#' + tips
                WARNING_LOGGER.warning(exc_msg)
                PRINT_LOGGER.debug(tips)
                self.client_close()
                return False

    def client_close(self):
        try:
            self.danmu_client.close()
            return True
        except Exception as exc:
            tips = u'关闭弹幕服务器连接时发生异常(rid=%s)' % self.roomid
            exc_msg = exception_message(exc) + '#' + tips
            WARNING_LOGGER.warning(exc_msg)
            PRINT_LOGGER.debug(tips)
            return False        

    def message_tosend(self, content_send):    # 将要发送给服务器的内容转换为协议格式，并转为字节码
        length = len(content_send) + 9
        msg_len = bytearray([length % 256, int(length % (256 ** 2) / 256),
                             int(length % (256 ** 3) / (256 ** 2)),
                             int(length / (256 ** 3))])
        head_len = msg_len
        head_code = bytearray([0xb1, 0x02, 0x00, 0x00])
        content_bytes = bytearray(content_send.encode('utf-8'))
        msg_end = bytearray([0x00])
        return bytes(msg_len + head_len + head_code + content_bytes + msg_end)

    def get_close_from_queue(self):
        if self.queue_rid_order and not self.queue_rid_order.empty():
            try:
                if self.queue_rid_order.get(0) == 'close': 
                    return True
                else:
                    return False
            except:
                return False

    def put_server_data(self, data, block=1):
        self.queue_server_data.put(data, block)

    def put_order_except(self, data, block=1):
        if self.queue_send_order_except:
            self.queue_send_order_except.put(data, block)
    

if __name__ == '__main__':    # 直接运行本程序，则在命令行中显示弹幕信息，无UI界面
    PRINT_LOGGER.debug(ABOUT)
    PRINT_LOGGER.debug('=' * 80)   
    PRINT_LOGGER.debug(u'设置直播间号：')
    while True:
        rid = input()    # 获取用户输入的直播间号
        if rid.isdigit():    # 判断输入是否正确的直播间号
            break
        else:
            PRINT_LOGGER.debug(u'直播间号错误！请重新输入：')
            continue
        
    msg_queue = Queue()    # 本接收线程和处理数据线程间的信息队列

    while True:    # 线程发生异常则进行重连
        get_msg = GetDanmuServerData(msg_queue)    # 创建接收数据线程实例
        process_msg = data_process.ProcessDanmuServerData(msg_queue)    # 创建处理数据线程实例
        get_msg.roomid = rid

        process_msg.thread_start()
        get_msg.start()

