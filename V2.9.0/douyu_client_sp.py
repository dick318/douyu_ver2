#!usr/bin/python3
# -*- coding: utf-8 -*-

# filename: douyu_sp.py
# version: 1.0.0
# date: 2018-04-06
# last date: 2018-10-28
# os: windows

import json
import logging
import os
import pickle
import re
import socket
import sqlite3
import sys
import time
import urllib.request
import webbrowser

from queue import Queue
from threading import Thread, Event

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHBoxLayout, QWidget, QTextEdit, QPushButton, QCheckBox

from douyu_client_gui import DYApplication
from douyu_client import * 

from douyu_server_data_process import ProcessDanmuServerData
from douyu_server_data_receive import GetDanmuServerData

# 关于软件的说明
about = ABOUT_SOFTWARE.split('\n')
about[1] += 'special'
ABOUT_SOFTWARE_SP = '\n'.join(about)


# 抢宝箱时同时打开两个浏览器
class DisplayWindowSP(MainWindow):
    def __init__(self):
        super(DisplayWindowSP, self).__init__()
        from douyu_client_gui import CHINESE_SIZE
        self.connect_widget = QWidget(self)
        self.room_id_list_config_button = QPushButton(u'设置监视的直播间列表', self)
        self.anchor_blacklist_config_button = QPushButton(u'设置主播黑名单', self)
        self.anchor_blacklist_check = QCheckBox(u'启用主播黑名单', self)
        self.room_id_list_config_widget = TextEditWidget(self)
        self.anchor_blacklist_config_widget = TextEditWidget(self)

        self.room_id_list_config_button.setCursor(POINT_HAND_CURSOR)
        self.anchor_blacklist_config_button.setCursor(POINT_HAND_CURSOR)
        self.room_id_list_config_button.setFixedWidth(CHINESE_SIZE.width() * 12)
        self.anchor_blacklist_config_button.setFixedWidth(CHINESE_SIZE.width() * 12)
        self.room_id_list_config_widget.setWindowTitle(u'设置监视的直播间列表')
        self.anchor_blacklist_config_widget.setWindowTitle(u'设置主播黑名单')
        
        self.topbar_widget.roomid_enter.setText('000000')
        self.topbar_widget.roomid_enter.setDisabled(True)
        self.topbar_widget.connect_danmu.setParent(self.connect_widget)
        self.topbar_widget.hide()
        self.tab_window.removeTab(0)
        self.tab_window.removeTab(1)
       
        connect_layout = QHBoxLayout()
        connect_layout.addWidget(self.anchor_blacklist_check)
        connect_layout.addWidget(self.anchor_blacklist_config_button)
        connect_layout.addStretch(1)
        connect_layout.addWidget(self.room_id_list_config_button)
        connect_layout.addWidget(self.topbar_widget.connect_danmu)
        connect_layout.setContentsMargins(10, 10, 10, 0)
        self.connect_widget.setLayout(connect_layout)
        self.connect_widget.resize(connect_layout.sizeHint())        
        self.layout().insertWidget(0, self.connect_widget)
        
        self.room_id = '000000'
        self.connected_room_id_list = []
        self.room_id_list = []    # 连接的直播间号列表
        self.anchor_blacklist_enabled = False
        self.anchor_blacklist = []    # 主播黑名单
        self.queue_rid_order = {}
        self.queue_server_data = {}
        self.queue_message_data = {}
        self.queue_order_except_1 = {}
        self.queue_order_except_2 = {}
        self.dsp_temp = {}    # 广播消息显示缓存

        self.config_sp_file = os.path.join(self.room_config_path, 'config_sp')
        self.browser_list_file = os.path.join(PROGRAM_CONFIG_FOLDER, 'BrowserList')
        self.browser_list = self.load_browser_list()
        self.update_details_timer.timeout.disconnect()
        self.config_widget.save_config_button.clicked.connect(self.load_browser_event)
        self.room_id_list_config_button.clicked.connect(self.room_id_list_config_button_event)
        self.anchor_blacklist_config_button.clicked.connect(self.anchor_blacklist_config_button_event)
        self.anchor_blacklist_check.clicked.connect(self.anchor_blacklist_check_event)
        self.room_id_list_config_widget.save_button.clicked.connect(self.room_id_list_config_save_event)
        self.anchor_blacklist_config_widget.save_button.clicked.connect(self.anchor_blacklist_config_save_event)        
        self.room_id_list_config_widget.cancel_button.clicked.connect(self.room_id_list_config_widget.hide)
        self.anchor_blacklist_config_widget.cancel_button.clicked.connect(self.anchor_blacklist_config_widget.hide)

        self.load_config_sp()

    def connect_event(self):    # 连接按键的事件处理器
        try:
            self.room_id = '000000'
            self.connected_room_id_list = [i for i in self.room_id_list]
            if self.connected_room_id_list:
                self.connect_triggered = True
                self.topbar_widget.connect_danmu.setDisabled(True)         

                self.gift_dict_saved = self.load_gift_dict()    # 加载保存在文件中的礼物ID与名称
                self.room_gift.update(self.gift_dict_saved)
                self.load_room_config()    # 加载直播间设置

                self.queue_rid_order = {}
                self.queue_server_data = {}
                self.queue_message_data = {}
                self.queue_order_except_1 = {}
                self.queue_order_except_2 = {}
                self.dsp_temp = {}
                
                for roomid in self.connected_room_id_list:                        
                    # 定义所需队列
                    self.queue_rid_order[roomid] = Queue()
                    self.queue_server_data[roomid] = Queue()
                    self.queue_message_data[roomid] = Queue()
                    self.queue_order_except_1[roomid] = Queue()
                    self.queue_order_except_2[roomid] = Queue()
                    self.dsp_temp[roomid] = {}
                    
                    self.queue_rid_order[roomid].put(roomid, 1)    # 直播间号发送给接收数据线程
                    receive_server = GetDanmuServerData(
                        self.queue_server_data[roomid],
                        self.queue_rid_order[roomid],
                        self.queue_order_except_1[roomid],
                        self.set_danmu_server,
                        self.set_danmu_port,
                        self.set_danmu_group)    # 接收数据线程，心跳线程
                    process_server = ProcessDanmuServerDataSP(
                        self.queue_server_data[roomid],
                        self.queue_message_data[roomid],
                        self.queue_order_except_1[roomid],
                        self.queue_order_except_2[roomid])    # 处理数据线程
                    # 启动各线程
                    self.start_display_message(roomid)
                    receive_server.thread_start()
                    process_server.thread_start()
                #self.start_get_details()
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)

    def disconnect_event(self):    # 断开按键的事件处理器
        self.event_display.set()
        self.connect_triggered = False
        self.save_room_config()    # 保存直播间设置
        self.topbar_widget.connect_danmu.setDisabled(True)
        for roomid in self.connected_room_id_list:
            self.queue_rid_order[roomid].put('close', 1)    # 发送结束消息给接收数据线程
        
    def start_display_message(self, roomid):    # 创建并开启触发显示线程
        self.event_display.set()
        self.run_display_message = True
        thread_display = Thread(target=self.thread_display_message,
                                args=(roomid,
                                      self.queue_message_data[roomid],
                                      self.queue_order_except_2[roomid]))
        thread_display.setDaemon(True)
        thread_display.start()

    def thread_display_message(self, room_id, queue_data, queue_order_except):    # 触发显示线程
        while self.run_display_message:
            if not queue_order_except.empty():
                try:
                    order_except = queue_order_except.get(0)                   
                    if order_except['type'] == 'closed':    # 后台接收和处理线程都已经关闭，关闭本线程
                        break
                    else:
                        self.process_message_signal.emit({
                            'rid': room_id,
                            'data': order_except
                        })    # 触发处理程序内部异常信息
                except:
                    pass
            else:
                data = queue_data.get(1)
                try:
                    if data['type'] in self.all_message_type:
                        self.event_display.clear()
                        self.process_message_signal.emit({
                            'rid': room_id,
                            'data': data
                        })    # 发送信号，触发处理显示服务器消息                        
                        self.event_display.wait(0.1)
                except Exception as exc:
                    exc_msg = exception_message(exc)
                    ERROR_LOGGER.error(exc_msg)
                    ERROR_LOGGER.error(repr(data))
        self.process_message_signal.emit({
            'rid': room_id,
            'data': {
                'time': int(time.time()),
                'type': 'disconnected',
                'from': 'main',
                'rid': order_except['rid']
            }
        })
        PRINT_LOGGER.debug('thread_display_message: closed!')
        
    def process_message_event(self, mdata):    # 处理显示消息，由触发显示线程触发        
        try:
            data = mdata['data']
            if 'time' in data:
                time_str = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(data['time']))
            #if data['type'] in self.danmu_message_type:
            #    self.display_danmu_message(data)
            #elif data['type'] in self.gift_message_type:
            #    self.display_gift_message(data)
            if data['type'] in self.broadcast_message_type:
                exist = self.check_msg_showed(mdata)
                if not exist:
                    self.display_broadcast_message(data)
            #elif data['type'] in self.list_message_type:
            #    self.display_list_message(data)
            elif data['type'] == 'rss':
                self.display_rss_message(data)
            elif data['type'] == 'loginres':
                self.process_loginres_message(data)
                self.update_details_timer.stop()
                dsp_str = u'%s 直播间【%s】连接成功' % (time_str, data['rid'])
                self.display_record_message(dsp_str)
            elif data['type'] in ('keeplive', 'live'):
                self.process_keeplive_message(data)
            elif data['type'] in ('exception', 'error'):
                self.process_error_message(mdata)

            elif data['type'] == 'disconnected':
                self.process_disconnected_message(data)
                dsp_str = u'%s 直播间【%s】已断开连接' % (time_str, data['rid'])
                self.display_record_message(dsp_str)

            # 设置了记录消息，则将数据发送给记录消息线程
            if (self.set_record and data['type'] in self.record_type_list and
                (data['type'] not in self.broadcast_message_type or
                 (data['type'] in self.broadcast_message_type and not exist))):
                if self.new_record:
                    self.new_record = False
                    self.start_record_message()    # 开启记录消息线程
                self.queue_record_data.put(data, 1)
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(repr(mdata))
        finally:
            self.event_display.set()
            pass

    def process_error_message(self, mdata):    # 弹窗提醒错误消息和相应处理
        data = mdata['data']
        self.is_error = True
        self.can_refresh_details = False
        time_short = time.strftime(' (%H:%M:%S) ', time.localtime(data['time']))
        #self.update_title_statusbar_tray(self.room_icon, data['reason'] + time_short)    # 设置窗体标题、状态栏、托盘图标说明

        time_str = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(data['time']))
        msg_remind = u'%s\n直播间【%s】%s' % (time_str, data['rid'], data['reason'])
        self.show_connect_error(msg_remind, self.room_id)    # 弹窗提示错误
        dsp_str = u'%s 直播间【%s】%s' % (time_str, data['rid'], data['reason'])
        self.display_record_message(dsp_str)
        
        if data['code'] in ['failed', 'timeout']:    # 网络断开或连接超时，处于重试状态
            self.topbar_widget.connect_danmu.setText(u'断开')
            self.tray_icon.action_connect.setText(u'断开(%s)' % self.room_id)
            self.topbar_widget.connect_danmu.clicked.disconnect()    # 取消按键事件绑定
            self.tray_icon.action_connect.triggered.disconnect()  
            self.topbar_widget.connect_danmu.clicked.connect(self.disconnect_event)
            self.tray_icon.action_connect.triggered.connect(self.disconnect_event)
            self.topbar_widget.connect_danmu.setEnabled(True)
        else:    # 发生其它错误导致需重启后台线程
            self.restart = True    # 标志自动重启后台线程
            self.disconnect_event()    # 触发断开连接事件处理器
            
    def check_msg_showed(self, mdata):
        try:
            roomid = mdata['rid']
            data = mdata['data']
            rtime = data['time']
            temp = {}
            if data['type'] == 'spbc' or data['type'] == 'bgbc':
                msg_data = [data['type'], data['sn'], data['dn'], data['gc'], data['gn']]
            elif data['type'] == 'anbc' or data['type'] == 'rnewbc':
                msg_data = [data['type'], data['unk'], data['donk'], data['gvnk'], data['nl']]
            elif data['type'] == 'cthn':
                msg_data = [data['type'], data['unk'], data['onk'], data['chatmsg']]
            elif data['type'] == 'ssd':
                msg_data = [data['type'], data['content'], data['trid']]
                
            for rid in self.dsp_temp:
                temp[rid] = {}
                for ktime in self.dsp_temp[rid]:
                    if (rtime - ktime) < 3:
                        temp[rid][ktime] = self.dsp_temp[rid][ktime]
            self.dsp_temp = temp
            for rid in [i for i in self.dsp_temp.keys() if i != roomid]:
                for ktime in self.dsp_temp[rid]:
                    if msg_data in self.dsp_temp[rid][ktime]:                        
                        return True
            if rtime in self.dsp_temp[roomid]:
                self.dsp_temp[roomid][rtime].append(msg_data)
            else:
                self.dsp_temp[roomid][rtime] = [msg_data]
            return False
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            return False

    def display_broadcast_message(self, data):    # 在广播消息框中显示广播消息
        text_html = self.get_display_text(data)
        if text_html:
            self.broadcast_widget.broadcast_text.append(text_html)    # 在广播消息框中显示该条消息
        if ((data['type'] in ('spbc', 'bgbc') and
            ((data['sn'] and data['sn'] in self.broadcast_care_list) or
             (data['dn'] and data['dn'] in self.broadcast_care_list))) or
            (data['type'] in ('anbc', 'rnewbc') and
             ((data['gvnk'] and data['gvnk'] in self.broadcast_care_list) or
              (data['unk'] and data['unk'] in self.broadcast_care_list) or
              (data['donk'] and data['donk'] in self.broadcast_care_list))) or
            (data['type'] == 'cthn' and
             ((data['unk'] and data['unk'] in self.broadcast_care_list) or
              (data['onk'] and data['onk'] in self.broadcast_care_list)))):
            self.display_record_message(text_html)    # 在关注列表中，在记录窗中显示
            
        if data['type'] == 'spbc' or data['type'] == 'bgbc':    # 礼物宝箱提醒
            if ((data['type'] == 'spbc' and self.set_sprocket_noble_remind and data['es'] == '101') or
                (self.set_all_gift_remind and data['gn'] not in self.gift_remind_blacklist and
                 ((self.anchor_blacklist_enabled and data['dn'] not in self.anchor_blacklist) or
                  not self.anchor_blacklist_enabled))):
                time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data['time']))
                msg_remind = (u'[%s] %s 赠送给 %s %s个【%s】' %
                              (time_str, data['sn'], data['dn'], data['gc'], data['gn']))
                self.show_gift_remind(msg_remind, data['drid'])
        elif data['type'] == 'anbc':    # 开通贵族宝箱提醒
            if ((self.set_sprocket_noble_remind or
                 (self.set_all_gift_remind and
                  data['noble'] not in self.gift_remind_blacklist)) and
                (data['noble'] in (u'伯爵', u'公爵', u'国王', u'皇帝')) and
                data['donk'] != '' and data['drid'] != '0'):    # 判断是否要进行弹窗提醒
                time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data['time']))
                if data['gvnk'] == '':
                    msg_remind = (u'[%s] %s 在 %s 的房间开通了【%s】' %
                                  (time_str, data['unk'], data['donk'], data['noble']))
                else:
                    msg_remind = (u'[%s] %s 在 %s 的房间给 %s 开通了【%s】' %
                                  (time_str, data['gvnk'], data['donk'], data['unk'], data['noble']))
                self.show_gift_remind(msg_remind, data['drid'])

    def display_rss_message(self, data):    # 在文本框中显示开关播消息，并根据设置进行弹窗提醒
        if data['ss'] == '1':    # 是开播消息
            if self.set_open_remind:    # 设置了开播提醒，则进行弹窗提醒
                time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data['time']))
                msg_remind = u'[%s]\n【%s】开播了！' % (time_str, data['rid'])
                self.show_open_remind(msg_remind, data['rid'])
            if self.set_auto_enter:    # 设置了开播自动打开直播间，则调用浏览器打开链接
                webbrowser.open(self.douyu_url + data['rid'])
        else:    # 是关播消息
            if self.open_remind_box:    # 关闭存在的开播提醒
                self.open_remind_box.set_duration(1)
                
        text_html = self.get_display_text(data)
        self.display_record_message(text_html)
        #self.update_details_timer.stop()
        #self.update_details_timer.start(5000)    # 5秒后更新直播间详细信息

    def room_id_list_config_button_event(self):
        text = '\n'.join(self.room_id_list)
        self.room_id_list_config_widget.edit_area.setText(text)
        self.room_id_list_config_widget.show()
        
    def anchor_blacklist_config_button_event(self):
        text = '\n'.join(self.anchor_blacklist)
        self.anchor_blacklist_config_widget.edit_area.setText(text)
        self.anchor_blacklist_config_widget.show()

    def room_id_list_config_save_event(self):
        self.room_id_list_config_widget.hide()
        text = self.room_id_list_config_widget.edit_area.toPlainText()
        temp_list = text.replace(' ', '').split('\n')        
        self.room_id_list = []
        for each in temp_list:
            if each != '' and each.isdigit() and each not in self.room_id_list:
                self.room_id_list.append(each)
        self.statusbar.danmu_num.setText(u'监视直播间数量：' + str(len(self.room_id_list)))
        self.save_config_sp()

    def anchor_blacklist_config_save_event(self):
        self.anchor_blacklist_config_widget.hide()
        text = self.anchor_blacklist_config_widget.edit_area.toPlainText()
        temp_list = text.replace(' ', '').split('\n')
        self.anchor_blacklist = []
        for each in temp_list:
            if each != '' and each not in self.anchor_blacklist:
                self.anchor_blacklist.append(each)
        self.statusbar.gift_num.setText(u'主播黑名单数量：' + str(len(self.anchor_blacklist)))
        self.save_config_sp()

    def anchor_blacklist_check_event(self):
        self.anchor_blacklist_enabled = self.anchor_blacklist_check.isChecked()
        self.save_config_sp()
        
    def load_browser_event(self):
        self.browser_list = self.load_browser_list()

    def load_browser_list(self):
        try:
            with open(self.browser_list_file, 'r') as bs_file:
                bs_list = bs_file.readlines()
            bs_dict = {}
            for i in range(len(bs_list)):
                bs_dir = bs_list[i].replace('\n', '')
                if bs_dir:
                    bs_name = 'browser' + str(i)
                    webbrowser.register(bs_name, None, webbrowser.BackgroundBrowser(bs_dir))
                    bs_dict[bs_name] = bs_dir
            return bs_dict
        except Exception as exc:
            return {}

    def load_config_sp(self):
        if os.path.exists(self.config_sp_file):
            try:
                with open(self.config_sp_file, 'rb') as config_file:
                    config_data = pickle.load(config_file)
                self.room_id_list = config_data['RoomIdList']
                self.anchor_blacklist = config_data['AnchorBlacklist']
                self.anchor_blacklist_enabled = config_data['AnchorBlacklistEnabled']
            except Exception as exc:
                exc_msg = exception_message(exc) + u'#加载特殊设置失败'
                ERROR_LOGGER.error(exc_msg)
                os.remove(self.config_sp_file)
                self.room_id_list = []
                self.anchor_blacklist = []
                self.anchor_blacklist_enabled = False
                self.save_config_sp()
        else:
            self.room_id_list = []
            self.anchor_blacklist = []
            self.anchor_blacklist_enabled = False
            self.save_config_sp()
        self.anchor_blacklist_check.setChecked(self.anchor_blacklist_enabled)
        self.statusbar.danmu_num.setText(u'监视直播间数量：' + str(len(self.room_id_list)))
        self.statusbar.gift_num.setText(u'主播黑名单数量：' + str(len(self.anchor_blacklist)))

    def save_config_sp(self):
        try:
            config_data = {
                'RoomIdList': self.room_id_list,
                'AnchorBlacklist': self.anchor_blacklist,
                'AnchorBlacklistEnabled': self.anchor_blacklist_enabled
            }
            with open(self.config_sp_file, 'wb') as config_file:
                pickle.dump(config_data, config_file)
        except Exception as exc:
            exc_msg = exception_message(exc) + u'#保存特殊设置失败'
            ERROR_LOGGER.warning(exc_msg)            
                
    def show_gift_remind(self, message, roomid):
        self.gift_remind_box = MessageBoxSP(self, u'抢宝箱提醒', message, u'抢宝箱',
                                            u'算了', self.set_gift_remind_duration,
                                            self.browser_list)
        self.gift_remind_box.set_url(self.douyu_url + roomid)
        self.gift_remind_box.set_sound(self.gift_remind_sound_path, 0)
        self.gift_remind_box.set_stay_top(True)
        if self.set_gift_remind_sound:
            self.gift_remind_box.play_sound()
        self.gift_remind_box.setWindowFlag(Qt.WindowCloseButtonHint, False)
        self.gift_remind_box.show()

    def about_software_event(self):    # 弹窗显示关于程序的信息
        self.show_about_software(ABOUT_SOFTWARE_SP)


class TextEditWidget(QDialog):
    def __init__(self, parent=None):
        super(TextEditWidget, self).__init__(parent)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)    # 无帮助按钮
        self.setWindowFlag(Qt.MSWindowsFixedSizeDialogHint, True)    # 窗体大小固定

        self.edit_area = QTextEdit(self)
        self.save_button = QPushButton(u'保存', self)
        self.cancel_button = QPushButton(u'取消', self)

        self.edit_area.setAcceptRichText(False)
        self.save_button.setCursor(POINT_HAND_CURSOR)
        self.cancel_button.setCursor(POINT_HAND_CURSOR)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        
        widget_layout = QVBoxLayout()
        widget_layout.addWidget(self.edit_area)
        widget_layout.addLayout(button_layout)

        self.setLayout(widget_layout)
        self.resize(widget_layout.sizeHint())
        
 
class MessageBoxSP(MessageBox):
    def __init__(self, parent=None, title='', message='',
                 yes_button='', no_button='', duration=-1, browsers={}):
        super(MessageBoxSP, self).__init__(parent, title, message,
                                           yes_button, no_button, duration)
        self.browsers = browsers
        self.room_url = ''
        self.move(0, 820)    # 弹窗显示在左下方

    def set_url(self, url):
        if url:
            self.room_url = url
            self.yes_button.clicked.disconnect()
            self.yes_button.clicked.connect(self.open_url_event)

    def open_url_event(self):   # 按钮事件处理器，打开链接
        if self.room_url:
            for bs_name in self.browsers:
                browser_open_url(bs_name, self.room_url)
            #browser_open_url('Chrome', r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe', self.room_url)
            #browser_open_url('QQBrowser', r'D:\QQBrowser\QQBrowser.exe', self.room_url)            
        self.close()


class ProcessDanmuServerDataSP(ProcessDanmuServerData):    # 只处理广播消息
    def __init__(self, queue_data, queue_message=None,
                 queue_revc_order=None, queue_send_order=None):
        super(ProcessDanmuServerDataSP, self).__init__(
            queue_data, queue_message, queue_revc_order, queue_send_order)
        self.show_function = {
            'loginres': self.recv_loginres,
            'keeplive': self.recv_keeplive,
            'mrkl': self.recv_keeplive,
            #'chatmsg': self.show_chatmsg,
            #'uenter': self.show_uenter,
            'spbc': self.show_spbc,
            'bgbc': self.show_bgbc,
            'anbc': self.show_anbc,
            #'newblackres': self.show_newblackres,
            #'dgb': self.show_dgb,
            #'bc_buy_deserve': self.show_deserve,
            #'blab': self.show_blab,
            'rnewbc': self.show_rnewbc,
            'rss': self.show_rss,
            'error': self.show_error,
            'cthn': self.show_cthn,
            'ssd': self.show_ssd,
            #'ranklist': self.show_ranklist,
            #'frank': self.show_frank,
            #'fswrank': self.show_frank,
            #'noble_num_info': self.show_noble_num_info,
            #'online_noble_list': self.show_online_noble_list,
            #'setadminres': self.show_setadminres,
        }

# 使用指定浏览器，打开指定url
def browser_open_url(browser, url):
    try:
        webbrowser.get(browser).open(url)
    except Exception as exc:
        pass
        
    
if __name__ == '__main__':
    app = DYApplication(sys.argv)    
       
    win = DisplayWindowSP()    # 创建主窗体       
    win.show()    # 居中显示主窗体 

    sys.exit(app.exec_())
