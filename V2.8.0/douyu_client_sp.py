#!usr/bin/python3
# -*- coding: utf-8 -*-

# filename: douyu_sp.py
# version: 1.0.0
# date: 2018-04-06
# last date: 2018-10-28
# os: windows

import os
import sys
import time
import webbrowser

from PyQt5.QtCore import Qt

from douyu_client_gui import DYApplication
from douyu_client import MainWindow, MessageBox, ABOUT_SOFTWARE, PROGRAM_CONFIG_FOLDER

# 关于软件的说明
about = ABOUT_SOFTWARE.split('\n')
about[1] += 'special'
ABOUT_SOFTWARE_SP = '\n'.join(about)


# 抢宝箱时同时打开两个浏览器
class DisplayWindowSP(MainWindow):
    def __init__(self):
        super(DisplayWindowSP, self).__init__()
        self.danmu_widget.simple_danmu.setText(u'屏蔽弹幕')
        self.broadcast_widget.broadcast_care_list_label.setText(u'主播黑名单：')
        self.broadcast_widget.broadcast_care_list.setToolTip(
            u'主播名称，用斜杠"/"分割，\n主播的礼物消息不再弹窗提醒')
        self.browser_list_file = os.path.join(PROGRAM_CONFIG_FOLDER, 'BrowserList')
        self.browser_list = self.load_browser_list()
        self.config_widget.save_config_button.clicked.connect(self.load_browser_event)

    def display_danmu_message(self, data):    # 在弹幕消息框中显示消息
        if not ((data['type'] == 'uenter' and self.set_hide_uenter) or
                (data['type'] == 'chatmsg' and self.set_simple_danmu)):    # 判断是否屏蔽消息
            text_html = self.get_display_text(data)
            if text_html:
                self.danmu_widget.danmu_text.append(text_html)    # 在弹幕消息框中显示该条消息
            if (data['type'] in ['chatmsg', 'uenter'] and data['nn'] and
                data['nn'] in self.danmu_care_list):
                self.display_record_message(text_html)

    def display_broadcast_message(self, data):    # 在广播消息框中显示广播消息
        text_html = self.get_display_text(data)
        if text_html:
            self.broadcast_widget.broadcast_text.append(text_html)    # 在广播消息框中显示该条消息
            
        if data['type'] == 'spbc' or data['type'] == 'bgbc':    # 礼物宝箱提醒
            if ((data['type'] == 'spbc' and self.set_sprocket_noble_remind and data['es'] == '101') or
                (self.set_all_gift_remind and data['gn'] not in self.gift_remind_blacklist and
                 data['dn'] not in self.broadcast_care_list)):
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
