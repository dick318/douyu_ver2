#!usr/bin/python3
# -*- coding: utf-8 -*-

# filename: douyu_server_data_process.py
# version: 1.0.0
# date: 2017-12-02
# last date: 2018-11-13
# os: windows


import logging
import re
import time
from queue import Queue
from threading import Thread, Lock


WARNING_LOGGER = logging.getLogger('WARNING')
ERROR_LOGGER = logging.getLogger('ERROR')
PRINT_LOGGER = logging.getLogger('PRINT')
PRINT_LOGGER.setLevel(logging.DEBUG)

def exception_message(exc):
    return str(exc.__class__.__name__) + ': ' + str(exc)


ERROR_DICT = {'0': u'操作成功', '51': u'数据传输出错', '52': u'服务器关闭', '204': u'房间ID错误'}
CLIENT_TYPE_DICT = {'0': u'浏览器', '1': u'安卓端', '2': u'苹果端', '14': u'电脑端'}        
NOBLE_NAME_DICT = {
    '1': u'骑士', '2': u'子爵', '3': u'伯爵', '4': u'公爵',
    '5': u'国王', '6': u'皇帝', '7': u'游侠'
}
DESERVE_NAME_DICT = {'1': u'初级酬勤', '2': u'中级酬勤', '3': u'高级酬勤'}
GIFT_NAME_DICT = {
    '824': u'粉丝荧光棒', '519': u'呵呵', '520': u'稳', '192': u'赞', '714': u'怂',
    '193': u'弱鸡', '191': u'100鱼丸', '712': u'棒棒哒', '713': u'辣眼睛', '1117': u'没排面',
    '1118': u'有排面', '1027': u'药丸', '380': u'好人卡', '750': u'办卡', '195': u'飞机',
    '196': u'火箭', '1005': u'超级火箭'
}


class ProcessDanmuServerData(object):    # 处理从弹幕服务器接收到的各种信息数据
    def __init__(self, queue_server_data, queue_send_message=None,
                 queue_revc_order=None, queue_send_order=None):
        self.queue_recv_server_data = queue_server_data    # 接收来自接收数据线程的数据，则弹幕服务器的数据
        self.queue_send_message_data = queue_send_message    # 存放处理分析得到的数据，发送给主UI线程
        self.queue_recv_order_except = queue_revc_order    # 接收来自接收数据线程的关闭命令或程序异常消息
        self.queue_send_order_except = queue_send_order    # 存放发送给主UI线程的关闭命令或程序异常消息
        
        self.msg_buf = ''    # 储存不完整的消息 
        self.buf_isnull = True    # 标志是否存在不完整的消息
        self.keeplive_time = time.time()    # 记录上次发送给主UI线程心跳消息的时间
        self.roomid = ''
        
        self.show_function = {
            'loginres': self.recv_loginres,
            'keeplive': self.recv_keeplive,
            'mrkl': self.recv_keeplive,
            'chatmsg': self.show_chatmsg,
            'uenter': self.show_uenter,
            'spbc': self.show_spbc,
            'bgbc': self.show_bgbc,
            'anbc': self.show_anbc,
            'newblackres': self.show_newblackres,
            'dgb': self.show_dgb,
            'bc_buy_deserve': self.show_deserve,
            'blab': self.show_blab,
            'rnewbc': self.show_rnewbc,
            'rss': self.show_rss,
            'error': self.show_error,
            'cthn': self.show_cthn,
            'ssd': self.show_ssd,
            'ranklist': self.show_ranklist,
            'frank': self.show_frank,
            'fswrank': self.show_frank,
            'noble_num_info': self.show_noble_num_info,
            'online_noble_list': self.show_online_noble_list,
            'setadminres': self.show_setadminres,
        }
        self.thread = Thread(target = self.start)    # 创建处理数据线程
        self.thread.setDaemon(True)

    def thread_start(self):    # 开启线程
        self.thread.start()
        
    def start(self):
        while True:
            server_data_recv = self.recv_server_data()    # 获取来自接收线程的数据
            order_except_recv = self.recv_order_except()
            if order_except_recv:
                order_except = order_except_recv['data']
                if order_except['type'] == 'roomid':
                    self.roomid = order_except['rid']
                elif order_except['type'] == 'closeThread':    # 收到结束线程的指令
                    break    # 跳出循环，结束本线程
                elif order_except['type'] in ('exception', 'threadlive'):    # 收到接收线程发生异常的消息或程序内心跳信息
                    self.send_order_except(order_except)
                
            if server_data_recv and server_data_recv['data']['type'] == 'serverData':
                server_data = server_data_recv['data']
                msg_recv_bytes = server_data['data']
                if not self.buf_isnull:    # 存在缓存数据，缓存数据与刚接收的数据合起来
                    msg_recv_bytes = self.msg_buf + msg_recv_bytes

                msg_list = re.findall(b'\xb2\x02\x00\x00.+?\x00', msg_recv_bytes)    # 获取完整消息
                if msg_list:    # 有完整的消息
                    for msg_single in msg_list:    # 逐条消息处理
                        try:
                            # 消息内容转换为unicode字符，'type'可能不在开头，加'/'方便提取msg_type
                            msg_utf8 = '/' + msg_single[4:-1].decode('utf-8', 'ignore') 
                        except Exception as exc:
                            exc_msg = exception_message(exc)
                            ERROR_LOGGER.error(exc_msg)
                            ERROR_LOGGER.error(msg_single)
                            continue
                        else:
                            self.parse_msg_utf8({'time': server_data['time'], 'data': msg_utf8})

                    if msg_recv_bytes.endswith(b'\x00'):    # 判断尾部是否有不完整消息，有则缓存
                        self.msg_buf = ''
                        self.buf_isnull = True
                    else:
                        self.msg_buf = msg_recv_bytes[msg_recv_bytes.rfind(b'\xb2\x02\x00\x00'):]
                        self.buf_isnull = False
                        #PRINT_LOGGER.debug(self.msg_buf)
                else:
                    self.msg_buf = msg_recv_bytes
                    self.buf_isnull = False
        # 已跳出循环，发送给主UI线程已结束线程的消息
        #time.sleep(0.5)
        data_send = {
            'time': int(time.time()),
            'type': 'closeThread',
        }
        self.send_order_except(data_send)
        PRINT_LOGGER.debug('thread_ProcessDanmuServerData: closed!')                

    def parse_msg_utf8(self, msg_dict):    # 提取消息类型，并调用不同的处理方法
        msg_utf8_str = msg_dict['data']
        if '/type@=' in msg_utf8_str:
            try:
                msg_type = re.search('/type@=(.*?)/', msg_utf8_str).group(1)
                #log_msg_parse(msg_utf8_str, ('ul_ranklist', ))                
            except Exception as exc:
                exc_msg = exception_message(exc)
                ERROR_LOGGER.error(exc_msg)
                ERROR_LOGGER.error(msg_utf8_str)
            else:
                if msg_type in self.show_function:    # 根据消息类型调用不同的方法
                    self.show_function[msg_type](msg_dict)
                #if msg_type not in ('chatmsg', 'uenter', 'dgb', 'online_noble_list', 'noble_num_info', 'ul_ranklist'):
                    #log_msg_parse(msg_utf8_str, (msg_type, ))

    def recv_loginres(self, loginres_msg):    # 接收到登录弹幕服务器成功的消息，提取数据发送给主UI线程
        try:
            PRINT_LOGGER.debug(u'连接直播间弹幕成功')
            data_send = {
                'time': loginres_msg['time'],
                'type': 'loginres',
                'rid': self.roomid
            }
            self.send_message_data(data_send)
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(loginres_msg)
                    
    def recv_keeplive(self, keeplive_msg):    # 若能接收到心跳消息，则给主UI线程发送心跳消息
        self.keeplive_time = int(time.time())
        try:
            #tick = re.search('/tick@=(.*?)/', keeplive_msg).group(1) if '/tick@=' in keeplive_msg else '0'    # 旧版心跳消息
            #PRINT_LOGGER.debug(keeplive_msg)
            data_send = {
                'time': keeplive_msg['time'],
                'type': 'keeplive',
                'delay': self.keeplive_time - keeplive_msg['time'],
                'rid': self.roomid
            }
            self.send_message_data(data_send)
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(keeplive_msg)
        
    def show_chatmsg(self, msg):    # 弹幕消息，提取弹幕消息中的数据
        try:
            time_int10 = msg['time']
            time_recv = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(msg['time']))
            mtype = re.search('/type@=(.*?)/', msg['data']).group(1) if '/type@=' in msg['data'] else ''
            rid = re.search('/rid@=(.*?)/', msg['data']).group(1) if '/rid@=' in msg['data'] else '0'    # 直播间号
            ct = re.search('/ct@=(.*?)/', msg['data']).group(1) if '/ct@=' in msg['data'] else '0'    # 客户端类型: 无-电脑浏览器，1-安卓端，2-苹果端，14-PC客户端，其它-未知            
            uid = re.search('/uid@=(.*?)/', msg['data']).group(1) if '/uid@=' in msg['data'] else '0'    # 用户ID
            nn = re.search('/nn@=(.*?)/', msg['data']).group(1) if '/nn@=' in msg['data'] else ''    # 用户名称
            txt = self.trans_char(re.search('/txt@=(.*?)/', msg['data']).group(1) if '/txt@=' in msg['data'] else '')    # 弹幕内容
            level = (re.search('/level@=(.*?)/', msg['data']).group(1) if '/level@=' in msg['data'] else '0')    # 用户等级
            nl = re.search('/nl@=(.*?)/', msg['data']).group(1) if '/nl@=' in msg['data'] else '0'    # 贵族等级
            col = re.search('/col@=(.*?)/', msg['data']).group(1) if '/col@=' in msg['data'] else '0'    # 弹幕颜色: 无-默认，1-21级红色，2-6级蓝色，3-9级绿色，4-15级橙色，5-18级紫色，6-12级粉色
            rg = re.search('/rg@=(.*?)/', msg['data']).group(1) if '/rg@=' in msg['data'] else '1'    # 房间权限组，普通用户rg=1，房管rg=4
            bnn = re.search('/bnn@=(.*?)/', msg['data']).group(1) if '/bnn@=' in msg['data'] else ''    # 粉丝牌名称
            bl = re.search('/bl@=(.*?)/', msg['data']).group(1) if '/bl@=' in msg['data'] else '0'    # 粉丝牌等级
            brid = re.search('/brid@=(.*?)/', msg['data']).group(1) if '/brid@=' in msg['data'] else '0'    # 粉丝牌直播间号
            
            noble_name = NOBLE_NAME_DICT[nl] if nl in NOBLE_NAME_DICT else ''    # 从字典中获得贵族名称            
            client_type = CLIENT_TYPE_DICT[ct] if ct in CLIENT_TYPE_DICT else u'未知'    # 从字典中获得客户端类型
            
            if noble_name:
                msg_show = u'%s [%s] [%s] [%s] %s: %s' % (time_recv, client_type, level, noble_name, nn, txt)
            else:
                msg_show = u'%s [%s] [%s] %s: %s' % (time_recv, client_type, level, nn, txt)
            PRINT_LOGGER.debug(msg_show)
            
            data_send = {
                'time': time_int10,
                'type': mtype,
                'rid': rid,
                'ct': ct,
                'uid': uid,
                'nn': nn,
                'txt': txt,
                'level': level,
                'nl': nl,
                'col': col,
                'rg': rg,                
                'bnn': bnn,
                'bl': bl,
                'brid': brid,
                'noble': noble_name,
                'client': client_type,
            }
            self.send_message_data(data_send)
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(msg)
            
    def show_uenter(self, msg):    # 用户进入直播间消息
        try:
            time_int10 = msg['time']
            time_recv = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(msg['time']))
            mtype = re.search('/type@=(.*?)/', msg['data']).group(1) if '/type@=' in msg['data'] else ''
            rid = re.search('/rid@=(.*?)/', msg['data']).group(1) if '/rid@=' in msg['data'] else '0'    # 直播间号
            uid = re.search('/uid@=(.*?)/', msg['data']).group(1) if '/uid@=' in msg['data'] else '0'    # 用户ID
            nn = re.search('/nn@=(.*?)/', msg['data']).group(1) if '/nn@=' in msg['data'] else ''    # 用户名称
            level = (re.search('/level@=(.*?)/', msg['data']).group(1) if '/level@=' in msg['data'] else '0')    # 用户等级
            rg = re.search('/rg@=(.*?)/', msg['data']).group(1) if '/rg@=' in msg['data'] else '1'    # 房间权限组，普通用户rg=1，房管rg=4
            nl = re.search('/nl@=(.*?)/', msg['data']).group(1) if '/nl@=' in msg['data'] else '0'    # 贵族等级            
            noble_name = NOBLE_NAME_DICT[nl] if nl in NOBLE_NAME_DICT else ''    # 从字典中获得贵族名称
            
            if noble_name:
                msg_show = u'%s [%s] [%s] %s 进入直播间' % (time_recv, level, noble_name, nn)
            else:
                msg_show = u'%s [%s] %s 进入直播间' % (time_recv, level, nn)
            PRINT_LOGGER.debug(msg_show)
            
            data_send = {
                'time': time_int10,
                'type': mtype,
                'rid': rid,
                'uid': uid,
                'nn': nn,
                'level': level,
                'rg': rg,
                'nl': nl,
                'noble': noble_name,                 
            }
            self.send_message_data(data_send)
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(msg)           

    def show_newblackres(self, msg):    # 禁言消息
        try:
            time_int10 = msg['time']
            time_recv = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(msg['time']))
            mtype = re.search('/type@=(.*?)/', msg['data']).group(1) if '/type@=' in msg['data'] else ''
            rid = re.search('/rid@=(.*?)/', msg['data']).group(1) if '/rid@=' in msg['data'] else '0'    # 直播间号
            otype = re.search('/otype@=(.*?)/', msg['data']).group(1) if '/otype@=' in msg['data'] else '0'    # 操作者类型：0-普通用户，1-房管，2-主播，3-超管
            sid = re.search('/sid@=(.*?)/', msg['data']).group(1) if '/sid@=' in msg['data'] else '0'    # 房管ID
            did = re.search('/did@=(.*?)/', msg['data']).group(1) if '/did@=' in msg['data'] else '0'    # 被禁言用户ID           
            snic = re.search('/snic@=(.*?)/', msg['data']).group(1) if '/snic@=' in msg['data'] else ''    # 房管名称
            dnic = re.search('/dnic@=(.*?)/', msg['data']).group(1) if '/dnic@=' in msg['data'] else ''    # 被禁言用户名称
            endtime = re.search('/endtime@=(.*?)/', msg['data']).group(1) if '/endtime@=' in msg['data'] else '0'    # 禁言结束时间
            time_end = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(endtime))) if endtime else ''
                        
            msg_show = u'%s %s 已被禁言(%s) 解禁时间: %s' % (time_recv, dnic, snic, time_end)
            PRINT_LOGGER.debug(msg_show)
            
            data_send = {
                'time': time_int10,
                'type': mtype,
                'rid': rid,
                'otype': otype,
                'sid': sid,
                'did': did,
                'snic': snic,
                'dnic': dnic,
                'endtime': time_end,
            }
            self.send_message_data(data_send)
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(msg)

    def show_blab(self, msg):    # 粉丝牌升级消息
        try:
            time_int10 = msg['time']
            time_recv = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(msg['time']))
            mtype = re.search('/type@=(.*?)/', msg['data']).group(1) if '/type@=' in msg['data'] else ''
            uid = re.search('/uid@=(.*?)/', msg['data']).group(1) if '/uid@=' in msg['data'] else '0'    # 用户ID
            nn = re.search('/nn@=(.*?)/', msg['data']).group(1) if '/nn@=' in msg['data'] else ''    # 用户名称
            lbl = re.search('/lbl@=(.*?)/', msg['data']).group(1) if '/lbl@=' in msg['data'] else '0'    # 粉丝牌升级前等级
            bl = re.search('/bl@=(.*?)/', msg['data']).group(1) if '/bl@=' in msg['data'] else '0'    # 粉丝牌升级后等级
            ba = re.search('/ba@=(.*?)/', msg['data']).group(1) if '/ba@=' in msg['data'] else '0'    # 广播区域字段
            bnn = re.search('/bnn@=(.*?)/', msg['data']).group(1) if '/bnn@=' in msg['data'] else ''    # 粉丝牌名称
            rid = re.search('/rid@=(.*?)/', msg['data']).group(1) if '/rid@=' in msg['data'] else '0'    # 直播间号
            
            msg_show = u'%s %s 粉丝等级升级到 [%s %s]' % (time_recv, nn, bl, bnn)
            PRINT_LOGGER.debug(msg_show)
            
            data_send = {
                'time': time_int10,
                'type': mtype,
                'uid': uid,
                'nn': nn,
                'lbl': lbl,
                'bl': bl,
                'ba': ba,
                'bnn': bnn,
                'rid': rid,
            }
            self.send_message_data(data_send)
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(msg)

    def show_setadminres(self, msg):    # 任免房管消息
        try:
            time_int10 = msg['time']
            time_recv = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(msg['time']))
            mtype = re.search('/type@=(.*?)/', msg['data']).group(1) if '/type@=' in msg['data'] else ''
            rescode = re.search('/rescode@=(.*?)/', msg['data']).group(1) if '/rescode@=' in msg['data'] else '0'    # 未知字段
            userid = re.search('/userid@=(.*?)/', msg['data']).group(1) if '/userid@=' in msg['data'] else '0'    # 被任免的用户ID
            opuid = re.search('/opuid@=(.*?)/', msg['data']).group(1) if '/opuid@=' in msg['data'] else '0'    # 操作用户ID，可能是主播或房管：0-用户自己解除房管，主播ID-主播任免房管
            group = re.search('/group@=(.*?)/', msg['data']).group(1) if '/group@=' in msg['data'] else '1'    # 用户权限组：1-解除房管，4-任命房管
            adnick = re.search('/adnick@=(.*?)/', msg['data']).group(1) if '/adnick@=' in msg['data'] else ''    # 被任免的用户名称
            rid = re.search('/rid@=(.*?)/', msg['data']).group(1) if '/rid@=' in msg['data'] else '0'    # 直播间号
            level = re.search('/level@=(.*?)/', msg['data']).group(1) if '/level@=' in msg['data'] else '0'    # 被任免的用户等级

            if group == '1':
                if opuid == '0':
                    msg_show = u'%s %s 自己解除房管' % (time_recv, adnick)
                else:
                    msg_show = u'%s %s 被解除房管' % (time_recv, adnick)
            elif group == '4':
                msg_show = u'%s %s 被任命房管' % (time_recv, adnick)
            PRINT_LOGGER.debug(msg_show)
            
            data_send = {
                'time': time_int10,
                'type': mtype,
                'rescode': rescode,
                'userid': userid,
                'opuid': opuid,
                'rgroup': group,
                'adnick': adnick,
                'rid': rid,
                'level': level,
            }
            self.send_message_data(data_send)            
            
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(msg)            

    def show_dgb(self, msg):    # 赠送礼物消息
        try:
            time_int10 = msg['time']
            time_recv = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(msg['time']))
            mtype = re.search('/type@=(.*?)/', msg['data']).group(1) if '/type@=' in msg['data'] else ''
            rid = re.search('/rid@=(.*?)/', msg['data']).group(1) if '/rid@=' in msg['data'] else '0'    # 直播间号
            gfid = re.search('/gfid@=(.*?)/', msg['data']).group(1) if '/gfid@=' in msg['data'] else '0'    # 礼物ID
            uid = re.search('/uid@=(.*?)/', msg['data']).group(1) if '/uid@=' in msg['data'] else '0'    # 用户ID
            bg = re.search('/bg@=(.*?)/', msg['data']).group(1) if '/bg@=' in msg['data'] else '0'    # 大礼物标识，无或0-小礼物 1-大礼物
            nn = re.search('/nn@=(.*?)/', msg['data']).group(1) if '/nn@=' in msg['data'] else ''    # 用户名称
            level = (re.search('/level@=(.*?)/', msg['data']).group(1) if '/level@=' in msg['data'] else '0')    # 用户等级
            gfcnt = re.search('/gfcnt@=(.*?)/', msg['data']).group(1) if '/gfcnt@=' in msg['data'] else '1'    # 一次批量赠送礼物数量
            hits = re.search('/hits@=(.*?)/', msg['data']).group(1) if '/hits@=' in msg['data'] else '1'    # 可连击时间内赠送礼物总数
            bcnt = re.search('/bcnt@=(.*?)/', msg['data']).group(1) if '/bcnt@=' in msg['data'] else '1'    # 批量赠送连击次数
            rg = re.search('/rg@=(.*?)/', msg['data']).group(1) if '/rg@=' in msg['data'] else '1'    # 房间权限组，普通用户rg=1，房管rg=4
            nl = re.search('/nl@=(.*?)/', msg['data']).group(1) if '/nl@=' in msg['data'] else '0'    # 贵族等级                        
            bnn = re.search('/bnn@=(.*?)/', msg['data']).group(1) if '/bnn@=' in msg['data'] else ''    # 粉丝牌名称
            bl = re.search('/bl@=(.*?)/', msg['data']).group(1) if '/bl@=' in msg['data'] else '0'    # 粉丝牌等级
            brid = re.search('/brid@=(.*?)/', msg['data']).group(1) if '/brid@=' in msg['data'] else '0'    # 粉丝牌直播间号
            
            noble_name = NOBLE_NAME_DICT[nl] if nl in NOBLE_NAME_DICT else ''    # 从字典中获得贵族名称        
            giftname = GIFT_NAME_DICT[gfid] if gfid in GIFT_NAME_DICT else gfid    # 从字典中获得礼物名称

            if gfcnt == '1':
                if hits == '0' or hits == '1':
                    if noble_name:
                        msg_show = u'%s [%s] [%s] %s 赠送给主播 %s' % (time_recv, level, noble_name, nn, giftname)
                    else:
                        msg_show = u'%s [%s] %s 赠送给主播 %s' % (time_recv, level, nn, giftname)
                elif int(hits)%10 == 0 or bg == '1':
                    if noble_name:
                        msg_show = u'%s [%s] [%s] %s 赠送给主播 %s %s连击' % (time_recv, level, noble_name, nn, giftname, hits)
                    else:
                        msg_show = u'%s [%s] %s 赠送给主播 %s %s连击' % (time_recv, level, nn, giftname, hits)
                else:
                    msg_show = None
            else:
                if noble_name:
                    msg_show = u'%s [%s] [%s] %s 赠送给主播 %s X%s' % (time_recv, level, noble_name, nn, giftname, gfcnt)
                else:
                    msg_show = u'%s [%s] %s 赠送给主播 %s X%s' % (time_recv, level, nn, giftname, gfcnt)                
                    
            if msg_show:
                PRINT_LOGGER.debug(msg_show)

            if gfcnt != '1' or bg == '1' or (hits == '1' or int(hits)%10 == 0):
                data_send = {
                    'time': time_int10,
                    'type': mtype,
                    'rid': rid,
                    'gfid': gfid,
                    'uid': uid,
                    'bg': bg,
                    'nn': nn,
                    'level': level,
                    'gfcnt': gfcnt,
                    'hits': hits,
                    'bcnt': bcnt,
                    'rg': rg,
                    'nl': nl,
                    'bnn': bnn,
                    'bl': bl,
                    'brid': brid,                    
                    'noble': noble_name,                    
                    'gn': giftname,
                }
                self.send_message_data(data_send)                
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(msg)

    def show_deserve(self, msg):    # 赠送酬勤消息
        try:
            time_int10 = msg['time']
            time_recv = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(msg['time']))
            mtype = re.search('/type@=(.*?)/', msg['data']).group(1) if '/type@=' in msg['data'] else ''
            uid = re.search('/sid@=(.*?)/', msg['data']).group(1) if '/sid@=' in msg['data'] else '0'    # 用户ID
            nn = re.search('@Snick@A=(.*?)@S', msg['data']).group(1) if '@Snick@A=' in msg['data'] else ''    # 用户名称 
            level = (re.search('/level@=(.*?)/', msg['data']).group(1) if '/level@=' in msg['data'] else '0')    # 用户等级        
            hits = re.search('/hits@=(.*?)/', msg['data']).group(1) if '/hits@=' in msg['data'] else '0'    # 连击数
            lev = re.search('/lev@=(.*?)/', msg['data']).group(1) if '/lev@=' in msg['data'] else '0'    # 酬勤等级：1-初级酬勤 2-中级酬勤 3-高级酬勤
            rid = re.search('/rid@=(.*?)/', msg['data']).group(1) if '/rid@=' in msg['data'] else '0'    # 直播间号
            bnn = re.search('/bnn@=(.*?)/', msg['data']).group(1) if '/bnn@=' in msg['data'] else ''    # 粉丝牌名称
            bl = re.search('/bl@=(.*?)/', msg['data']).group(1) if '/bl@=' in msg['data'] else '0'    # 粉丝牌等级
            brid = re.search('/brid@=(.*?)/', msg['data']).group(1) if '/brid@=' in msg['data'] else '0'    # 粉丝牌直播间号
            rg = re.search('/rg@=(.*?)/', msg['data']).group(1) if '/rg@=' in msg['data'] else '1'    # 房间权限组，普通用户rg=1，房管rg=4
            giftname = DESERVE_NAME_DICT[lev] if lev in DESERVE_NAME_DICT else ''    # 从字典中获得酬勤名称
            
            if hits == '0' or hits == '1':
                msg_show = u'%s [%s] %s %s 赠送给主播 %s' % (time_recv, level, noble_name, nn, giftname)
            else:
                msg_show = u'%s [%s] %s %s 赠送给主播 %s X%s' % (time_recv, level, noble_name, nn, giftname, hits)                
            PRINT_LOGGER.debug(msg_show)

            data_send = {
                'time': time_int10,
                'type': 'dgb',
                'rid': rid,
                'gfid': 'deserve',
                'uid': uid,
                'bg': '1',
                'nn': nn,
                'level': level,
                'hits': hits,
                'rg': rg,
                'nl': '0',
                'bnn': bnn,
                'bl': bl,
                'brid': brid,                    
                'noble': '',                    
                'gn': giftname,
            }
            self.send_message_data(data_send)
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(msg)
            
    def show_spbc(self, msg):    # 礼物广播消息
        try:
            time_int10 = msg['time']
            time_recv = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(msg['time']))
            mtype = re.search('/type@=(.*?)/', msg['data']).group(1) if '/type@=' in msg['data'] else ''
            sn = re.search('/sn@=(.*?)/', msg['data']).group(1) if '/sn@=' in msg['data'] else ''    # 赠送礼物用户名称
            dn = re.search('/dn@=(.*?)/', msg['data']).group(1) if '/dn@=' in msg['data'] else ''    # 受赠主播名称
            gn = re.search('/gn@=(.*?)/', msg['data']).group(1) if '/gn@=' in msg['data'] else ''    # 礼物名称
            gc = re.search('/gc@=(.*?)/', msg['data']).group(1) if '/gc@=' in msg['data'] else '1'    # 礼物数量
            drid = re.search('/drid@=(.*?)/', msg['data']).group(1) if '/drid@=' in msg['data'] else '0'    # 受赠直播间号            
            gb = re.search('/gb@=(.*?)/', msg['data']).group(1) if '/gb@=' in msg['data'] else '0'    # 是否有宝箱，0-无 1-有，已不可用
            es = re.search('/es@=(.*?)/', msg['data']).group(1) if '/es@=' in msg['data'] else '0'    # 广播展现样式，1-火箭 2-飞机 101-超级火箭
            gfid = re.search('/gfid@=(.*?)/', msg['data']).group(1) if '/gfid@=' in msg['data'] else '0'    # 礼物ID
            sid = re.search('/sid@=(.*?)/', msg['data']).group(1) if '/sid@=' in msg['data'] else '0'    # 赠送礼物用户ID
            
            msg_show = u'%s %s 赠送给 %s %s个 %s\n直播间: https://www.douyu.com/%s' % (time_recv, sn, dn, gc, gn, drid)
            PRINT_LOGGER.debug(msg_show)
            
            data_send = {
                'time': time_int10,
                'type': mtype,
                'sn': sn,
                'dn': dn,
                'gn': gn,
                'gc': gc,
                'drid': drid,
                'gb': gb,
                'es': es,                
                'gfid': gfid,
                'sid': sid,
            }
            self.send_message_data(data_send)
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(msg)

    def show_bgbc(self, msg):    # 批量礼物消息
        try:
            time_int10 = msg['time']
            time_recv = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(msg['time']))
            mtype = re.search('/type@=(.*?)/', msg['data']).group(1) if '/type@=' in msg['data'] else ''
            gfid = re.search('/gfid@=(.*?)/', msg['data']).group(1) if '/gfid@=' in msg['data'] else '0'    # 礼物ID
            gc = re.search('/gc@=(.*?)/', msg['data']).group(1) if '/gc@=' in msg['data'] else '1'    # 礼物数量
            drid = re.search('/drid@=(.*?)/', msg['data']).group(1) if '/drid@=' in msg['data'] else '0'    # 受赠直播间号
            sid = re.search('/sid@=(.*?)/', msg['data']).group(1) if '/sid@=' in msg['data'] else '0'    # 赠送礼物用户ID
            sn = re.search('/sn@=(.*?)/', msg['data']).group(1) if '/sn@=' in msg['data'] else ''    # 赠送礼物用户名称
            did = re.search('/did@=(.*?)/', msg['data']).group(1) if '/did@=' in msg['data'] else '0'    # 受赠主播ID
            dn = re.search('/dn@=(.*?)/', msg['data']).group(1) if '/dn@=' in msg['data'] else ''    # 受赠主播名称
            gn = re.search('/gn@=(.*?)/', msg['data']).group(1) if '/gn@=' in msg['data'] else ''    # 礼物名称
            
            msg_show = u'%s %s 赠送给 %s %s个 %s\n直播间: https://www.douyu.com/%s' % (time_recv, sn, dn, gc, gn, drid)
            PRINT_LOGGER.debug(msg_show)
            
            data_send = {
                'time': time_int10,
                'type': mtype,
                'gfid': gfid,
                'gc': gc,
                'drid': drid,
                'sid': sid,
                'sn': sn,
                'did': did,
                'dn': dn,
                'gn': gn,                               
            }
            self.send_message_data(data_send)
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(msg)
            
    def show_anbc(self, msg):    # 开通贵族消息
        try:
            time_int10 = msg['time']
            time_recv = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(msg['time']))
            mtype = re.search('/type@=(.*?)/', msg['data']).group(1) if '/type@=' in msg['data'] else ''
            uid = re.search('/uid@=(.*?)/', msg['data']).group(1) if '/uid@=' in msg['data'] else '0'    # 开通贵族用户ID
            unk = re.search('/unk@=(.*?)/', msg['data']).group(1) if '/unk@=' in msg['data'] else ''    # 开通贵族用户名称
            drid = re.search('/drid@=(.*?)/', msg['data']).group(1) if '/drid@=' in msg['data'] else '0'    # 受益主播直播间号
            donk = re.search('/donk@=(.*?)/', msg['data']).group(1) if '/donk@=' in msg['data'] else ''    # 受益主播名称
            gvnk = re.search('/gvnk@=(.*?)/', msg['data']).group(1) if '/gvnk@=' in msg['data'] else ''    # 赠送贵族用户名称
            nl = re.search('/nl@=(.*?)/', msg['data']).group(1) if '/nl@=' in msg['data'] else '0'    # 贵族等级：1-骑士 2-子爵 3-伯爵 4-公爵 5-国王 6-皇帝 7-游侠                        
            noble_name = NOBLE_NAME_DICT[nl] if nl in NOBLE_NAME_DICT else ''    # 从字典中获得贵族名称
            
            if ('gvnk@=' in msg['data']) and ('donk@=' in msg['data']):
                msg_show = (
                    u'%s %s 在 %s 的房间给 %s 开通了%s' % (time_recv, gvnk, donk, unk, noble_name) +
                    u'\n直播间: https://www.douyu.com/%s' % drid)
            elif ('gvnk@=' not in msg['data']) and ('donk@=' in msg['data']):
                msg_show = (
                    u'%s %s 在 %s 的房间开通了%s' % (time_recv, unk, donk, noble_name) +
                    u'\n直播间: https://www.douyu.com/%s' % drid)
            elif ('gvnk@=' in msg['data']) and ('donk@=' not in msg['data']):
                msg_show = u'%s %s 给 %s 开通了%s' % (time_recv, gvnk, unk, noble_name)
            else:
                msg_show = u'%s %s 开通了%s' % (time_recv, unk, noble_name)                
            PRINT_LOGGER.debug(msg_show)
            
            data_send = {
                'time': time_int10,
                'type': mtype,
                'uid': uid,
                'unk': unk,
                'drid': drid,                
                'donk': donk,
                'gvnk': gvnk,
                'nl': nl,
                'noble': noble_name,                
            }
            self.send_message_data(data_send)
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(msg)

    def show_rnewbc(self, msg):    # 续费贵族消息
        try:
            time_int10 = msg['time']
            time_recv = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(msg['time']))
            mtype = re.search('/type@=(.*?)/', msg['data']).group(1) if '/type@=' in msg['data'] else ''
            uid = re.search('/uid@=(.*?)/', msg['data']).group(1) if '/uid@=' in msg['data'] else '0'    # 续费贵族用户ID
            unk = re.search('/unk@=(.*?)/', msg['data']).group(1) if '/unk@=' in msg['data'] else ''    # 续费贵族用户名称
            drid = re.search('/drid@=(.*?)/', msg['data']).group(1) if '/drid@=' in msg['data'] else '0'    # 受益主播直播间号
            donk = re.search('/donk@=(.*?)/', msg['data']).group(1) if '/donk@=' in msg['data'] else ''    # 受益主播名称
            gvnk = re.search('/gvnk@=(.*?)/', msg['data']).group(1) if '/gvnk@=' in msg['data'] else ''    # 赠送贵族用户名称
            nl = re.search('/nl@=(.*?)/', msg['data']).group(1) if '/nl@=' in msg['data'] else '0'    # 贵族等级：1-骑士 2-子爵 3-伯爵 4-公爵 5-国王 6-皇帝 7-游侠                        
            noble_name = NOBLE_NAME_DICT[nl] if nl in NOBLE_NAME_DICT else ''    # 从字典中获得贵族名称
            
            if ('gvnk@=' in msg['data']) and ('donk@=' in msg['data']):
                msg_show = (
                    u'%s %s 在 %s 的房间给 %s 续费了%s' % (time_recv, gvnk, donk, unk, noble_name) +
                    u'\n直播间: https://www.douyu.com/%s' % drid)
            elif ('gvnk@=' not in msg['data']) and ('donk@=' in msg['data']):
                msg_show = (
                    u'%s %s 在 %s 的房间续费了%s' % (time_recv, unk, donk, noble_name) +
                    u'\n直播间: https://www.douyu.com/%s' % drid)
            elif ('gvnk@=' in msg['data']) and ('donk@=' not in msg['data']):
                msg_show = u'%s %s 给 %s 续费了%s' % (time_recv, gvnk, unk, noble_name)
            else:
                msg_show = u'%s %s 续费了%s' % (time_recv, unk, noble_name)
            PRINT_LOGGER.debug(msg_show)
            
            data_send = {
                'time': time_int10,
                'type': mtype,
                'uid': uid,
                'unk': unk,
                'drid': drid,                
                'donk': donk,
                'gvnk': gvnk,
                'nl': nl,
                'noble': noble_name,                
            }
            self.send_message_data(data_send)
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(msg)

    def show_cthn(self, msg):    # 喇叭消息
        try:
            time_int10 = msg['time']
            time_recv = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(msg['time']))
            mtype = re.search('/type@=(.*?)/', msg['data']).group(1) if '/type@=' in msg['data'] else ''
            rid = re.search('/rid@=(.*?)/', msg['data']).group(1) if '/rid@=' in msg['data'] else '0'    # 接收喇叭直播间号
            nl = re.search('/nl@=(.*?)/', msg['data']).group(1) if '/nl@=' in msg['data'] else '0'    # 贵族等级
            unk = re.search('/unk@=(.*?)/', msg['data']).group(1) if '/unk@=' in msg['data'] else ''    # 发喇叭用户名称
            drid = re.search('/drid@=(.*?)/', msg['data']).group(1) if '/drid@=' in msg['data'] else '0'    # 发喇叭直播间号
            onk = re.search('/onk@=(.*?)/', msg['data']).group(1) if '/onk@=' in msg['data'] else ''    # 发喇叭直播间主播名称
            chatmsg = re.search('/chatmsg@=(.*?)/', msg['data']).group(1) if '/chatmsg@=' in msg['data'] else ''    # 喇叭内容
            noble_name = NOBLE_NAME_DICT[nl] if nl in NOBLE_NAME_DICT else ''    # 从字典中获得贵族名称
            
            msg_show = u'%s %s: %s (%s)' % (time_recv, unk, chatmsg, onk)
            PRINT_LOGGER.debug(msg_show)
            
            data_send = {
                'time': time_int10,
                'type': mtype,
                'rid': rid,
                'nl': nl,                
                'unk': unk,
                'drid': drid,
                'onk': onk,
                'chatmsg': chatmsg,
                'noble': noble_name,
            }
            self.send_message_data(data_send)
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(msg)

    def show_ssd(self, msg):    # 超管广播消息
        try:
            time_int10 = msg['time']
            time_recv = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(msg['time']))
            mtype = re.search('/type@=(.*?)/', msg['data']).group(1) if '/type@=' in msg['data'] else ''
            content = re.search('/content@=(.*?)/', msg['data']).group(1) if '/content@=' in msg['data'] else ''    # 广播内容
            rid = re.search('/rid@=(.*?)/', msg['data']).group(1) if '/rid@=' in msg['data'] else '0'    # 接收广播直播间号
            trid = re.search('/trid@=(.*?)/', msg['data']).group(1) if '/trid@=' in msg['data'] else '0'    # 广播目标直播间号
            
            msg_show = u'%s %s' % (time_recv, content)
            PRINT_LOGGER.debug(msg_show)
            
            data_send = {
                'time': time_int10,
                'type': mtype,
                'content': content,
                'rid': rid,
                'trid': trid,                                
            }
            self.send_message_data(data_send)
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(msg)
            
    def show_rss(self, msg):    # 开关播消息
        try:
            time_int10 = msg['time']
            time_recv = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(msg['time']))
            mtype = re.search('/type@=(.*?)/', msg['data']).group(1) if '/type@=' in msg['data'] else ''
            rid = re.search('/rid@=(.*?)/', msg['data']).group(1) if '/rid@=' in msg['data'] else '0'    # 直播间号
            ss = re.search('/ss@=(.*?)/', msg['data']).group(1) if '/ss@=' in msg['data'] else '0'    # 直播状态：1-开播 0-关播

            if ss == '1':
                msg_show = u'%s %s 开播' % (time_recv, rid)
            else:
                msg_show = u'%s %s 关播' % (time_recv, rid)
            PRINT_LOGGER.debug(msg_show)
            
            data_send = {
                'time': time_int10,
                'type': mtype,
                'rid': rid,
                'ss': ss,                                
            }      
            self.send_message_data(data_send)
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(msg)
                
    def show_error(self, msg):    # 服务器错误消息
        try:
            time_int10 = msg['time']
            time_recv = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(msg['time']))
            mtype = re.search('/type@=(.*?)/', msg['data']).group(1) if '/type@=' in msg['data'] else ''
            error_code = re.search('/code@=(.*?)/', msg['data']).group(1) if '/code@=' in msg['data'] else ''    # 错误码
            error_str = ERROR_DICT[error_code] if error_code in ERROR_DICT else u'服务器内部异常'
            
            exc_msg = u'#%s %s: code=%s\n' % (time_recv, error_str,error_code)
            WARNING_LOGGER.warning(exc_msg)
            
            data_send = {
                'time': time_int10,
                'type': mtype,
                'code': error_code,
                'reason': error_str,
                'rid': self.roomid,
            }
            self.send_message_data(data_send)
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(msg)

    def show_ranklist(self, msg):    # 贡献榜信息
        try:
            time_int10 = msg['time']
            time_recv = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(msg['time']))
            mtype = re.search('/type@=(.*?)/', msg['data']).group(1) if '/type@=' in msg['data'] else ''
            rid = re.search('/rid@=(.*?)/', msg['data']).group(1) if '/rid@=' in msg['data'] else '0'    # 直播间号
            list = re.search('/list@=(.*?)/', msg['data']).group(1) if '/list@=' in msg['data'] else ''    # 周榜信息
            list_all = re.search('/list_all@=(.*?)/', msg['data']).group(1) if '/list_all@=' in msg['data'] else ''    # 总榜信息
            list_day = re.search('/list_day@=(.*?)/', msg['data']).group(1) if '/list_day@=' in msg['data'] else ''    # 日榜信息
            lists = []
            for li in (list, list_all, list_day):
                li = self.trans_char(li)
                ranklist = li.split('/')
                rank_users = []
                for user in ranklist:
                    if user:
                        user = '/' + self.trans_char(user)
                        uid = re.search('/uid@=(.*?)/', user).group(1) if '/uid@=' in user else '0'    # 用户ID
                        crk = re.search('/crk@=(.*?)/', user).group(1) if '/crk@=' in user else '0'    # 当前排名
                        lrk = re.search('/lrk@=(.*?)/', user).group(1) if '/lrk@=' in user else '0'    # 上次排名
                        rs = re.search('/rs@=(.*?)/', user).group(1) if '/rs@=' in user else '0'    # 排名变化
                        nickname = re.search('/nickname@=(.*?)/', user).group(1) if '/nickname@=' in user else ''    # 用户名称
                        gold = re.search('/gold@=(.*?)/', user).group(1) if '/gold@=' in user else '0'    # 用户贡献值
                        level = re.search('/level@=(.*?)/', user).group(1) if '/level@=' in user else '0'    # 用户等级
                        ne = re.search('/ne@=(.*?)/', user).group(1) if '/ne@=' in user else '0'    # 贵族等级
                        #icon = re.search('/icon@=(.*?)/', user).group(1) if '/icon@=' in user else ''    # 用户头像地址
                        #icon = self.trans_char(icon)
                        noble_name = NOBLE_NAME_DICT[ne] if ne in NOBLE_NAME_DICT else ''    # 从字典中获得贵族名称
                        rank_users.append({
                            'uid': uid, 'crk': crk, 'lrk': lrk, 'rs': rs, 'nickname': nickname,
                            'gold': gold, 'level': level, 'ne': ne, 'noble': noble_name
                        })
                lists.append(rank_users)                    

            data_send = {
                'time': time_int10,
                'type': mtype,
                'rid': rid,
                'list': lists[0],
                'list_all': lists[1],
                'list_day': lists[2],                
            }
            self.send_message_data(data_send)
            #PRINT_LOGGER.debug(data_send)
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(msg)

    def show_frank(self, msg):    # 粉丝团信息
        try:
            time_int10 = msg['time']
            time_recv = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(msg['time']))
            mtype = re.search('/type@=(.*?)/', msg['data']).group(1) if '/type@=' in msg['data'] else ''
            fc = re.search('/fc@=(.*?)/', msg['data']).group(1) if '/fc@=' in msg['data'] else '0'    # 粉丝总人数
            bnn = re.search('/bnn@=(.*?)/', msg['data']).group(1) if '/bnn@=' in msg['data'] else ''    # 粉丝牌名称
            list = re.search('/list@=(.*?)/', msg['data']).group(1) if '/list@=' in msg['data'] else ''    # 粉丝榜top10信息

            list = self.trans_char(list)
            flist = list.split('/')
            fans = []
            for user in flist:
                if user:
                    user = '/' + self.trans_char(user)
                    uid = re.search('/uid@=(.*?)/', user).group(1) if '/uid@=' in user else '0'    # 用户ID
                    nn = re.search('/nn@=(.*?)/', user).group(1) if '/nn@=' in user else ''    # 用户名称
                    fim = re.search('/fim@=(.*?)/', user).group(1) if '/fim@=' in user else '0'    # 亲密度
                    bl = re.search('/bl@=(.*?)/', user).group(1) if '/bl@=' in user else '0'    # 粉丝牌等级
                    lev = re.search('/lev@=(.*?)/', user).group(1) if '/lev@=' in user else '0'    # 用户等级
                    nl = re.search('/nl@=(.*?)/', user).group(1) if '/nl@=' in user else '0'    # 贵族等级
                    #ic = re.search('/ic@=(.*?)/', user).group(1) if '/ic@=' in user else ''    # 用户头像地址
                    #ic = self.trans_char(ic)
                    fans.append({'uid': uid, 'nn': nn, 'fim': fim, 'bl': bl, 'lev': lev, 'nl': nl})

            data_send = {
                'time': time_int10,
                'type': mtype,
                'fc': fc,
                'bnn': bnn,
                'list': fans,                
            }
            self.send_message_data(data_send)
            #PRINT_LOGGER.debug(data_send)
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(msg)

    def show_online_noble_list(self, msg):    # 在线贵族信息
        try:
            time_int10 = msg['time']
            time_recv = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(msg['time']))
            mtype = re.search('/type@=(.*?)/', msg['data']).group(1) if '/type@=' in msg['data'] else ''
            num = re.search('/num@=(.*?)/', msg['data']).group(1) if '/num@=' in msg['data'] else '0'    # 在线贵族人数
            rid = re.search('/rid@=(.*?)/', msg['data']).group(1) if '/rid@=' in msg['data'] else '0'    # 直播间号
            nl = re.search('/nl@=(.*?)/', msg['data']).group(1) if '/nl@=' in msg['data'] else ''    # 在线贵族top20信息

            nl = self.trans_char(nl)
            lists = nl.split('/')
            nobles = []
            for user in lists:
                if user:
                    user = '/' + self.trans_char(user)
                    uid = re.search('/uid@=(.*?)/', user).group(1) if '/uid@=' in user else '0'    # 用户ID
                    nn = re.search('/nn@=(.*?)/', user).group(1) if '/nn@=' in user else ''    # 用户名称
                    ne = re.search('/ne@=(.*?)/', user).group(1) if '/ne@=' in user else '0'    # 贵族等级
                    lv = re.search('/lv@=(.*?)/', user).group(1) if '/lv@=' in user else '0'    # 用户等级
                    rk = re.search('/rk@=(.*?)/', user).group(1) if '/rk@=' in user else '0'    # 排名
                    #icon = re.search('/icon@=(.*?)/', user).group(1) if '/icon@=' in user else ''    # 用户头像地址
                    #icon = self.trans_char(icon)
                    noble_name = NOBLE_NAME_DICT[ne] if ne in NOBLE_NAME_DICT else ''    # 从字典中获得贵族名称
                    nobles.append({'uid': uid, 'nn': nn, 'ne': ne, 'lv': lv, 'rk': rk, 'noble': noble_name})

            data_send = {
                'time': time_int10,
                'type': mtype,
                'num': num,
                'rid': rid,
                'nl': nobles,                
            }
            self.send_message_data(data_send)
            #PRINT_LOGGER.debug(data_send)
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(msg)

    def show_noble_num_info(self, msg):    # 在线各贵族等级数量信息
        try:
            time_int10 = msg['time']
            time_recv = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(msg['time']))
            mtype = re.search('/type@=(.*?)/', msg['data']).group(1) if '/type@=' in msg['data'] else ''
            sum = re.search('/sum@=(.*?)/', msg['data']).group(1) if '/sum@=' in msg['data'] else '0'    # 在线贵族人数
            rid = re.search('/rid@=(.*?)/', msg['data']).group(1) if '/rid@=' in msg['data'] else '0'    # 直播间号
            list = re.search('/list@=(.*?)/', msg['data']).group(1) if '/list@=' in msg['data'] else ''    # 在线各贵族等级数量信息

            list = self.trans_char(list)
            lists = list.split('/')
            nobles = []
            for noble in lists:
                if noble:
                    noble = '/' + self.trans_char(noble)
                    lev = re.search('/lev@=(.*?)/', noble).group(1) if '/lev@=' in noble else '0'    # 贵族等级
                    num = re.search('/num@=(.*?)/', noble).group(1) if '/num@=' in noble else '0'    # 贵族数量
                    nobles.append({'lev': lev, 'num': num})

            data_send = {
                'time': time_int10,
                'type': mtype,
                'sum': sum,
                'rid': rid,
                'list': nobles,                
            }
            self.send_message_data(data_send)
            #PRINT_LOGGER.debug(data_send)
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(msg)
            
    def recv_server_data(self):
        return self.queue_recv_server_data.get(1)
    
    def send_message_data(self, data, block=1):    # 将分析提取出来的数据发送给主UI线程用于显示
        if self.queue_send_message_data:
            data_send = {
                'time': int(time.time()),
                'roomid': self.roomid,
                'data': data,
            }
            self.queue_send_message_data.put(data_send, block)

    def recv_order_except(self):
        if self.queue_recv_order_except and not self.queue_recv_order_except.empty():
            try:
                return self.queue_recv_order_except.get(0)
            except:
                return None

    def send_order_except(self, data, block=1):
        if self.queue_send_order_except:
            data_send = {
                'time': int(time.time()),
                'roomid': self.roomid,
                'data': data,
            }            
            self.queue_send_order_except.put(data_send, block)
            self.queue_send_message_data.put(data_send, block)

    def trans_char(self, strg):    # 转义字符的替换
        return strg.replace('\\\\', '\\').replace('@S', '/').replace('@A', '@')
    

def log_msg_parse(msg_log, type_tuple):    # 将元组中所列的消息类型的消息记录到对应的日志文件中，以便分析
    for type_parse in type_tuple:    
        if ('type@=' + type_parse) in msg_log:
            log_name ='type_' + type_parse + '.log'
            formatter = logging.Formatter('[%(asctime)s][%(levelname)s]: %(message)s')
            fh_parse = logging.FileHandler(log_name)
            fh_parse.setFormatter(formatter)
            debug_filter = logging.Filter('debug')
            fh_parse.addFilter(debug_filter)
            logger = logging.getLogger('debug')
            logger.setLevel(logging.DEBUG)
            logger.addHandler(fh_parse)
            logger.debug(msg_log)
            logger.removeHandler(fh_parse)


