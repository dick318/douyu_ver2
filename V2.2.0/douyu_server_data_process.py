#!usr/bin/python3
# -*- coding: utf-8 -*-

# filename: douyu_server_data_process.py
# version: 1.0.0
# date: 2017-12-02
# last date: 2018-04-20
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


ERROR_DICT = {'0':u'操作成功', '51':u'数据传输出错', '52':u'服务器关闭', '204':u'房间ID错误'}
CLIENT_TYPE_DICT = {'0':u'浏览器', '1':u'安卓端', '2':u'苹果端', '14':u'电脑端'}        
NOBLE_NAME_DICT = {
    '1':u'骑士', '2':u'子爵', '3':u'伯爵', '4':u'公爵',
    '5':u'国王', '6':u'皇帝', '7':u'游侠'
}
DESERVE_NAME_DICT = {'1':u'初级酬勤', '2':u'中级酬勤', '3':u'高级酬勤'}
GIFT_NAME_DICT = {
    '824':u'粉丝荧光棒', '519':u'呵呵', '520':u'稳', '192':u'赞', '714':u'怂',
    '193':u'弱鸡', '191':u'100鱼丸', '712':u'棒棒哒', '713':u'辣眼睛', '1117':u'没排面',
    '1118':u'有排面', '1027':u'药丸', '380':u'好人卡', '750':u'办卡', '195':u'飞机',
    '196':u'火箭', '1005':u'超级火箭'
}


class ProcessDanmuServerData(object):    # 处理从弹幕服务器接收到的各种信息数据
    def __init__(self, queue_data, queue_message=None,
                 queue_revc_order=None, queue_send_order=None):
        self.queue_server_data = queue_data    # 接收来自接收数据线程的数据，则弹幕服务器的数据
        self.queue_message_data = queue_message    # 存放处理分析得到的数据，发送给主UI线程
        self.queue_recv_order_except = queue_revc_order    # 接收来自接收数据线程的关闭命令或程序异常消息
        self.queue_send_order_except = queue_send_order    # 存放发送给主UI线程的关闭命令或程序异常消息
        
        self.msg_buf = ''    # 储存不完整的消息 
        self.buf_isnull = True    # 标志是否存在不完整的消息
        self.keeplive_time = time.time()    # 记录上次发送给主UI线程心跳消息的时间
        
        self.show_function = {
            'loginres':self.recv_loginres, 'keeplive':self.recv_keeplive,
            'mrkl':self.recv_keeplive, 'chatmsg':self.show_chatmsg,
            'uenter':self.show_uenter, 'spbc':self.show_spbc,
            'anbc':self.show_anbc, 'newblackres':self.show_newblackres,
            'dgb':self.show_dgb, 'bc_buy_deserve':self.show_deserve,
            'rss':self.show_rss, 'error':self.show_error
        }
        self.thread = Thread(target = self.start)    # 创建处理数据线程
        self.thread.setDaemon(True)

    def thread_start(self):    # 开启线程
        self.thread.start()
        
    def start(self):
        while True:
            server_data = self.get_server_data()    # 获取来自接收线程的数据
            order_except = self.get_order_except()
            if order_except:
                if order_except['type'] == 'close':    # 收到结束线程的指令
                    break    # 跳出循环，结束本线程
                elif order_except['type'] == 'exception':    # 收到接收线程发生异常的消息
                    self.put_order_except(order_except)
                    self.put_message_data(order_except)
                
            if server_data['type'] == 'message':
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
                            self.parse_msg_utf8({'time':server_data['time'], 'data':msg_utf8})

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
        data_send = {'type':'closed', 'from':'ProcessDanmuServerData'}
        self.put_order_except(data_send)
        self.put_message_data(data_send)
        PRINT_LOGGER.debug('thread_ProcessDanmuServerData: closed!')                

    def parse_msg_utf8(self, msg_dict):    # 提取消息类型，并调用不同的处理方法
        msg_utf8_str = msg_dict['data']
        if '/type@=' in msg_utf8_str:
            try:
                msg_type = re.search('/type@=(.*?)/', msg_utf8_str).group(1)
                #log_msg_parse(msg_utf8_str, ('spbc', ))                
            except Exception as exc:
                exc_msg = exception_message(exc)
                ERROR_LOGGER.error(exc_msg)
                ERROR_LOGGER.error(msg_utf8_str)
            else:
                if msg_type in self.show_function:    # 根据消息类型调用不同的方法
                    self.show_function[msg_type](msg_dict)
                #if msg_type not in ('chatmsg', 'uenter', 'dgb', 'online_noble_list', 'noble_num_info'):
                    #log_msg_parse(msg_utf8_str, (msg_type, ))

    def recv_loginres(self, loginres_msg):    # 接收到登录弹幕服务器成功的消息，提取数据发送给主UI线程
        try:
            PRINT_LOGGER.debug(u'连接直播间弹幕成功')
            dsptext = {'type':'loginres'}
            self.put_message_data(dsptext)
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(loginres_msg)
                    
    def recv_keeplive(self, keeplive_msg):    # 若能接收到心跳消息，则给主UI线程发送心跳消息
        #PRINT_LOGGER.debug(keeplive_msg)
        #if (time.time() - self.keeplive_time) >= 20:
        self.keeplive_time = time.time()
        try:
            #tick = re.search('/tick@=(.*?)/', keeplive_msg).group(1) if '/tick@=' in keeplive_msg else '0'    # 旧版心跳消息
            #PRINT_LOGGER.debug(keeplive_msg)
            dsptext = {'type':'keeplive'}
            self.put_message_data(dsptext)
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(keeplive_msg)
        
    def show_chatmsg(self, msg):    # 弹幕消息，提取弹幕消息中的数据
        try:
            chat_msg = msg['data']
            time_int10 = msg['time']
            time_recv = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(msg['time']))
            nn = re.search('/nn@=(.*?)/', chat_msg).group(1) if '/nn@=' in chat_msg else '?'    # 用户名称
            level = (re.search('/level@=(.*?)/', chat_msg).group(1) if '/level@=' in chat_msg else '?')    # 用户等级
            nl = re.search('/nl@=(.*?)/', chat_msg).group(1) if '/nl@=' in chat_msg else '-1'    # 贵族等级
            txt = self.trans_char(re.search('/txt@=(.*?)/', chat_msg).group(1) if '/txt@=' in chat_msg else '')    # 弹幕内容
            # 客户端类型: 无-电脑浏览器 1-安卓端 2-苹果端 14-PC客户端 其它-未知
            ct = re.search('/ct@=(.*?)/', chat_msg).group(1) if '/ct@=' in chat_msg else '0'    
            # 弹幕颜色: 无-默认 1-21级红色 2-6级蓝色 3-9级绿色 4-15级橙色 5-18级紫色 6-12级粉色
            col = re.search('/col@=(.*?)/', chat_msg).group(1) if '/col@=' in chat_msg else '0'    
            rid = re.search('/rid@=(.*?)/', chat_msg).group(1) if '/rid@=' in chat_msg else ''    # 直播间号
            noble_name = NOBLE_NAME_DICT[nl] if nl in NOBLE_NAME_DICT else ''    # 从字典中获得贵族名称            
            client_type = CLIENT_TYPE_DICT[ct] if ct in CLIENT_TYPE_DICT else u'未知'    # 从字典中获得客户端类型
            if noble_name:
                msg_to = u'%s (%s) <%s> {%s} %s: %s' % (time_recv, client_type, level, noble_name, nn, txt)
            else:
                msg_to = u'%s (%s) <%s> %s: %s' % (time_recv, client_type, level, nn, txt)
            PRINT_LOGGER.debug(msg_to)
            dsptext = {
                'time':time_int10, 'ct':client_type, 'level':level, 'nl':noble_name,
                'nn':nn, 'txt':txt, 'col':col, 'rid':rid, 'type':'chatmsg'
            }
            self.put_message_data(dsptext)
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(msg)
            
    def show_uenter(self, msg):    # 用户进入直播间消息
        try:
            uenter_msg = msg['data']
            time_int10 = msg['time']
            time_recv = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(msg['time']))
            nn = re.search('/nn@=(.*?)/', uenter_msg).group(1) if '/nn@=' in uenter_msg else '?'    # 用户名称
            level = (re.search('/level@=(.*?)/', uenter_msg).group(1) if '/level@=' in uenter_msg else '?')    # 用户等级
            nl = re.search('/nl@=(.*?)/', uenter_msg).group(1) if '/nl@=' in uenter_msg else '-1'    # 贵族等级
            rid = re.search('/rid@=(.*?)/', uenter_msg).group(1) if '/rid@=' in uenter_msg else ''    # 直播间号
            noble_name = NOBLE_NAME_DICT[nl] if nl in NOBLE_NAME_DICT else ''    # 从字典中获得贵族名称
            if noble_name:
                msg_to = u'%s <%s> {%s} %s 进入直播间' % (time_recv, level, noble_name, nn)
            else:
                msg_to = u'%s <%s> %s 进入直播间' % (time_recv, level, nn)
            PRINT_LOGGER.debug(msg_to)
            dsptext = {
                'time':time_int10, 'level':level, 'nl':noble_name,
                'nn':nn, 'rid':rid, 'type':'uenter'
            }
            self.put_message_data(dsptext)
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(msg)           

    def show_newblackres(self, msg):    # 禁言消息
        try:
            newblackres_msg = msg['data']
            time_int10 = msg['time']
            time_recv = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(msg['time']))
            snic = re.search('/snic@=(.*?)/', newblackres_msg).group(1) if '/snic@=' in newblackres_msg else '?'    # 房管名称
            dnic = re.search('/dnic@=(.*?)/', newblackres_msg).group(1) if '/dnic@=' in newblackres_msg else '?'    # 被禁言用户名称
            endtime = re.search('/endtime@=(.*?)/', newblackres_msg).group(1) if '/endtime@=' in newblackres_msg else ''    # 禁言结束时间
            time_end = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(endtime))) if endtime else '?'
            rid = re.search('/rid@=(.*?)/', newblackres_msg).group(1) if '/rid@=' in newblackres_msg else ''    # 直播间号            
            msg_to = u'%s %s 已被禁言(%s) 解禁时间: %s' % (time_recv, dnic, snic, time_end)
            PRINT_LOGGER.debug(msg_to)
            dsptext = {
                'time':time_int10, 'dnic':dnic, 'snic':snic,
                'endtime':time_end, 'rid':rid, 'type':'newblackres'
            }
            self.put_message_data(dsptext)
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(msg)            

    def show_dgb(self, msg):    # 赠送礼物消息
        try:
            dgb_msg = msg['data']
            time_int10 = msg['time']
            time_recv = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(msg['time']))
            nn = re.search('/nn@=(.*?)/', dgb_msg).group(1) if '/nn@=' in dgb_msg else '?'    # 用户名称
            level = (re.search('/level@=(.*?)/', dgb_msg).group(1) if '/level@=' in dgb_msg else '?')    # 用户等级
            nl = re.search('/nl@=(.*?)/', dgb_msg).group(1) if '/nl@=' in dgb_msg else '-1'    # 贵族等级
            gfid = re.search('/gfid@=(.*?)/', dgb_msg).group(1) if '/gfid@=' in dgb_msg else ''    # 礼物ID            
            hits = re.search('/hits@=(.*?)/', dgb_msg).group(1) if '/hits@=' in dgb_msg else '0'    # 连击数
            bg = re.search('/bg@=(.*?)/', dgb_msg).group(1) if '/bg@=' in dgb_msg else '0'    # 大礼物标识，无或0-小礼物 1-大礼物
            rid = re.search('/rid@=(.*?)/', dgb_msg).group(1) if '/rid@=' in dgb_msg else ''    # 直播间号            
            noble_name = NOBLE_NAME_DICT[nl] if nl in NOBLE_NAME_DICT else ''    # 从字典中获得贵族名称        
            giftname = GIFT_NAME_DICT[gfid] if gfid in GIFT_NAME_DICT else gfid    # 从字典中获得礼物名称            
            if hits == '0':
                if noble_name:
                    msg_to = u'%s <%s> {%s} %s 赠送给主播 %s' % (time_recv, level, noble_name, nn, giftname)
                else:
                    msg_to = u'%s <%s> %s 赠送给主播 %s' % (time_recv, level, nn, giftname)
                PRINT_LOGGER.debug(msg_to)
                dsptext = {
                    'time':time_int10, 'level':level, 'nl':noble_name, 'nn':nn,
                    'gn':giftname, 'hits':hits, 'gfid':gfid, 'bg':bg, 'rid':rid, 'type':'dgb'
                }
                self.put_message_data(dsptext)
            elif int(hits)%10 == 0 or bg == '1':
                if noble_name:
                    msg_to = u'%s <%s> {%s} %s 赠送给主播 %s X%s' % (time_recv, level, noble_name, nn, giftname, hits)
                else:
                    msg_to = u'%s <%s> %s 赠送给主播 %s X%s' % (time_recv, level, nn, giftname, hits)
                PRINT_LOGGER.debug(msg_to)
                dsptext = {
                    'time':time_int10, 'level':level, 'nl':noble_name,
                    'nn':nn, 'gn':giftname, 'hits':hits, 'gfid':gfid,
                    'bg':bg, 'rid':rid, 'type':'dgb'
                }
                self.put_message_data(dsptext)                
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(msg)

    def show_deserve(self, msg):    # 赠送酬勤消息
        try:
            deserve_msg = msg['data']
            time_int10 = msg['time']
            time_recv = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(msg['time']))
            nn = re.search('@Snick@A=(.*?)@S', deserve_msg).group(1) if '@Snick@A=' in deserve_msg else '?'    # 用户名称
            level = (re.search('/level@=(.*?)/', deserve_msg).group(1) if '/level@=' in deserve_msg else '?')    # 用户等级        
            hits = re.search('/hits@=(.*?)/', deserve_msg).group(1) if '/hits@=' in deserve_msg else '0'    # 连击数
            lev = re.search('/lev@=(.*?)/', deserve_msg).group(1) if '/lev@=' in deserve_msg else '0'    # 酬勤等级：1-初级酬勤 2-中级酬勤 3-高级酬勤
            rid = re.search('/rid@=(.*?)/', deserve_msg).group(1) if '/rid@=' in deserve_msg else ''    # 直播间号
            noble_name = ''
            bg = '1'
            gfid = 'deserve'
            giftname = DESERVE_NAME_DICT[lev] if lev in DESERVE_NAME_DICT else '?'    # 从字典中获得酬勤名称
            if hits == '0':
                msg_to = u'%s <%s> %s %s 赠送给主播 %s' % (time_recv, level, noble_name, nn, giftname)
                PRINT_LOGGER.debug(msg_to)
                dsptext = {
                    'time':time_int10, 'level':level, 'nl':noble_name,
                    'nn':nn, 'gn':giftname, 'hits':hits, 'gfid':gfid,
                    'bg':bg, 'rid':rid, 'type':'dgb'
                }
                self.put_message_data(dsptext)
            else:
                msg_to = u'%s <%s> %s %s 赠送给主播 %s X%s' % (time_recv, level, noble_name, nn, giftname, hits)
                PRINT_LOGGER.debug(msg_to)
                dsptext = {
                    'time':time_int10, 'level':level, 'nl':noble_name,
                    'nn':nn, 'gn':giftname, 'hits':hits, 'gfid':gfid,
                    'bg':bg, 'rid':rid, 'type':'dgb'
                }
                self.put_message_data(dsptext)
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(msg)
            
    def show_spbc(self, msg):    # 礼物广播消息
        try:
            spbc_msg = msg['data']
            time_int10 = msg['time']
            time_recv = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(msg['time']))
            sn = re.search('/sn@=(.*?)/', spbc_msg).group(1) if '/sn@=' in spbc_msg else '?'    # 赠送用户名称
            dn = re.search('/dn@=(.*?)/', spbc_msg).group(1) if '/dn@=' in spbc_msg else '?'    # 受赠主播名称
            gn = re.search('/gn@=(.*?)/', spbc_msg).group(1) if '/gn@=' in spbc_msg else '?'    # 礼物名称
            gc = re.search('/gc@=(.*?)/', spbc_msg).group(1) if '/gc@=' in spbc_msg else '0'    # 礼物数量
            drid = re.search('/drid@=(.*?)/', spbc_msg).group(1) if '/drid@=' in spbc_msg else ''    # 受赠直播间号
            gfid = re.search('/gfid@=(.*?)/', spbc_msg).group(1) if '/gfid@=' in spbc_msg else ''    # 礼物ID
            es = re.search('/es@=(.*?)/', spbc_msg).group(1) if '/es@=' in spbc_msg else '0'    # 广播展现样式，1-火箭 2-飞机 101-超级火箭
            gb = re.search('/gb@=(.*?)/', spbc_msg).group(1) if '/gb@=' in spbc_msg else '0'    # 是否有宝箱，0-无 1-有            
            msg_to = u'%s %s 赠送给 %s %s个 %s\n直播间: https://www.douyu.com/%s' % (time_recv, sn, dn, gc, gn, drid)
            PRINT_LOGGER.debug(msg_to)
            dsptext = {
                'time':time_int10, 'sn':sn, 'dn':dn, 'gn':gn,
                'drid':drid, 'es':es, 'gb':gb, 'type':'spbc'
            }
            self.put_message_data(dsptext)
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(msg)

    def show_anbc(self, msg):    # 贵族开通消息
        try:
            anbc_msg = msg['data']
            time_int10 = msg['time']
            time_recv = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(msg['time']))
            unk = re.search('/unk@=(.*?)/', anbc_msg).group(1) if '/unk@=' in anbc_msg else '?'    # 开通贵族用户名称
            donk = re.search('/donk@=(.*?)/', anbc_msg).group(1) if '/donk@=' in anbc_msg else ''    # 受益主播名称
            drid = re.search('/drid@=(.*?)/', anbc_msg).group(1) if '/drid@=' in anbc_msg else ''    # 受益主播直播间号
            nl = re.search('/nl@=(.*?)/', anbc_msg).group(1) if '/nl@=' in anbc_msg else '-1'    # 贵族等级：1-骑士 2-子爵 3-伯爵 4-公爵 5-国王 6-皇帝 7-游侠
            gvnk = re.search('/gvnk@=(.*?)/', anbc_msg).group(1) if '/gvnk@=' in anbc_msg else ''    # 赠送贵族用户名称            
            noble_name = NOBLE_NAME_DICT[nl] if nl in NOBLE_NAME_DICT else '?'    # 从字典中获得贵族名称            
            if ('gvnk@=' in anbc_msg) and ('donk@=' in anbc_msg):
                msg_to = (
                    u'%s %s 在 %s 的房间给 %s 开通了%s' % (time_recv, gvnk, donk, unk, noble_name) +
                    u'\n直播间: https://www.douyu.com/%s' % drid)
            elif ('gvnk@=' not in anbc_msg) and ('donk@=' in anbc_msg):
                msg_to = (
                    u'%s %s 在 %s 的房间开通了%s' % (time_recv, unk, donk, noble_name) +
                    u'\n直播间: https://www.douyu.com/%s' % drid)
            elif ('gvnk@=' in anbc_msg) and ('donk@=' not in anbc_msg):
                msg_to = u'%s %s 给 %s 开通了%s' % (time_recv, gvnk, unk, noble_name)
            else:
                msg_to = u'%s %s 开通了%s' % (time_recv, unk, noble_name)
            PRINT_LOGGER.debug(msg_to)
            dsptext = {
                'time':time_int10, 'gvnk':gvnk, 'donk':donk, 'unk':unk,
                'nl':noble_name, 'drid':drid, 'type':'anbc'
            }
            self.put_message_data(dsptext)
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(msg)
    
    def show_rss(self, msg):    # 开关播消息
        try:
            rss_msg = msg['data']
            time_int10 = msg['time']
            time_recv = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(msg['time']))
            rid = re.search('/rid@=(.*?)/', rss_msg).group(1) if '/rid@=' in rss_msg else ''    # 直播间号
            ss = re.search('/ss@=(.*?)/', rss_msg).group(1) if '/ss@=' in rss_msg else '0'    # 直播状态：1-开播 0-关播            
            msg_to = rid + u' 开播了！'
            PRINT_LOGGER.debug(msg_to)
            dsptext = {'time':time_int10, 'ss':ss, 'rid':rid, 'type':'rss'}      
            self.put_message_data(dsptext)
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(msg)
                
    def show_error(self, msg):    # 服务器错误消息
        try:
            error_msg = msg['data']
            time_int10 = msg['time']
            time_recv = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(msg['time']))
            error_code = re.search('/code@=(.*?)/', error_msg).group(1) if '/code@=' in error_msg else ''    # 错误码
            error_str = ERROR_DICT[error_code] if error_code in ERROR_DICT else u'服务器内部异常'
            exc_msg = u'#%s %s: code=%s\n' % (time_recv, error_str,error_code)
            WARNING_LOGGER.warning(exc_msg)
            dsptext = {'time':time_int10, 'reason':error_str, 'code':error_code, 'type':'error'}
            self.put_message_data(dsptext)
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(msg)

    def get_server_data(self):
        return self.queue_server_data.get(1)
    
    def put_message_data(self, data, block=1):    # 将分析提取出来的数据发送给主UI线程用于显示
        if self.queue_message_data:
            self.queue_message_data.put(data, block)

    def get_order_except(self):
        if self.queue_recv_order_except and not self.queue_recv_order_except.empty():
            try:
                return self.queue_recv_order_except.get(0)
            except:
                return None

    def put_order_except(self, data, block=1):
        if self.queue_send_order_except:
            self.queue_send_order_except.put(data, block)            

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


