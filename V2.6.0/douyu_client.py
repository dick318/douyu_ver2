#!/usr/bin/python3
# -*- coding: utf-8 -*-

# filename: douyu_client.py
# version: 1.0.0
# date: 2018-03-29
# last date: 2018-09-08
# os: windows


import json
import logging
import os
import pickle
import re
import socket
import sqlite3
import time
import urllib.request
import webbrowser

from queue import Queue
from threading import Thread, Lock, Event

from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QUrl
from PyQt5.QtMultimedia import QMediaPlayer, QMediaPlaylist, QMediaContent
from PyQt5.QtGui import QPixmap, QColor, QIcon


# 创建日志的logger
LOG_FORMATTER = logging.Formatter(
    '[%(asctime)s][%(levelname)s]: <File: %(filename)s, ' +
    'Line: %(lineno)d, Func: %(funcName)s> %(message)s')    # 定义记录日志的信息格式
WARNING_LOG = logging.FileHandler('WARNING.log')    # 记录警告信息，不影响软件运行
WARNING_LOG.setFormatter(LOG_FORMATTER)
WARNING_FILTER = logging.Filter('WARNING')
WARNING_LOG.addFilter(WARNING_FILTER)

ERROR_LOG = logging.FileHandler('ERROR.log')    # 记录错误信息，会影响软件运行，一般是软件的bug
ERROR_LOG.setFormatter(LOG_FORMATTER)
ERROR_FILTER = logging.Filter('ERROR')
ERROR_LOG.addFilter(ERROR_FILTER)

PRINT_FORMATTER = logging.Formatter('%(message)s')    # 定义控制台的信息格式
PRINT_LOG = logging.StreamHandler()    # 控制台，显示所有信息
PRINT_LOG.setFormatter(PRINT_FORMATTER)

LOGGER = logging.getLogger()
LOGGER.addHandler(WARNING_LOG)
LOGGER.addHandler(ERROR_LOG)
#LOGGER.addHandler(PRINT_LOG)    # 输出所有信息到控制台!!

WARNING_LOGGER = logging.getLogger('WARNING')
ERROR_LOGGER = logging.getLogger('ERROR')
PRINT_LOGGER = logging.getLogger('PRINT')
PRINT_LOGGER.setLevel(logging.DEBUG)

def exception_message(exc):    # 返回关于异常的信息
    return str(exc.__class__.__name__) + ': ' + str(exc)


from douyu_client_gui import *
import douyu_database_manage
import douyu_server_data_process as data_process
import douyu_server_data_receive as data_receive


# 关于软件的说明
ABOUT_SOFTWARE = (u'Design by 枫轩\n'
                  u'当前版本：2.6.0(2018-09-08)\n'
                  u'联系方式：990761629(QQ)')

# 定义各文件夹和文件的名称
PROGRAM_CONFIG_FOLDER = 'ProgramConfig'    # 保存程序配置文件的文件夹
CONFIG_FILE = 'UserConfig'    # 保存用户设置的文件
ICON_FILE = 'Icon.ico'    # 图标文件
OPEN_REMIND_FILE = 'OpenRemind.wav'    # 开播提醒铃声文件
TITLE_REMIND_FILE = 'TitleRemind.wav'    # 修改标题提醒铃声文件
GIFT_REMIND_FILE = 'GiftRemind.wav'    # 抢宝箱提醒铃声文件
GIFT_DICT_FILE = 'GiftDict'    # 保存礼物ID与名称的文件

EMOTION_FOLDER = 'emotion'    # 保存斗鱼表情的文件夹
NOBLE_FOLDER = 'noble'    # 保存贵族图标的文件夹
USER_LEVEL_FOLDER = 'user_level'    # 保存用户等级图标的文件夹
ANCHOR_LEVEL_FOLDER = 'anchor_level'    # 保存主播等级图标的文件夹
CLIENT_FOLDER = 'client'    # 保存客户端类型图标的文件夹

USERDATA_FOLDER = 'UserData'    # 保存用户数据的文件夹
DATABASE_FOLDER = 'Database'    # 保存数据库文件的文件夹
OWNER_AVATAR_FOLDER = 'OwnerAvatar'    # 保存直播间主播头像的文件夹
ROOM_CONFIG_FOLDER = 'RoomConfig'    # 保存直播间设置文件的文件夹

# 构建主窗体
class MainWindow(MainWindowUi):
    process_message_signal = pyqtSignal(dict)    # 处理弹幕服务器消息的信号
    update_details_signal = pyqtSignal(dict)    # 更新直播间信息的信号
    record_warn_signal = pyqtSignal(dict)    # 处理记录线程消息的信号
    query_result_signal = pyqtSignal(dict)    # 显示查询结果的信号
    
    def __init__(self):
        super(MainWindow, self).__init__()

        # 各文件的路径
        self.emotion_path = os.path.join(PROGRAM_CONFIG_FOLDER, EMOTION_FOLDER)
        self.noble_path = os.path.join(PROGRAM_CONFIG_FOLDER, NOBLE_FOLDER)
        self.config_file_path = os.path.join(PROGRAM_CONFIG_FOLDER, CONFIG_FILE)
        self.icon_file_path = os.path.join(PROGRAM_CONFIG_FOLDER, ICON_FILE)
        self.open_remind_sound_path = os.path.join(PROGRAM_CONFIG_FOLDER, OPEN_REMIND_FILE)
        self.title_remind_sound_path = os.path.join(PROGRAM_CONFIG_FOLDER, TITLE_REMIND_FILE)
        self.gift_remind_sound_path = os.path.join(PROGRAM_CONFIG_FOLDER, GIFT_REMIND_FILE)
        self.gift_dict_file_path = os.path.join(PROGRAM_CONFIG_FOLDER, GIFT_DICT_FILE)
        
        self.database_path = os.path.join(USERDATA_FOLDER, DATABASE_FOLDER)
        self.owner_avatar_path = os.path.join(USERDATA_FOLDER, OWNER_AVATAR_FOLDER)
        self.room_config_path = os.path.join(USERDATA_FOLDER, ROOM_CONFIG_FOLDER)

        if not os.path.isdir(PROGRAM_CONFIG_FOLDER):    # 保存程序配置文件的文件夹不存在则创建
            os.mkdir(PROGRAM_CONFIG_FOLDER)
        if not os.path.isdir(USERDATA_FOLDER):    # 保存用户数据的文件夹不存在则创建
            os.mkdir(USERDATA_FOLDER)
        if not os.path.isdir(self.database_path):    # 保存数据库文件的文件夹不存在则创建
            os.mkdir(self.database_path)        
        if not os.path.isdir(self.owner_avatar_path):    # 保存主播头像的文件夹不存在则创建
            os.mkdir(self.owner_avatar_path)
        if not os.path.isdir(self.room_config_path):    # 保存直播间设置文件的文件夹不存在则创建
            os.mkdir(self.room_config_path)
            
        # 创建主窗体图标和托盘图标
        self.tray_icon = TrayIcon(self)
        if os.path.exists(self.icon_file_path):
            self.default_icon = QIcon(self.icon_file_path)    # 未连接的图标
        else:    # 图标不存在则显示固定图标
            pixmap = QPixmap(12, 12)
            pixmap.fill(QColor('#1E87F0'))
            self.default_icon = QIcon(pixmap)        
        self.room_icon = self.default_icon    # 成功连接后的图标
        self.tooltip = u'未连接'    # 鼠标放在托盘图标上时显示的文字

        # 设置主窗体图标和托盘图标
        self.setWindowIcon(self.default_icon)
        self.setWindowTitle(self.tooltip)
        self.tray_icon.setIcon(self.default_icon)
        self.tray_icon.setToolTip(self.tooltip)
        self.tray_icon.show()
        # 创建并设置直播间默认头像
        self.default_avatar = QPixmap(150, 150)    
        self.default_avatar.fill(QColor('#1E87F0'))
        self.topbar_widget.set_owner_avatar(self.default_avatar)
        
        self.room_id = ''    # 直播间号
        self.room_owner = ''    # 主播名称
        self.last_rid = ''    # 上次连接的直播间号
        self.last_title = ''    # 直播间上一个标题
        self.douyu_url = 'https://www.douyu.com/'    # 斗鱼首页网址
        self.room_details_url = 'http://open.douyucdn.cn/api/RoomApi/room/'    # 获取直播间详细信息的url

        # 创建线程间传递数据的队列        
        self.queue_rid_order = None    # 主UI线程与接收数据线程间的队列，传递直播间号或命令给接收数据线程
        self.queue_server_data = None    # 接收数据线程与处理数据线程间的队列，传递接收到的服务器数据给处理数据线程
        self.queue_message_data = None    # 触发显示线程与处理数据线程间的队列，传递提取到的消息数据给触发显示线程
        self.queue_order_except_1 = None    # 接收数据线程与处理数据线程间的队列, 传递关闭命令和程序异常消息
        self.queue_order_except_2 = None    # 处理数据线程与主UI线程间的队列, 传递关闭命令和程序异常消息        
        self.queue_record_data = None    # 主UI线程与数据库记录数据线程间的队列，传递需记录的数据
        self.queue_details_order = None    # 主UI线程与获取直播间详细信息线程间的队列，传递命令或直播间号给获取信息线程

        self.lock_display = Lock()    # 主UI线程中的显示程序与触发显示线程中的触发程序互锁
        self.event_display = Event()    # 协调主UI线程中的显示程序与触发显示线程中的触发程序
        self.receive_server_data = None    # 接收弹幕服务器数据线程
        self.process_server_data = None    # 处理数据线程
        self.run_display_message = True    # 触发显示线程运行控制位
        self.run_get_details = True    # 获取直播间详细信息线程运行控制位
        self.run_record_message = True    # 记录数据线程运行控制位

        # 定义标志位
        self.is_error = False    # 是否发生异常
        self.restart = False    # 是否进行重启
        self.is_connected = False    # 是否处于正常连接状态
        self.connect_triggered = False    # 是否已触发连接
        self.new_record = True    # 是否启动新的记录线程
        self.can_refresh_details = True    # 是否能更新直播间信息
        self.can_change_config = True    # 是否处理配置变更信号
        self.stop_query = False    # 是否停止查询

        # 定义各文本显示框中显示消息的类型
        self.danmu_message_type = ('chatmsg', 'uenter', 'newblackres', 'blab', 'setadminres')    # 弹幕文本框显示的消息类型列表
        self.gift_message_type = ('dgb',)    # 礼物文本框显示的消息类型列表
        self.broadcast_message_type = ('spbc', 'anbc', 'rnewbc', 'cthn', 'ssd')    # 广播文本框显示的消息类型列表
        self.list_message_type = ('ranklist', 'frank', 'fswrank', 'noble_num_info', 'online_noble_list')    # 榜单窗体显示的消息类型
        self.all_message_type = (self.danmu_message_type +
                                 self.gift_message_type +
                                 self.broadcast_message_type +
                                 self.list_message_type +
                                 ('rss', 'error', 'loginres', 'keeplive'))

        self.client_dict = {'0': u'浏', '1': u'安', '2': u'苹', '14': u'电'}
        self.noble_dict = {'1': u'骑', '2': u'子', '3': u'伯', '4': u'公',
                           '5': u'王', '6': u'皇', '7': u'侠'}

        self.gift_dict_saved = {}    # 保存在文件中的直播间内的礼物ID与对应的礼物名称
        self.room_gift = {}    # 用于存放直播间内的礼物ID与对应的礼物名称
        self.room_gift.update(data_process.GIFT_NAME_DICT)

        # 文本框的显示样式：文本间距和颜色
        self.message_css = ('<style type="text/css">\n'
                            'p { margin-top:6px; margin-bottom:6px; margin-left:0px; margin-right:0px; }\n'
                            '.time, .rid, .black { color:#000000; }\n'    # 黑色
                            '.nn, .dnic, .snic, .sn, .dn, .gvnk, .donk, .unk, .ss_1, .onk { color:#2B94FF; }\n'    # 蓝色
                            '.newblackres_txt, .endtime, .ss_0, .red_txt { color:#FF0000; }\n'    # 红色
                            '.txt, .grey { color:#888888; }\n'    # 灰色
                            '.gn, .hits, .noble, .content, .orange_txt { color:#FF5500; }\n'    # 橙色
                            '.ct { color:#000000; }\n'    # 黑色
                            '.nl { color:#FFFFFF; background-color:#FF5500; }\n'    # 橙色
                            '.bnn { color:#FFFFFF; background-color:#FF69B4; }\n'    # 粉色
                            '.level { color:#FFFFFF; background-color:#2B94FF; }\n'    # 蓝色
                            '.rg { color:#FFFFFF; background-color:#7AC84B; }\n'    # 绿色
                            '.txt_col_0 { color:#2C3E50; }\n'    # 黑色
                            '.txt_col_1 { color:#FF0000; }\n'    # 红色
                            '.txt_col_2 { color:#1E87F0; }\n'    # 蓝色
                            '.txt_col_3 { color:#7AC84B; }\n'    # 绿色
                            '.txt_col_4 { color:#FF7F00; }\n'    # 橙色
                            '.txt_col_5 { color:#9B39F4; }\n'    # 紫色
                            '.txt_col_6 { color:#FF69B4; }\n'    # 粉色
                            '</style>')
        
        # 设置记录消息类型单选框中的值对应的消息类型
        self.message_type_dict = {0: 'chatmsg', 1: 'uenter', 2: 'newblackres',
                                  3: 'blab', 4: 'setadminres', 5: 'dgb',
                                  6: 'spbc', 7: 'anbc', 8: 'rnewbc',
                                  9: 'cthn', 10: 'ssd', 11: 'rss'}

        # 定义数据库的各类型消息的表头
        self.table_chatmsg = ('time INT', 'type TEXT', 'rid TEXT', 'ct TEXT',
                              'uid TEXT', 'nn TEXT', 'txt TEXT', 'level TEXT',
                              'nl TEXT', 'col TEXT', 'rg TEXT', 'bnn TEXT',
                              'bl TEXT', 'brid TEXT', 'noble TEXT', 'client TEXT')
        self.table_uenter = ('time INT', 'type TEXT', 'rid TEXT',
                             'uid TEXT', 'nn TEXT', 'level TEXT',
                             'rg TEXT', 'nl TEXT', 'noble TEXT')
        self.table_newblackres = ('time INT', 'type TEXT', 'rid TEXT',
                                  'otype TEXT', 'sid TEXT', 'did TEXT',
                                  'snic TEXT', 'dnic TEXT', 'endtime TEXT')
        self.table_blab = ('time INT', 'type TEXT', 'uid TEXT',
                           'nn TEXT', 'lbl TEXT', 'bl TEXT',
                           'ba TEXT', 'bnn TEXT', 'rid TEXT')
        self.table_setadminres = ('time INT', 'type TEXT', 'rescode TEXT',
                                  'userid TEXT', 'opuid TEXT', 'rgroup TEXT',
                                  'adnick TEXT', 'rid TEXT', 'level TEXT')        
        self.table_dgb = ('time INT', 'type TEXT', 'rid TEXT', 'gfid TEXT', 
                          'uid TEXT', 'bg TEXT', 'nn TEXT','level TEXT',
                          'hits TEXT', 'rg TEXT', 'nl TEXT', 'bnn TEXT',
                          'bl TEXT', 'brid TEXT', 'noble TEXT', 'gn TEXT')
        self.table_spbc = ('time INT', 'type TEXT', 'sn TEXT', 'dn TEXT',
                           'gn TEXT', 'gc TEXT', 'drid TEXT', 'gb TEXT',
                           'es TEXT', 'gfid TEXT')
        self.table_anbc = ('time INT', 'type TEXT', 'uid TEXT',
                           'unk TEXT', 'drid TEXT', 'donk TEXT',
                           'gvnk TEXT', 'nl TEXT', 'noble TEXT')
        self.table_rnewbc = ('time INT', 'type TEXT', 'uid TEXT',
                           'unk TEXT', 'drid TEXT', 'donk TEXT',
                           'gvnk TEXT', 'nl TEXT', 'noble TEXT')
        self.table_cthn = ('time INT', 'type TEXT', 'rid TEXT',
                           'nl TEXT', 'unk TEXT', 'drid TEXT',
                           'onk TEXT', 'chatmsg TEXT', 'noble TEXT')
        self.table_ssd = ('time INT', 'type TEXT', 'content TEXT', 'rid TEXT', 'trid TEXT')
        self.table_rss = ('time INT', 'type TEXT', 'rid TEXT', 'ss TEXT')

        # 定义各类型消息的字典的键，与数据库的表头顺序对应
        self.message_table_key = {
            'chatmsg': ('time', 'type', 'rid', 'ct', 'uid', 'nn', 'txt', 'level',
                        'nl', 'col', 'rg', 'bnn', 'bl', 'brid', 'noble', 'client'),
            'uenter': ('time', 'type', 'rid', 'uid', 'nn', 'level', 'rg', 'nl', 'noble'),
            'newblackres': ('time', 'type', 'rid', 'otype', 'sid',
                            'did', 'snic', 'dnic', 'endtime'),
            'blab': ('time', 'type', 'uid', 'nn', 'lbl', 'bl', 'ba', 'bnn', 'rid'),
            'setadminres': ('time', 'type', 'rescode', 'userid', 'opuid',
                            'rgroup', 'adnick', 'rid', 'level'),
            'dgb': ('time', 'type', 'rid', 'gfid', 'uid', 'bg', 'nn', 'level',
                    'hits', 'rg', 'nl', 'bnn', 'bl', 'brid', 'noble', 'gn'),
            'spbc': ('time', 'type', 'sn', 'dn', 'gn', 'gc', 'drid', 'gb', 'es', 'gfid'),
            'anbc': ('time', 'type', 'uid', 'unk', 'drid', 'donk', 'gvnk', 'nl', 'noble'),
            'rnewbc': ('time', 'type', 'uid', 'unk', 'drid', 'donk', 'gvnk', 'nl', 'noble'),
            'cthn': ('time', 'type', 'rid', 'nl', 'unk', 'drid', 'onk', 'chatmsg', 'noble'),
            'ssd': ('time', 'type', 'content', 'rid', 'trid'),
            'rss': ('time', 'type', 'rid', 'ss')
        }
        
        self.record_type_list = []    # 要记录的消息类型列表

        # 可保存的用户设置项
        self.set_hide_uenter = False    # 设置是否屏蔽进房消息
        self.set_simple_danmu = False    # 设置是否简化弹幕
        self.set_danmu_care_list = ''    # 设置弹幕关注列表
        self.set_hide_smallgift = False    # 设置是否屏蔽小礼物
        self.set_gift_care_list = ''    # 设置礼物关注列表
        self.set_sprocket_noble_remind = False    # 是否提醒超级火箭和开通贵族宝箱
        self.set_all_gift_remind = False    # 是否提醒所有礼物宝箱
        self.set_gift_remind_blacklist = ''    # 设置礼物宝箱提醒黑名单
        self.set_broadcast_care_list = ''    # 设置广播关注列表
        self.set_stay_top = False    # 设置是否始终保持在其它窗口前端
        self.set_close_frame = 0    # 设置关闭窗口时的操作        
        self.set_auto_enter = False    # 设置是否开播自动打开直播间
        self.set_open_remind = True    # 设置是否开播弹窗提醒
        self.set_open_remind_sound = True    # 设置开启铃声提醒
        self.set_open_remind_duration = 0    # 设置开播弹窗显示时间
        self.set_title_remind = True    # 设置是否修改直播间标题提醒
        self.set_title_remind_sound = True    # 设置开启铃声提醒
        self.set_title_remind_duration = 0    # 设置修改标题提醒显示时间
        self.set_record = False    # 设置是否记录消息
        self.set_record_all = False    # 设置是否记录全部消息
        self.set_record_chatmsg = False    # 设置是否记录弹幕消息
        self.set_record_uenter = False    # 设置是否记录进房消息
        self.set_record_newblackres = False    # 设置是否记录禁言消息
        self.set_record_blab = False    # 设置是否记录粉丝牌升级消息
        self.set_record_setadminres = False    # 设置是否记录任免房管消息
        self.set_record_dgb = False    # 设置是否记录房间礼物
        self.set_record_spbc = False    # 设置是否记录广播礼物
        self.set_record_anbc = False    # 设置是否记录开通贵族
        self.set_record_rnewbc = False    # 设置是否记录续费贵族
        self.set_record_cthn = False    # 设置是否记录喇叭消息
        self.set_record_ssd = False    # 设置是否记录系统广播
        self.set_record_rss = False    # 设置是否记录开关播消息
        self.set_gift_remind_sound = True    # 设置开启铃声提醒
        self.set_gift_remind_duration = 150    # 设置抢宝箱提醒显示时间
        self.set_max_danmu_num = 0    # 设置显示的最大弹幕消息数量
        self.set_max_gift_num = 0    # 设置显示的最大礼物消息数量
        self.set_max_broadcast_num = 0    # 设置显示的最大广播消息数量
        
        self.gift_remind_blacklist = []    # 礼物宝箱提醒黑名单
        self.danmu_care_list = []    # 弹幕关注列表
        self.gift_care_list = []    # 礼物关注列表
        self.broadcast_care_list = []    # 广播关注列表
        # 高级设置项
        self.set_danmu_server = 'openbarrage.douyutv.com'    # 弹幕服务器名
        self.set_danmu_port = '8601'    # 弹幕服务器端口号
        self.set_danmu_group = '-9999'    # 弹幕组

        # 绑定信号与槽
        self.keeplive_timer = QTimer(self)    # 创建用于判断是否发生心跳异常的定时器
        self.keeplive_timer.timeout.connect(self.keeplive_timeout_event)
        self.update_details_timer = QTimer(self)    # 创建用于更新直播间信息的定时器
        self.update_details_timer.timeout.connect(self.update_details_timer_event)
        
        self.process_message_signal.connect(self.process_message_event)
        self.update_details_signal.connect(self.update_details_event)
        self.record_warn_signal.connect(self.record_warn_event)
        self.query_result_signal.connect(self.query_result_event)

        self.operation_signal_connect_slot()
        self.tray_signal_connect_slot()
        self.changed_config_signal_connect_slot()

        self.audition_player = QMediaPlayer(self)    # 试听提示音的播放器
        self.gift_remind_box = MessageBox(self)    # 礼物提醒的弹窗
        self.open_remind_box = MessageBox(self)    # 开播提醒的弹窗
        self.title_remind_box = MessageBox(self)    # 修改标题提醒的弹窗
        self.connect_error_box = MessageBox(self)    # 提醒连接错误消息的弹窗
        self.record_error_box = MessageBox(self)    # 提醒记录消息错误的弹窗
        self.query_error_box = MessageBox(self)    # 提醒查询记录错误的弹窗
        self.about_software_box = MessageBox(self)    # 关于软件信息的弹窗
        
        self.load_user_config()    # 加载保存的用户设置
        
        #self.tray_icon.action_about_software.triggered.disconnect()
        #self.tray_icon.action_about_software.triggered.connect(self.test_event)

#################################################################################################
        
    def test_event(self):    # 用于测试
        #self.show_open_remind('','')
        pass

    def operation_signal_connect_slot(self):    # 操作组件的信号绑定槽
        self.topbar_widget.owner_avatar.clicked.connect(self.open_room_event)
        self.topbar_widget.roomid_enter.textChanged.connect(self.roomid_changed_event)
        self.topbar_widget.connect_danmu.clicked.connect(self.connect_event)        
        self.danmu_widget.danmu_text.textChanged.connect(self.danmu_text_changed_event)
        self.danmu_widget.clear_danmu_button.clicked.connect(self.clear_danmu_event)
        self.danmu_widget.gift_text.textChanged.connect(self.gift_text_changed_event)
        self.danmu_widget.clear_gift_button.clicked.connect(self.clear_gift_event)
        self.broadcast_widget.broadcast_text.textChanged.connect(self.broadcast_text_changed_event)
        self.broadcast_widget.clear_broadcast_button.clicked.connect(self.clear_broadcast_event)
        self.record_widget.record_text.textChanged.connect(self.record_text_changed_event)
        self.record_widget.query_button.clicked.connect(self.query_button_event)
        self.record_widget.reset_button.clicked.connect(self.reset_button_event)
        self.record_widget.clear_record_button.clicked.connect(self.clear_record_event)
        self.config_widget.open_remind_file.clicked.connect(self.audition_sound_event)
        self.config_widget.title_remind_file.clicked.connect(self.audition_sound_event)
        self.config_widget.gift_remind_file.clicked.connect(self.audition_sound_event)
        self.config_widget.save_config_button.clicked.connect(self.save_config_event)
        self.config_widget.default_config_button.clicked.connect(self.recover_default_event)
        self.config_widget.advanced_setting_button.clicked.connect(self.advanced_setting_event)
        self.config_widget.about_software_button.clicked.connect(self.about_software_event)
        self.advanced_setting.confirm_button.clicked.connect(self.setting_confirm_event)
        self.advanced_setting.reset_button.clicked.connect(self.setting_reset_event)
        self.advanced_setting.cancel_button.clicked.connect(self.setting_cancel_event)

    def tray_signal_connect_slot(self):    # 托盘发出的信号绑定槽
        self.tray_icon.activated.connect(self.tray_icon_clicked_event)
        self.tray_icon.action_connect.triggered.connect(self.connect_event)
        self.tray_icon.action_open_room.triggered.connect(self.open_room_event)
        self.tray_icon.action_superrocket_remind.triggered.connect(self.changed_tray_menu_event)
        self.tray_icon.action_all_remind.triggered.connect(self.changed_tray_menu_event)
        self.tray_icon.action_auto_enter.triggered.connect(self.changed_tray_menu_event)
        self.tray_icon.action_open_remind.triggered.connect(self.changed_tray_menu_event)
        self.tray_icon.action_title_remind.triggered.connect(self.changed_tray_menu_event)
        self.tray_icon.action_main_window.triggered.connect(self.show_mainwindow_event)
        self.tray_icon.action_enter_config.triggered.connect(self.enter_config_event)
        self.tray_icon.action_about_software.triggered.connect(self.about_software_event)
        self.tray_icon.action_software_quit.triggered.connect(self.quit_event)
        
    def changed_config_signal_connect_slot(self):    # 设置组件的信号绑定槽
        self.danmu_widget.hide_uenter.clicked.connect(self.changed_config_event)
        self.danmu_widget.simple_danmu.clicked.connect(self.changed_config_event)
        self.danmu_widget.danmu_care_list.textChanged.connect(self.changed_config_event)
        self.danmu_widget.hide_smallgift.clicked.connect(self.changed_config_event)
        self.danmu_widget.gift_care_list.textChanged.connect(self.changed_config_event)
        self.broadcast_widget.superrocket_noble_remind.clicked.connect(self.changed_config_event)
        self.broadcast_widget.all_gift_remind.clicked.connect(self.changed_config_event)
        self.broadcast_widget.gift_remind_blacklist.textChanged.connect(self.changed_config_event)
        self.broadcast_widget.broadcast_care_list.textChanged.connect(self.changed_config_event)
        self.config_widget.close_mainwindow_config.buttonClicked.connect(self.changed_config_event)
        self.config_widget.stay_top.clicked.connect(self.changed_config_event)
        self.config_widget.auto_enter.clicked.connect(self.changed_config_event)
        self.config_widget.open_remind.clicked.connect(self.changed_config_event)
        self.config_widget.open_remind_sound.clicked.connect(self.changed_config_event)        
        self.config_widget.open_remind_duration.valueChanged.connect(self.changed_config_event)
        self.config_widget.title_remind.clicked.connect(self.changed_config_event)
        self.config_widget.title_remind_sound.clicked.connect(self.changed_config_event)
        self.config_widget.title_remind_duration.valueChanged.connect(self.changed_config_event)
        self.config_widget.record_message.clicked.connect(self.changed_config_event)
        self.config_widget.record_all.clicked.connect(self.changed_config_event)
        self.config_widget.record_chatmsg.clicked.connect(self.changed_config_event)
        self.config_widget.record_uenter.clicked.connect(self.changed_config_event)
        self.config_widget.record_newblackres.clicked.connect(self.changed_config_event)
        self.config_widget.record_blab.clicked.connect(self.changed_config_event)
        self.config_widget.record_setadminres.clicked.connect(self.changed_config_event)
        self.config_widget.record_dgb.clicked.connect(self.changed_config_event)
        self.config_widget.record_spbc.clicked.connect(self.changed_config_event)
        self.config_widget.record_anbc.clicked.connect(self.changed_config_event)
        self.config_widget.record_rnewbc.clicked.connect(self.changed_config_event)
        self.config_widget.record_cthn.clicked.connect(self.changed_config_event)
        self.config_widget.record_ssd.clicked.connect(self.changed_config_event)
        self.config_widget.record_rss.clicked.connect(self.changed_config_event)
        self.config_widget.gift_remind_sound.clicked.connect(self.changed_config_event)
        self.config_widget.gift_remind_duration.valueChanged.connect(self.changed_config_event)
        self.config_widget.max_danmu_num.valueChanged.connect(self.changed_config_event)
        self.config_widget.max_gift_num.valueChanged.connect(self.changed_config_event)
        self.config_widget.max_broadcast_num.valueChanged.connect(self.changed_config_event)

    def changed_config_signal_disconnect_slot(self):    # 设置组件的信号取消绑定槽
        self.danmu_widget.hide_uenter.clicked.disconnect(self.changed_config_event)
        self.danmu_widget.simple_danmu.clicked.disconnect(self.changed_config_event)
        self.danmu_widget.danmu_care_list.textChanged.disconnect(self.changed_config_event)
        self.danmu_widget.hide_smallgift.clicked.disconnect(self.changed_config_event)
        self.danmu_widget.gift_care_list.textChanged.disconnect(self.changed_config_event)
        self.broadcast_widget.superrocket_noble_remind.clicked.disconnect(self.changed_config_event)
        self.broadcast_widget.all_gift_remind.clicked.disconnect(self.changed_config_event)
        self.broadcast_widget.gift_remind_blacklist.textChanged.disconnect(self.changed_config_event)
        self.broadcast_widget.broadcast_care_list.textChanged.disconnect(self.changed_config_event)
        self.config_widget.close_mainwindow_config.buttonClicked.disconnect(self.changed_config_event)
        self.config_widget.stay_top.clicked.disconnect(self.changed_config_event)
        self.config_widget.auto_enter.clicked.disconnect(self.changed_config_event)
        self.config_widget.open_remind.clicked.disconnect(self.changed_config_event)
        self.config_widget.open_remind_sound.clicked.disconnect(self.changed_config_event)        
        self.config_widget.open_remind_duration.valueChanged.disconnect(self.changed_config_event)
        self.config_widget.title_remind.clicked.disconnect(self.changed_config_event)
        self.config_widget.title_remind_sound.clicked.disconnect(self.changed_config_event)
        self.config_widget.title_remind_duration.valueChanged.disconnect(self.changed_config_event)
        self.config_widget.record_message.clicked.disconnect(self.changed_config_event)
        self.config_widget.record_all.clicked.disconnect(self.changed_config_event)
        self.config_widget.record_chatmsg.clicked.disconnect(self.changed_config_event)
        self.config_widget.record_uenter.clicked.disconnect(self.changed_config_event)
        self.config_widget.record_newblackres.clicked.disconnect(self.changed_config_event)
        self.config_widget.record_blab.clicked.disconnect(self.changed_config_event)
        self.config_widget.record_setadminres.clicked.disconnect(self.changed_config_event)
        self.config_widget.record_dgb.clicked.disconnect(self.changed_config_event)
        self.config_widget.record_spbc.clicked.disconnect(self.changed_config_event)
        self.config_widget.record_anbc.clicked.disconnect(self.changed_config_event)
        self.config_widget.record_rnewbc.clicked.disconnect(self.changed_config_event)
        self.config_widget.record_cthn.clicked.disconnect(self.changed_config_event)
        self.config_widget.record_ssd.clicked.disconnect(self.changed_config_event)
        self.config_widget.record_rss.clicked.disconnect(self.changed_config_event)
        self.config_widget.gift_remind_sound.clicked.disconnect(self.changed_config_event)
        self.config_widget.gift_remind_duration.valueChanged.disconnect(self.changed_config_event)
        self.config_widget.max_danmu_num.valueChanged.disconnect(self.changed_config_event)
        self.config_widget.max_gift_num.valueChanged.disconnect(self.changed_config_event)
        self.config_widget.max_broadcast_num.valueChanged.disconnect(self.changed_config_event)
        
    def connect_event(self):    # 连接按键的事件处理器
        try:
            self.room_id = self.topbar_widget.roomid_enter.text()    # 取直播间号
            if self.room_id:    # 判断直播间号是否正确
                self.connect_triggered = True
                self.topbar_widget.roomid_enter.setDisabled(True)    # 不可更改直播间号
                self.topbar_widget.connect_danmu.setDisabled(True)         

                self.gift_dict_saved = self.load_gift_dict()    # 加载保存在文件中的礼物ID与名称
                self.room_gift.update(self.gift_dict_saved)
                self.load_room_config()    # 加载直播间设置
                
                # 定义所需队列            
                self.queue_rid_order = Queue()
                self.queue_server_data = Queue()
                self.queue_message_data = Queue()
                self.queue_order_except_1 = Queue()
                self.queue_order_except_2 = Queue()
                
                self.queue_rid_order.put(self.room_id, 1)    # 直播间号发送给接收数据线程
                self.receive_server_data = data_receive.GetDanmuServerData(
                    self.queue_server_data, self.queue_rid_order,
                    self.queue_order_except_1, self.set_danmu_server,
                    self.set_danmu_port, self.set_danmu_group)    # 接收数据线程，心跳线程
                self.process_server_data = data_process.ProcessDanmuServerData(
                    self.queue_server_data, self.queue_message_data,
                    self.queue_order_except_1, self.queue_order_except_2)    # 处理数据线程
                # 启动各线程
                self.start_display_message()
                self.receive_server_data.thread_start()
                self.process_server_data.thread_start()
                self.start_get_details()

            else:
                self.show_mainwindow_event()
                self.show_connect_error(u'请输入直播间号', self.room_id)
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)

    def disconnect_event(self):    # 断开按键的事件处理器
        self.connect_triggered = False
        self.save_room_config()    # 保存直播间设置
        self.topbar_widget.connect_danmu.setDisabled(True)
        self.queue_rid_order.put('close', 1)    # 发送结束消息给接收数据线程        
        
    def start_display_message(self):    # 创建并开启触发显示线程
        self.event_display = Event()
        self.run_display_message = True
        thread_display = Thread(target=self.thread_display_message,
                                args=(self.queue_message_data,
                                      self.queue_order_except_2,
                                      self.event_display))
        thread_display.setDaemon(True)
        thread_display.start()

    def stop_display_message(self):    # 停止触发显示线程
        self.keeplive_timer.stop()    # 停止心跳定时器                    
        self.run_display_message = False
        if self.queue_message_data:
            self.queue_message_data.put({'type':'close', 'from':'main'}, 1)    # 通知结束触发显示线程

    def thread_display_message(self, queue_data, queue_order_except,
                               event_display):    # 触发显示线程
        while self.run_display_message:
            if not queue_order_except.empty():
                try:
                    order_except = queue_order_except.get(0)
                    self.process_message_signal.emit(order_except)
                    event_display.wait()
                except:
                    pass
            else:
                data = queue_data.get(1)
                try:
                    if data['type'] == 'close':
                        break
                    elif data['type'] in self.all_message_type:
                        self.process_message_signal.emit(data)    # 发送信号，触发处理显示消息
                        event_display.wait()
                except Exception as exc:
                    exc_msg = exception_message(exc)
                    ERROR_LOGGER.error(exc_msg)
                    ERROR_LOGGER.error(repr(data))
        PRINT_LOGGER.debug('thread_display_message: closed!')

    def process_message_event(self, data):    # 处理显示消息，由触发显示线程触发        
        try:
            #self.lock_display.acquire()    # 与触发程序互锁，保证处理完一条数据后才允许触发下一次事件
            # 设置了记录消息，则将数据发送给记录消息线程
            if self.set_record and data['type'] in self.record_type_list:
                if self.new_record:
                    self.new_record = False
                    self.start_record_message()    # 开启记录消息线程
                self.queue_record_data.put(data, 1)
                
            if data['type'] == 'closed':
                self.process_disconnected_message()                                
            elif data['type'] == 'loginres':
                self.process_loginres_message()
            elif data['type'] == 'keeplive':
                self.process_keeplive_message()
            elif data['type'] in ['exception', 'error']:
                self.process_error_message(data)
            elif data['type'] in self.danmu_message_type:
                self.display_danmu_message(data)
            elif data['type'] in self.gift_message_type:
                self.display_gift_message(data)
            elif data['type'] in self.broadcast_message_type:
                self.display_broadcast_message(data)
            elif data['type'] in self.list_message_type:
                self.display_list_message(data)
            elif data['type'] == 'rss':
                self.display_rss_message(data)
        finally:
            #self.lock_display.release()    # 释放锁
            self.event_display.set()
            pass

    def process_disconnected_message(self):    # 处理断开连接的消息
        try:
            self.is_error = False            
            self.stop_display_message()    # 停止触发显示线程
            self.stop_get_details()    # 停止更新直播间信息线程
            
            if self.restart:    # 发生错误要自动重启后台线程                
                self.restart = False
                self.connect_event()    # 触发连接事件处理器
            else:    # 是正常断开连接
                self.room_icon = self.default_icon
                self.can_refresh_details = False
                self.update_title_statusbar_tray(self.room_icon, u'已断开连接')    # 设置窗体标题、状态栏、托盘图标说明
                self.is_connected = False
                self.last_title = ''
                self.room_owner = ''                
                self.topbar_widget.connect_danmu.setText(u'连接')    # ‘断开’按钮更改为‘连接’按钮
                self.tray_icon.action_connect.setText(u'连接(%s)' % self.room_id)    # 托盘图标菜单选项更改为‘连接’
                self.topbar_widget.connect_danmu.clicked.disconnect()    # 取消按键事件绑定
                self.tray_icon.action_connect.triggered.disconnect()  
                self.topbar_widget.connect_danmu.clicked.connect(self.connect_event)    # 绑定连接事件处理器
                self.tray_icon.action_connect.triggered.connect(self.connect_event)
                self.topbar_widget.roomid_enter.setEnabled(True)
                self.topbar_widget.connect_danmu.setEnabled(True)
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)

    def process_loginres_message(self):    # 处理登录直播间成功的消息
        try:
            tooltip = u'直播间号：'+self.room_id
            self.statusbar.connect_status.setText(u'连接状态：连接成功')    # 状态栏显示状态
            self.setWindowTitle(tooltip)    # 设置窗体标题
            self.tray_icon.setToolTip(tooltip)    # 设置托盘图标说明文字
            
            self.topbar_widget.connect_danmu.setText(u'断开')    # ‘连接’按钮更改为‘断开’按钮
            self.tray_icon.action_connect.setText(u'断开(%s)' % self.room_id)    # 托盘图标菜单选项更改为‘断开’
            self.topbar_widget.connect_danmu.clicked.disconnect()    # 取消按键事件绑定
            self.tray_icon.action_connect.triggered.disconnect()  
            self.topbar_widget.connect_danmu.clicked.connect(self.disconnect_event)    # 绑定断开连接事件处理器
            self.tray_icon.action_connect.triggered.connect(self.disconnect_event)
            self.topbar_widget.connect_danmu.setEnabled(True)

            self.keeplive_timer.start(45000)    # 开启心跳消息定时器，45秒内没接收到心跳消息就会重启连接
            self.is_connected = True    # 标志处于正常连接状态
            self.can_refresh_details = True
            self.update_details_timer.start(100)    # 登录成功，0.1秒后更新直播间详细信息
            
            # 与上次登录的直播间不同，则关闭上次的记录线程，再重新创建队列和记录线程
            # 避免两个记录线程同时修改同一个数据库导致异常
            if self.room_id != self.last_rid: 
                self.last_rid = self.room_id                
                self.new_record = True
                if self.queue_record_data:
                    self.queue_record_data.put({'type':'close'}, 1)    # 通知结束记录消息线程

            if self.connect_error_box:    # 自动关闭错误提示的弹窗
                self.connect_error_box.set_duration(1)
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
                
    def process_keeplive_message(self):    # 处理心跳消息
        self.keeplive_timer.stop
        self.keeplive_timer.start(45000)    # 重置心跳定时器45s

    def process_error_message(self, data):    # 弹窗提醒错误消息和相应处理
        self.is_error = True
        self.can_refresh_details = False
        self.update_title_statusbar_tray(self.room_icon, data['reason'])    # 设置窗体标题、状态栏、托盘图标说明

        time_str = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(data['time']))
        msg_remind = time_str + '\n' + data['reason']
        self.show_connect_error(msg_remind, self.room_id)    # 弹窗提示错误
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
            
    def display_danmu_message(self, data):    # 在弹幕消息框中显示消息
        if not (data['type'] == 'uenter' and self.set_hide_uenter):    # 判断是否屏蔽消息
            text_html = self.get_display_text(data)
            if text_html:
                self.danmu_widget.danmu_text.append(text_html)    # 在弹幕消息框中显示该条消息
            if (data['type'] in ['chatmsg', 'uenter'] and data['nn'] and
                data['nn'] in self.danmu_care_list):
                self.display_record_message(text_html)

    def display_gift_message(self, data):    # 在礼物消息框中显示房间礼物消息
        if data['gfid'] in self.room_gift:
            data['gn'] = self.room_gift[data['gfid']]        
        if (not self.set_hide_smallgift) or data['bg'] == '1':    # 没有设置‘屏蔽小礼物’或者是大礼物
            text_html = self.get_display_text(data)
            if text_html:
                self.danmu_widget.gift_text.append(text_html)    # 在礼物消息框中显示该条消息
            if data['nn'] and data['nn'] in self.gift_care_list:
                self.display_record_message(text_html)

    def display_broadcast_message(self, data):    # 在广播消息框中显示广播消息
        text_html = None
        if data['type'] == 'spbc':    # 礼物宝箱提醒
            if ((self.set_sprocket_noble_remind and data['es'] == '101') or
                (self.set_all_gift_remind and data['gn'] not in self.gift_remind_blacklist)):
                time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data['time']))
                msg_remind = (u'[%s] %s 赠送给 %s 1个【%s】' %
                              (time_str, data['sn'], data['dn'], data['gn']))
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
        text_html = self.get_display_text(data)
        if text_html:
            self.broadcast_widget.broadcast_text.append(text_html)    # 在广播消息框中显示该条消息
        if data['type'] == 'spbc' and data['sn'] and data['sn'] in self.broadcast_care_list:
            self.display_record_message(text_html)

    def display_list_message(self, data):    # 显示榜单消息
        try:
            update_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data['time']))

            if data['type'] == 'ranklist':    # 显示贡献榜
                self.show_rank_list(self.list_widget.rank_day, data['list_day'], update_time)
                self.show_rank_list(self.list_widget.rank_week, data['list'], update_time)
                self.show_rank_list(self.list_widget.rank_all, data['list_all'], update_time)
                
            elif data['type'] == 'frank':    # 显示粉丝等级总榜
                self.show_fans_list(self.list_widget.fans_all, data['list'],
                                    data['bnn'], data['fc'], update_time)
                
            elif data['type'] == 'fswrank':    # 显示粉丝7天亲密度排行
                self.show_fans_list(self.list_widget.fans_week, data['list'],
                                    data['bnn'], data['fc'], update_time)
                
            elif data['type'] == 'online_noble_list':    # 显示在线贵族
                self.list_widget.noble_window.setTabText(0, u'贵族（%s）' % data['num'])
                self.show_noble_list(self.list_widget.noble_list, data['nl'], update_time)
                
            elif data['type'] == 'noble_num_info':    # 显示在线贵族各等级数量
                noble_msg = []
                for user in data['list']:
                    noble_msg.append(u'[%s]%s' % (self.noble_dict[user['lev']], user['num']))
                self.list_widget.noble_list.label.setText('  '.join(noble_msg))
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(repr(data))

    def show_rank_list(self, show_widget, list_data, update_time):    # 显示一个贡献榜列表信息
        try:
            show_widget.list.setRowCount(len(list_data))
            for i in range(len(list_data)):    # 逐行添加显示信息
                noble = (self.noble_dict[list_data[i]['ne']]
                         if list_data[i]['ne'] in self.noble_dict else '')
                info_widget = UserInfoWidget(
                    str(i+1), noble,
                    list_data[i]['level'], list_data[i]['nickname'],
                    None, str(int(int(list_data[i]['gold'])/100)))
                show_widget.list.setCellWidget(i, 0, info_widget)
            show_widget.time.setText(u'更新时间：' + update_time)
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(repr(list_data))

    def show_fans_list(self, show_widget, list_data, bnn, fc, update_time):    # 显示一个粉丝榜列表信息
        try:
            show_widget.list.setRowCount(len(list_data))
            for i in range(len(list_data)):
                bl = ((' %s ' % list_data[i]['bl'])
                      if len(list_data[i]['bl']) == 1 else list_data[i]['bl'])
                brand = ' (%s) %s ' % (bl, bnn)
                info_widget = UserInfoWidget(
                    str(i+1), None,
                    list_data[i]['lev'], list_data[i]['nn'],
                    brand, str(int(int(list_data[i]['fim'])/100)))
                show_widget.list.setCellWidget(i, 0, info_widget)
                
            show_widget.label.setText(u'粉丝总人数：' + fc)
            show_widget.time.setText(u'更新时间：' + update_time)
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(repr(list_data))

    def show_noble_list(self, show_widget, list_data, update_time):    # 显示一个在线贵族列表信息
        try:
            show_widget.list.setRowCount(len(list_data))
            for i in range(len(list_data)):
                info_widget = UserInfoWidget(
                    None, self.noble_dict[list_data[i]['ne']],
                    list_data[i]['lv'], list_data[i]['nn'],
                    None, None)
                show_widget.list.setCellWidget(i, 0, info_widget)                    
            show_widget.time.setText(u'更新时间：' + update_time)
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(repr(list_data))
                
    def display_rss_message(self, data):    # 在文本框中显示开关播消息，并根据设置进行弹窗提醒
        if data['ss'] == '1':    # 是开播消息
            if self.set_open_remind:    # 设置了开播提醒，则进行弹窗提醒
                time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data['time']))
                msg_remind = u'[%s]\n【%s】开播了！' % (time_str, self.room_owner)
                self.show_open_remind(msg_remind, self.room_id)
            if self.set_auto_enter:    # 设置了开播自动打开直播间，则调用浏览器打开链接
                webbrowser.open(self.douyu_url + self.room_id)
        else:    # 是关播消息
            if self.open_remind_box:    # 关闭存在的开播提醒
                self.open_remind_box.set_duration(1)
                
        text_html = self.get_display_text(data)
        self.display_record_message(text_html)
        self.update_details_timer.stop()
        self.update_details_timer.start(5000)    # 5秒后更新直播间详细信息        

    def keeplive_timeout_event(self):    # 定时器的事件处理器：发生心跳异常
        exc_msg = u'#心跳异常(rid=%s)' % self.room_id
        WARNING_LOGGER.warning(exc_msg)
        self.keeplive_timer.stop()        

        self.is_error = True
        self.can_refresh_details = False
        self.update_title_statusbar_tray(self.room_icon, u'心跳异常')    # 设置窗体标题、状态栏、托盘图标说明
        
        time_error = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime())
        msg_remind = time_error + u'\n心跳异常'
        self.show_connect_error(msg_remind, self.room_id)    # 弹窗提醒
        self.restart = True
        self.disconnect_event()    # 触发断开连接事件处理器

    def update_title_statusbar_tray(self, taskbar_icon, tooltip):    # 更新主窗体标题、状态栏、托盘信息
        self.setWindowTitle(tooltip)
        self.statusbar.connect_status.setText(u'连接状态：' + tooltip)
        self.tray_icon.setIcon(taskbar_icon)
        self.tray_icon.setToolTip(tooltip)

    def get_display_text(self, msg):    # 将字典型消息转换成可用于在文本框中显示的html文本
        try:
            text = []
            time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(msg['time']))
            text.append(u'<span class="time">[%s]</span>' % time_str)
            if msg['type'] == 'chatmsg':    # 弹幕消息
                chat_txt = msg['txt'].replace(' ', '&nbsp;')
                space = '&nbsp;' * (4 - len(msg['level']))    # 在用户等级前后插入空格                
                style = ('style="color:#FF0000"'    # 在关注列表中则改为红色字体
                         if msg['nn'] and (msg['nn'] == self.room_owner or
                                           msg['nn'] in self.danmu_care_list) else '')
                text.append(u'<span class="ct">[%s]</span>' %
                            (self.client_dict[msg['ct']] if msg['ct'] in self.client_dict else '未'))
                if not self.set_simple_danmu:
                    text.append((u'<span class="rg">&nbsp;房&nbsp;</span>') if msg['rg'] == '4' else '')
                    text.append((u'<span class="nl">&nbsp;&nbsp;%s&nbsp;&nbsp;</span>' %
                                 self.noble_dict[msg['nl']]) if msg['nl'] in self.noble_dict else '')
                    bl = ('&nbsp;%s&nbsp;' % msg['bl']) if len(msg['bl']) == 1 else msg['bl']
                    text.append((u'<span class="bnn">&nbsp;(%s)&nbsp;%s&nbsp;</span>' %
                                 (bl, msg['bnn'])) if msg['bnn'] else '')
                text.append(u'<span class="level" >%s</span>' % (space + msg['level'] + space)) 
                text.append(u'<span class="nn" %s>%s：</span>' % (style, msg['nn']))
                text.append(u'<span class="txt_col_%s">%s</span>' % (msg['col'], chat_txt))
                # 插入斗鱼表情
                emot_list = re.findall('\[emot\:dy\d{3}\]', text[-1])
                for emot in emot_list:
                    img_file = os.path.join(self.emotion_path, emot[6:-1] + '.png')
                    if os.path.exists(img_file):
                        img = ('<img class="emotion" src="%s" />' % img_file)
                        text[-1] = text[-1].replace(emot, img)
            elif msg['type'] == 'uenter':    # 用户进房消息
                space = '&nbsp;' * (4 - len(msg['level']))
                style = ('style="color:#FF0000"'
                         if msg['nn'] and (msg['nn'] == self.room_owner or
                                           msg['nn'] in self.danmu_care_list) else '')
                text.append((u'<span class="rg">&nbsp;房&nbsp;</span>') if msg['rg'] == '4' else '')
                text.append((u'<span class="nl">&nbsp;&nbsp;%s&nbsp;&nbsp;</span>' %
                             self.noble_dict[msg['nl']]) if msg['nl'] in self.noble_dict else '')
                text.append(u'<span class="level">%s</span>' % (space + msg['level'] + space))
                text.append(u'<span class="nn" %s>%s</span>' % (style, msg['nn']))
                text.append(u'<span class="txt">进入直播间</span>')
            elif msg['type'] == 'newblackres':    # 禁言消息
                text.append(u'<span class="dnic">%s</span>' % msg['dnic'])
                text.append(u'<span class="newblackres_txt">已被禁言</span>')
                text.append((u'<span class="snic">(%s)</span>' % msg['snic']) if msg['snic'] else '')
                text.append(u'<span class="newblackres_txt">解禁时间:</span>')
                text.append(u'<span class="endtime">%s</span>' % msg['endtime'])
            elif msg['type'] == 'blab':    # 粉丝牌升级消息
                bl = ('&nbsp;%s&nbsp;' % msg['bl']) if len(msg['bl']) == 1 else msg['bl']
                text.append(u'<span class="nn">%s</span>' % msg['nn'])
                text.append(u'<span class="orange_txt">粉丝等级升级到</span>')
                text.append(u'<span class="bnn">&nbsp;(%s)&nbsp;%s&nbsp;</span>' % (bl, msg['bnn']))
            elif msg['type'] == 'setadminres':    # 任免房管消息
                if msg['rgroup'] == '1':
                    res_txt = u'自己解除房管' if msg['opuid'] == '0' else u'被解除房管'
                else:
                    res_txt = u'被任命房管'
                text.append(u'<span class="nn">%s</span>' % msg['adnick'])
                text.append(u'<span class="orange_txt">%s</span>' % res_txt)
            elif msg['type'] == 'dgb':    # 房间礼物消息
                space = '&nbsp;' * (4 - len(msg['level']))
                bl = ('&nbsp;%s&nbsp;' % msg['bl']) if len(msg['bl']) == 1 else msg['bl']
                style = ('style="color:#FF0000"'
                         if msg['nn'] and msg['nn'] in self.gift_care_list else '')
                text.append((u'<span class="rg">&nbsp;房&nbsp;</span>') if msg['rg'] == '4' else '')
                text.append((u'<span class="nl">&nbsp;&nbsp;%s&nbsp;&nbsp;</span>' %
                             self.noble_dict[msg['nl']]) if msg['nl'] in self.noble_dict else '')
                text.append((u'<span class="bnn">&nbsp;(%s)&nbsp;%s&nbsp;</span>' %
                             (bl, msg['bnn'])) if msg['bnn'] else '')
                text.append(u'<span class="level">%s</span>' % (space + msg['level'] + space))
                text.append(u'<span class="nn" %s>%s</span>' % (style, msg['nn']))
                text.append(u'<span class="txt">赠送给主播</span>')
                text.append(u'<span class="gn">%s</span>' % msg['gn'])
                text.append((u'<span class="hits">%s连击</span>' % msg['hits'])
                            if (msg['hits'] != '0' and msg['hits'] != '1') else '')
            elif msg['type'] == 'spbc':    # 广播礼物消息
                style = ('style="color:#FF0000"'
                         if msg['sn'] and msg['sn'] in self.broadcast_care_list else '')
                url = (self.douyu_url + msg['drid']) if msg['drid'] != '0' else ''
                text.append(u'<span class="sn" %s>%s</span>' % (style, msg['sn']))
                text.append(u'<span class="txt">赠送给</span>')
                text.append(u'<span class="dn">%s</span>' % msg['dn'])
                text.append(u'<span class="txt">1个</span>')
                text.append(u'<span class="gn">%s</span>' % msg['gn'])
                text.append((u'<span class="txt">%s直播间：</span>' % ('&nbsp;'*4)) if url else '')
                text.append((u'<a href="%s" class="url">%s</a>' % (url, url)) if url else '')
            elif msg['type'] == 'anbc' or msg['type'] == 'rnewbc':    # 开通或续费贵族消息
                url = (self.douyu_url + msg['drid']) if msg['drid'] != '0' else ''
                do_what = u'开通了' if msg['type'] == 'anbc' else u'续费了'
                if msg['gvnk'] != '' and msg['donk'] != '':
                    text.append(u'<span class="gvnk">%s</span>' % msg['gvnk'])
                    text.append(u'<span class="txt">在</span>')
                    text.append(u'<span class="donk">%s</span>' % msg['donk'])
                    text.append(u'<span class="txt">的房间给</span>')
                    text.append(u'<span class="unk">%s</span>' % msg['unk'])
                    text.append(u'<span class="txt">%s</span>' % do_what)
                    text.append(u'<span class="noble">%s</span>' % msg['noble'])
                elif msg['gvnk'] == '' and msg['donk'] != '':
                    text.append(u'<span class="unk">%s</span>' % msg['unk'])
                    text.append(u'<span class="txt">在</span>')
                    text.append(u'<span class="donk">%s</span>' % msg['donk'])
                    text.append(u'<span class="txt">的房间%s</span>' % do_what)
                    text.append(u'<span class="noble">%s</span>' % msg['noble'])
                elif msg['gvnk'] != '' and msg['donk'] == '':
                    text.append(u'<span class="gvnk">%s</span>' % msg['gvnk'])
                    text.append(u'<span class="txt">给</span>')
                    text.append(u'<span class="unk">%s</span>' % msg['unk'])
                    text.append(u'<span class="txt">%s</span>' % do_what)
                    text.append(u'<span class="noble">%s</span>' % msg['noble'])                    
                elif msg['gvnk'] == '' and msg['donk'] == '':
                    text.append(u'<span class="unk">%s</span>' % msg['unk'])
                    text.append(u'<span class="txt">%s</span>' % do_what)
                    text.append(u'<span class="noble">%s</span>' % msg['noble']) 
                text.append((u'<span class="txt">%s直播间：</span>' % ('&nbsp;'*4)) if url else '')
                text.append((u'<a href="%s" class="url">%s</a>' % (url, url)) if url else '')
            elif msg['type'] == 'cthn':    # 喇叭消息
                url = (self.douyu_url + msg['drid']) if msg['drid'] != '0' else ''
                chat_txt = msg['chatmsg'].replace(' ', '&nbsp;')
                text.append(u'<span class="unk">%s：</span>' % msg['unk'])
                text.append(u'<span class="txt_col_0">%s</span>' % chat_txt)
                text.append(u'<span class="txt_col_0">（来自</span>')
                text.append(u'<span class="onk">%s</span>' % msg['onk'])
                text.append(u'<span class="txt_col_0">的直播间）</span>')
                text.append((u'<span class="txt">%s直播间：</span>' % ('&nbsp;'*4)) if url else '')
                text.append((u'<a href="%s" class="url">%s</a>' % (url, url)) if url else '')
            elif msg['type'] == 'ssd':    # 系统广播消息
                url = (self.douyu_url + msg['trid']) if msg['trid'] != '0' else ''
                content = msg['content'].replace(' ', '&nbsp;')
                text.append(u'<span class="content">%s</span>' % content)
                text.append((u'<span class="txt">%s直播间：</span>' % ('&nbsp;'*4)) if url else '')
                text.append((u'<a href="%s" class="url">%s</a>' % (url, url)) if url else '')                
            elif msg['type'] == 'rss':    # 开关播消息
                text.append(u'<span class="rid">%s</span>' % msg['rid'])
                text.append(u'<span class="%s">%s</span>' %
                            (('ss_1', u'开播') if msg['ss'] == '1' else ('ss_0', u'关播')))            
            return self.message_css + '<p>' + '\n'.join(text) + '</p>'
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(repr(msg))
            return None
        
    # 顶栏组件相关事件处理器
    def roomid_changed_event(self):    # 直播间号输入框的事件处理器，文本一改变就触发
        rid_enter = self.topbar_widget.roomid_enter.text()
        text = u'连接(%s)' % rid_enter if rid_enter else u'连接(空)'
        self.tray_icon.action_connect.setText(text)
        self.room_id = rid_enter
        
    def start_get_details(self):    # 创建并开启获取直播间详细信息的线程
        self.queue_details_order = Queue()
        self.run_get_details = True
        thread_details = Thread(
            target=self.thread_get_details,
            args=(self.queue_details_order, ))
        thread_details.setDaemon(True)
        thread_details.start()

    def stop_get_details(self):    # 停止更新直播间信息线程
        self.update_details_timer.stop()    # 停止更新直播间信息的定时器
        self.run_get_details = False
        if self.queue_details_order:
            self.queue_details_order.put({'type':'close', 'from':'main'}, 1)    # 通知结束获取直播间详细信息线程
                
    def update_details_timer_event(self):    # 定时更新直播间详细信息的处理器：向线程发直播间号以获取对应直播间信息
        self.update_details_timer.stop()
        self.queue_details_order.put({'type':'rid', 'data':self.room_id}, 1)
        self.update_details_timer.start(30000)    # 30秒后再次更新直播间详细信息
        
    def thread_get_details(self, queue_recv):    # 获取直播间详细信息的线程
        avatar_dir = self.owner_avatar_path    # 头像文件存放目录名
        while self.run_get_details:
            status_text = ''
            data_recv = queue_recv.get(1)    # 获取直播间号或命令
            data_send = {}
            if data_recv['type'] == 'close':    # 结束线程
                break
            elif data_recv['type'] == 'rid':    # 获取对应直播间信息
                room_id = data_recv['data']
                socket.setdefaulttimeout(25)    # 设置25秒超时
                url = self.room_details_url + room_id    # 直播间详细信息对应的url
                url_req = urllib.request.Request(url)
                url_req.add_header(
                    'User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ' + 
                    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36')    # 添加浏览器信息                    
                html_dict = None
                try:
                    html = urllib.request.urlopen(url_req)    # 打开url
                    html_str = html.read()    # 获取html数据，json格式的字符串
                    html_dict = json.loads(html_str)    # 转换为python字典格式   
                except socket.timeout as exc:    # 发生超时
                    exc_msg = exception_message(exc) + u'#获取网页html时超时(rid=%s)' % room_id
                    #WARNING_LOGGER.warning(exc_msg)
                    status_text = u'获取直播间详细信息时超时！'
                    data_send = {
                        'type':'error',
                        'data':{'code':'urlerror', 'status':status_text}
                    }                    
                except Exception as exc:
                    exc_msg = exception_message(exc) + u'#获取网页html时发生异常(rid=%s)' % room_id
                    #WARNING_LOGGER.warning(exc_msg)
                    status_text = u'获取直播间详细信息时发生异常！'
                    data_send = {
                        'type':'error',
                        'data':{'code':'urlerror', 'status':status_text}
                    }
                else:
                    if html_dict and type(html_dict) == type(dict()):    # 获取html数据成功，提取信息
                        error = html_dict['error'] if 'error' in html_dict else -1
                        data = html_dict['data'] if 'data' in html_dict else 'ERROR'
                        if error == 0 and data != 'ERROR':    # 成功获取到直播间详细信息
                            try:    # 提取直播间详细信息
                                room_id = data['room_id'] if 'room_id' in data else 'ERROR'    # 直播间号
                                room_thumb = data['room_thumb'] if 'room_thumb' in data else 'ERROR'    # 直播间截图地址
                                avatar = data['avatar'] if 'avatar' in data else 'ERROR'    # 主播头像地址
                                room_name = data['room_name'] if 'room_name' in data else 'ERROR'    # 直播间标题
                                cate_name = data['cate_name'] if 'cate_name' in data else 'ERROR'    # 直播间所属分类名称
                                owner_name = data['owner_name'] if 'owner_name' in data else 'ERROR'    # 主播名称
                                hn = str(data['hn']) if 'hn' in data else 'ERROR'    # 在线热度值
                                fans_num = str(data['fans_num']) if 'fans_num' in data else 'ERROR'    # 直播间关注数
                                room_status = str(data['room_status']) if 'room_status' in data else ''    # 直播间开播状态 1-开播 2-关播
                                start_time = data['start_time'] if 'start_time' in data else 'ERROR'    # 最近开播时间
                                gift = data['gift'] if 'gift' in data else []    # 直播间礼物信息列表
                                room_status = u'开播' if room_status == '1' else u'关播'

                                gift_dict = {}
                                if gift:    # 提取礼物ID和礼物名称，更新到礼物字典中
                                    for item_dict in gift:
                                        gift_dict.update({item_dict['id']:item_dict['name']})
                                    
                            except Exception as exc:
                                exc_msg = exception_message(exc)
                                ERROR_LOGGER.error(exc_msg)
                                ERROR_LOGGER.error(repr(data))

                                data_send = {}
                            else:
                                try:    # 获取主播头像
                                    jpg_name = 'avatar_' + room_id
                                    jpg = urllib.request.urlretrieve(avatar, os.path.join(avatar_dir, jpg_name))    # 获取头像并保存为对应的文件
                                    avatar_jpg = jpg[0]    # 头像文件名和所在目录
                                    urllib.request.urlcleanup()
                                except socket.timeout as exc:    # 发生超时
                                    exc_msg = exception_message(exc) + u'#获取主播头像时超时(rid=%s)' % room_id
                                    #WARNING_LOGGER.warning(exc_msg)
                                    avatar_jpg = ''
                                except Exception as exc:
                                    exc_msg = exception_message(exc) + u'#获取主播头像时发生异常(rid=%s)' % room_id
                                    #WARNING_LOGGER.warning(exc_msg)
                                    avatar_jpg = ''
                                    
                                data_send = {
                                    'type':'details',
                                    'time':time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime()),
                                    'data':{
                                        'avatar':avatar_jpg, 'room_name':room_name,
                                        'cate_name':cate_name, 'room_status':room_status,
                                        'owner_name':owner_name, 'hn':hn,
                                        'fans_num':fans_num, 'start_time':start_time,
                                        'gift':gift_dict, 'room_id':room_id
                                }}

                        else:    # 获取到错误信息
                            status_text = data
                            data_send = {'type':'error', 'data':{'code':error, 'status':status_text}}

                    else:    # 获取失败
                        data_send = {}
                #socket.setdefaulttimeout(None)

            self.update_details_signal.emit(data_send)    # 触发更新直播间信息的事件处理器
        PRINT_LOGGER.debug('thread_get_details: closed!')

    def update_details_event(self, data_recv):    # 更新直播间详细信息的处理器：由获取信息线程触发
        if data_recv:
            if data_recv['type'] == 'error':    # 获取信息时发生错误
                self.statusbar.get_html_status.setText(data_recv['data']['status'])    # 状态栏显示错误信息
                # 101-房间未找到（不存在此房间） 102-房间未激活 103-房间获取错误
                #if data_recv['data']['code'] == 101:
                    #self.disconnect_event()    # 断开连接
                    #self.show_connect_error(data_recv['data']['status'], self.room_id)

            elif data_recv['type'] == 'details': # 成功获取直播间详细信息
                if (data_recv['data']['avatar'] and
                    os.path.exists(data_recv['data']['avatar'])):    # 存在头像文件则显示头像
                    avatar_pixmap = QPixmap(data_recv['data']['avatar'])
                    self.topbar_widget.set_owner_avatar(avatar_pixmap)
                    self.room_icon = QIcon(data_recv['data']['avatar'])
                # 显示各种直播间信息
                self.topbar_widget.set_room_details(data_recv['data']['room_name'],
                                                    data_recv['data']['cate_name'],
                                                    data_recv['data']['room_status'],
                                                    data_recv['data']['owner_name'],
                                                    data_recv['data']['hn'],
                                                    data_recv['data']['fans_num'],                                                    
                                                    data_recv['data']['start_time'])

                self.room_owner = data_recv['data']['owner_name']
                tooltip = (
                    u'标题：' + data_recv['data']['room_name'] + '\n' + 
                    u'主播：' + data_recv['data']['owner_name'] + '\n' + 
                    u'直播间号：' + data_recv['data']['room_id'] + '\n' +
                    u'分类：' + data_recv['data']['cate_name'] + '\n' +
                    u'开播状态：' + data_recv['data']['room_status'] + '\n' +
                    u'热度：' + data_recv['data']['hn'] + '\n' +
                    u'关注：' + data_recv['data']['fans_num'] + '\n' +
                    u'最近开播时间：' + data_recv['data']['start_time'])
                if self.can_refresh_details:
                    self.tray_icon.setIcon(self.room_icon)
                    self.tray_icon.setToolTip(tooltip)    # 设置托盘图标说明文字
                    self.statusbar.get_html_status.setText(u'正常')    # 更新状态栏
                self.room_gift.update(data_recv['data']['gift'])    # 更新礼物名称字典
                if self.room_gift != self.gift_dict_saved:
                    self.gift_dict_saved = {}
                    self.gift_dict_saved.update(self.room_gift)
                    self.save_gift_dict(self.room_gift)

                if data_recv['data']['room_name'] != self.last_title:    # 上一个标题不为空，不是第一次更新直播间信息                
                    if self.last_title:
                        text_html = (self.message_css + '<p>' + data_recv['time'] +
                                     data_recv['data']['room_name'] + '</p>')
                        self.display_record_message(text_html)
                        
                        if self.set_title_remind:    # 设置了标题修改提醒
                            msg_remind = data_recv['time'] + '\n' + data_recv['data']['room_name']
                            self.show_title_remind(msg_remind, data_recv['data']['room_id'])
                    self.last_title = data_recv['data']['room_name']    # 保存标题

    def open_room_event(self):    # 打开直播间
        webbrowser.open(self.douyu_url + self.room_id)

    def load_gift_dict(self):    # 从文件中加载直播间礼物ID与对应的名称
        try:
            with open(self.gift_dict_file_path, 'r') as gift_file:
                gift_list = gift_file.readlines()
            gift_dict = {}
            for each_gift in gift_list:
                each_gift = each_gift.replace('\n', '')
                (gift_id, gift_name) = each_gift.split(':')
                gift_dict[gift_id] = gift_name
            return gift_dict
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            return {}

    def save_gift_dict(self, gift_dict):    # 保存直播间礼物ID与对应的名称到文件
        try:
            gift_list = []
            for gift_id in gift_dict:
                gift_list.append('%s:%s\n' % (gift_id, gift_dict[gift_id]))
            with open(self.gift_dict_file_path, 'w') as gift_file:
                gift_file.writelines(gift_list)
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)

    # 弹幕窗体相关事件处理器
    def clear_danmu_event(self):    # 弹幕消息框的清屏处理器
        self.danmu_widget.danmu_text.clear()

    def danmu_text_changed_event(self):    # 状态栏显示弹幕消息数量
        document = self.danmu_widget.danmu_text.document()
        first_line = document.firstBlock().text()
        line_num = document.blockCount()
        if first_line == '' and line_num <= 1:
            line_num = 0
        self.statusbar.danmu_num.setText(u'弹幕消息数量：' + str(line_num))

    def clear_gift_event(self):    # 礼物消息框的清屏处理器
        self.danmu_widget.gift_text.clear()

    def gift_text_changed_event(self):    # 状态栏显示礼物消息数量
        document = self.danmu_widget.gift_text.document()
        first_line = document.firstBlock().text()
        line_num = document.blockCount()
        if first_line == '' and line_num <= 1:
            line_num = 0
        self.statusbar.gift_num.setText(u'礼物消息数量：' + str(line_num))

    # 广播窗体相关事件处理器
    def clear_broadcast_event(self):    # 广播消息框的清屏处理器
        self.broadcast_widget.broadcast_text.clear()

    def broadcast_text_changed_event(self):    # 状态栏显示广播消息数量
        document = self.broadcast_widget.broadcast_text.document()
        first_line = document.firstBlock().text()
        line_num = document.blockCount()
        if first_line == '' and line_num <= 1:
            line_num = 0
        self.statusbar.broadcast_num.setText(u'广播消息数量：' + str(line_num))
        
    # 记录窗体相关事件处理器
    def create_douyu_table(self, db):    # 创建对应直播间的各类型消息的数据库表格
        db.create('table_chatmsg', self.table_chatmsg)
        db.create('table_uenter', self.table_uenter)
        db.create('table_newblackres', self.table_newblackres)
        db.create('table_blab', self.table_blab)
        db.create('table_setadminres', self.table_setadminres)
        db.create('table_dgb', self.table_dgb)
        db.create('table_spbc', self.table_spbc)
        db.create('table_anbc', self.table_anbc)
        db.create('table_rnewbc', self.table_rnewbc)
        db.create('table_cthn', self.table_cthn)
        db.create('table_ssd', self.table_ssd)
        db.create('table_rss', self.table_rss)

    def start_record_message(self):    # 创建并启动记录消息线程
        self.queue_record_data = Queue()    # 创建用于记录消息线程的队列
        self.run_record_message = True
        th_record = Thread(
            target=self.thread_record_message,
            args=(self.queue_record_data, self.room_id))
        th_record.setDaemon(True)
        th_record.start()    # 开启线程

    def thread_record_message(self, queue, room_id):    # 记录消息的线程
        dbname = 'room_' + room_id + '.db'    # 记录的直播间的数据库名
        database_record = douyu_database_manage.MyDataBase(
            os.path.join(self.database_path, dbname))    # 连接或创建数据库
        self.create_douyu_table(database_record)    # 数据库中不存在表格则创建
        while self.run_record_message:
            data = queue.get(1)
            if data['type'] == 'close':    # 收到结束线程的指令
                break
            else:
                table_name = 'table_' + data['type']    # 记录消息的表名
                try:
                    database_record.insert_dict(table_name, data)    # 记录消息
                except sqlite3.OperationalError as exc:
                    exc_msg = (exception_message(exc) +
                               u'#数据库被锁定，重试记录数据(rid=%s)' % room_id)
                    WARNING_LOGGER.warning(exc_msg)
                    self.record_warn_signal.emit(
                        {'type':'warn',
                         'data':u'数据库被锁定，重试记录数据'})
                    retry_count = 10
                    while retry_count:    # 有其它线程在修改数据库导致数据库锁住，不断重试
                        time.sleep(1)
                        try:
                            database_record.insert_dict(table_name, data)
                            break
                        except sqlite3.OperationalError as exc:
                            retry_count = retry_count - 1
                            if retry_count == 0:
                                exc_msg = (exception_message(exc) +
                                           u'#数据库被锁定，重试记录数据失败(rid=%s)' % room_id)
                                WARNING_LOGGER.warning(exc_msg)
                                self.record_warn_signal.emit(
                                    {'type':'warn',
                                     'data':u'数据库被锁定，重试记录数据失败'})
                                break
                            continue
                        except Exception as exc:
                            exc_msg = (exception_message(exc) +
                                       u'#重试记录数据发生异常(rid=%s)' % room_id)
                            WARNING_LOGGER.warning(exc_msg)
                            self.record_warn_signal.emit(
                                {'type':'warn',
                                 'data':u'重试记录数据发生异常'})
                            break
                        
                except Exception as exc:
                    exc_msg = exception_message(exc)
                    ERROR_LOGGER.error(exc_msg)
                    ERROR_LOGGER.error(repr(table_name) + ' : ' + repr(data))
                    self.record_warn_signal.emit(
                        {'type':'error',
                         'data':u'记录数据线程出现错误'})

        database_record.disconnect()    # 结束线程，断开数据库连接
        PRINT_LOGGER.debug('thread_record_message: closed!')

    def record_warn_event(self, msg_recv):
        self.show_record_error(msg_recv['data'], self.room_id)

    def query_button_event(self):    # 查询按钮的事件处理器
        rid = self.record_widget.room_num.text()        
        if rid:
            self.stop_query = False
            dbname = 'room_' + rid + '.db'    # 要查询的数据库名
            db_path = os.path.join(self.database_path, dbname)
            if os.path.exists(db_path):    # 数据库是否存在
                try:
                    self.record_widget.query_button.setDisabled(True)
                    self.record_widget.result_tips.setText('')
                    # 获取用户设置的查询条件
                    msg_type_dict = {u'弹幕消息':'chatmsg', u'进房消息':'uenter',
                                     u'禁言消息':'newblackres', u'粉丝牌升级':'blab',
                                     u'任免房管':'setadminres', u'房间礼物':'dgb',
                                     u'广播礼物':'spbc', u'开通贵族':'anbc',
                                     u'续费贵族':'rnewbc', u'喇叭消息':'cthn',
                                     u'系统广播':'ssd', u'开关播消息':'rss',
                                     u'用户信息':'user'}
                    condition = {}    # 要查询的条件
                    sele_type = self.record_widget.message_type.currentText()
                    if not self.record_widget.not_begin.isChecked():
                        condition['begin_time'] = self.record_widget.begin_time.dateTime().toTime_t()
                    if not self.record_widget.not_end.isChecked():
                        condition['end_time'] = self.record_widget.end_time.dateTime().toTime_t()
                    client = self.record_widget.view_way.currentText()
                    noble = self.record_widget.noble_level.currentText()
                    uid = self.record_widget.user_id.text()
                    nn = self.record_widget.user_name.text()
                    txt = self.record_widget.danmu_text.text()
                    gn = self.record_widget.gift_name.text()
                    dn = self.record_widget.anthor_name.text()
                    msg_type = msg_type_dict[sele_type]

                    # 不同类型的消息对应不同的查询条件组合
                    condition_dic = {
                        'chatmsg':{'client':client, 'noble':noble, 'uid':uid, 'nn':nn, 'txt':txt}, 
                        'uenter':{'noble':noble, 'uid':uid, 'nn':nn}, 
                        'newblackres':{'did':uid, 'dnic':nn},
                        'blab':{'uid':uid, 'nn':nn},
                        'setadminres':{'userid':uid, 'adnick':nn},
                        'dgb':{'noble':noble, 'uid':uid, 'nn':nn, 'gn':gn}, 
                        'spbc':{'sn':nn, 'gn':gn, 'dn':dn}, 
                        'anbc':{'uid':uid, 'unk':nn, 'donk':dn, 'noble':noble},
                        'rnewbc':{'uid':uid, 'unk':nn, 'donk':dn, 'noble':noble},
                        'cthn':{'unk':nn, 'onk':dn},
                        'ssd':{},
                        'rss':{},
                        'user':{'uid':uid, 'nn':nn}
                    }            
                    condition.update(condition_dic[msg_type])
                    max_result = self.record_widget.max_result.value()    # 查询结果的最大显示数量

                    # 创建查询线程
                    thread_query = Thread(target=self.thread_query_message,
                                          args=(db_path, msg_type, condition, max_result))
                    thread_query.setDaemon(True)
                    thread_query.start()
                except Exception as exc:
                    exc_msg = exception_message(exc)
                    ERROR_LOGGER.error(exc_msg)
                    self.record_widget.query_button.setEnabled(True)
            else: # 数据库不存在则弹窗提醒
                self.show_query_error(u'没有该直播间的数据记录')
        else:
            self.show_query_error(u'直播间号错误')

    def thread_query_message(self, db_path, msg_type, condition, max_result):    # 查询线程
        try:
            database = douyu_database_manage.MyDataBase(db_path)    # 连接数据库
            con = {}
            for key in condition:    # 删除没有内容的条件
                if condition[key] != '':
                    con[key] = condition[key]
            condition = con
            
            if 'noble' in condition and condition['noble'] == u'无贵族':
                condition['noble'] = ''
            if msg_type in self.message_table_key:    # 查询消息
                table_name = 'table_' + msg_type    # 要查询的表名
                result_all = database.query_all(table_name, '*', condition)    # 返回数据元组的列表            
                self.query_result_signal.emit({'type':'result', 'data':str(len(result_all))})    # 显示查询到的记录数量
                if result_all:    # 查询结果不为空
                    key_tuple = self.message_table_key[msg_type]
                    if len(result_all) > max_result:
                        result_all = result_all[-max_result:]
                    for data_tuple in result_all:    # 逐一显示查询到的消息
                        if self.stop_query:    # 是否中断显示查询结果
                            break
                        data_dict = {}
                        for i in range(len(key_tuple)):    # 将数据元组转换成相应的字典格式，以用于转换
                            data_dict.update({key_tuple[i]:data_tuple[i]})                        
                        result_dsp = self.get_display_text(data_dict)
                        self.query_result_signal.emit({'type':'message', 'data':result_dsp})    # 触发显示查询结果
                        time.sleep(0.001)    # 避免主窗体出现未响应
            elif msg_type == 'user':    # 查询用户信息
                result_all = self.query_user_info(database, condition)
                self.query_result_signal.emit({'type':'result', 'data':str(len(result_all))})
                for result in result_all:    # 逐一显示查询到的用户信息
                    if self.stop_query:    # 是否中断显示查询结果
                        break
                    info_str = (u'%s<p>ID: %s%s名称: %s</p>' %
                                (self.message_css, result[0], '&nbsp;'*8, result[1]))
                    self.query_result_signal.emit({'type':'user_info', 'data':info_str})
                    time.sleep(0.001)    # 避免主窗体出现未响应
                
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            self.query_result_signal.emit({'type':'error', 'data':u'查询程序出现错误'})
        finally:
            database.disconnect()
            self.query_result_signal.emit({'type':'finish', 'data':''})
    
    def query_user_info(self, database, condition):    # 查询用户信息   
        args_list = [('table_chatmsg', 'uid', 'nn'), ('table_uenter', 'uid', 'nn'),
                     ('table_dgb', 'uid', 'nn'), ('table_newblackres', 'sid', 'snic'),
                     ('table_newblackres', 'did', 'dnic'), ('table_blab', 'uid', 'nn'),
                     ('table_setadminres', 'userid', 'adnick'), ('table_anbc', 'uid', 'unk'),
                     ('table_rnewbc', 'uid', 'unk')]      
        result_list = []
        for args in args_list:    # 逐一查询各表
            if self.stop_query:    # 是否中断查询
                break
            fields = '%s, %s' % (args[1], args[2])    # 要获取的字段
            cond = {}    # 查询条件
            cond.update(condition)
            if 'uid' in cond:
                cond[args[1]] = cond.pop('uid')
            if 'nn' in cond:
                cond[args[2]] = cond.pop('nn')
            result_all = database.query_all(args[0], fields, cond)
            for result in result_all:    # 去除重复的信息
                if self.stop_query:    # 是否中断查询
                    break
                if result and result not in result_list:
                    result_list.append(result)
        return result_list
        
    def query_result_event(self, data_recv):    # 显示查询结果的事件处理器
        if data_recv['type'] == 'message':
            self.display_record_message(data_recv['data'])
        elif data_recv['type'] == 'result':
            self.record_widget.result_tips.setText(u'查询结果：%s 条记录' % data_recv['data'])
        elif data_recv['type'] == 'user_info':
            self.display_record_message(data_recv['data'])
        elif data_recv['type'] == 'finish':
            self.record_widget.query_button.setEnabled(True)
            self.stop_query = False
        elif data_recv['type'] == 'error':
            self.show_query_error(data_recv['data'])
                        
    def clear_record_event(self):    # 历史记录框右键菜单中的清屏处理器
        self.record_widget.record_text.clear()
        self.record_widget.result_tips.setText('')

    def record_text_changed_event(self):    # 状态栏显示记录消息数量
        document = self.record_widget.record_text.document()
        first_line = document.firstBlock().text()
        line_num = document.blockCount()
        if first_line == '' and line_num <= 1:
            line_num = 0
        self.statusbar.record_num.setText(u'记录消息数量：' + str(line_num))
        
    def display_record_message(self, text_html):    # 在记录文本框中显示消息
        if text_html:
            self.record_widget.record_text.append(text_html)

    def reset_button_event(self):    # 重置按键的事件处理器
        self.record_widget.room_num.setText(self.room_id)
        self.stop_query = True    # 停止查询

    # 设置窗体相关事件处理器和方法
    def load_user_config(self):    # 加载用户设置，不存在则是加载默认设置
        if os.path.exists(self.config_file_path):    # 配置表格存在则取出保存的用户设置数据
            try:
                with open(self.config_file_path, 'rb') as config_file:
                    config_data = pickle.load(config_file)
            except Exception as exc:
                exc_msg = exception_message(exc) + u'#加载用户设置文件失败'
                ERROR_LOGGER.error(exc_msg)
                os.remove(self.config_file_path)
                self.load_default_config()
                self.save_user_config()
            else:
                if not (config_data and                        
                        self.set_config_data_to_windows(config_data) and
                        self.set_config_data_to_variables(config_data) and
                        self.set_advanced_settings(config_data)):
                    exc_msg = u'#加载用户设置失败'
                    ERROR_LOGGER.error(exc_msg)
                    os.remove(self.config_file_path)
                    self.load_default_config()
                    self.save_user_config()

        else:    # 不存在配置表格则新建表格，并将默认设置保存
            self.load_default_config()
            self.save_user_config()

    def load_default_config(self):    # 加载默认设置
        self.set_config_data_to_windows(self.get_default_config_data())
        self.set_config_data_to_variables(self.get_default_config_data())
        self.set_advanced_settings(self.get_default_config_data())
        
    def save_user_config(self):    # 保存用户设置
        try:
            with open(self.config_file_path, 'wb') as config_file:
                pickle.dump(self.get_config_data_from_windows(), config_file)
        except Exception as exc:
            os.remove(self.config_file_path)
            if not os.path.exists(self.config_file_path):
                self.save_user_config()
            else:
                exc_msg = exception_message(exc) + u'#保存用户设置失败'
                ERROR_LOGGER.warning(exc_msg)

    def load_room_config(self):    # 加载直播间的对应设置
        file_path = os.path.join(self.room_config_path, 'config_' + self.room_id)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'rb') as config_file:
                    config_data = pickle.load(config_file)
            except Exception as exc:
                exc_msg = exception_message(exc) + u'#加载直播间设置文件失败(rid=%s)' % self.room_id
                ERROR_LOGGER.error(exc_msg)
                os.remove(file_path)
                self.save_room_config()
            else:
                if not (config_data and                        
                        self.set_config_data_to_windows(config_data) and
                        self.set_config_data_to_variables(config_data) and
                        self.set_advanced_settings(config_data)):
                    exc_msg = u'#加载直播间设置失败(rid=%s)' % self.room_id
                    ERROR_LOGGER.error(exc_msg)
                    os.remove(file_path)
                    self.load_user_config()
                    self.save_room_config()
        else:
            self.save_room_config()

    def save_room_config(self):    # 保存直播间的对应设置
        file_path = os.path.join(self.room_config_path, 'config_' + self.room_id)
        try:
            with open(file_path, 'wb') as config_file:
                pickle.dump(self.get_config_data_from_windows(), config_file)
        except Exception as exc:
            os.remove(file_path)
            if not os.path.exists(file_path):
                self.save_room_config()
            else:
                exc_msg = exception_message(exc) + u'#保存直播间设置失败(rid=%s)' % self.room_id
                ERROR_LOGGER.warning(exc_msg)
            
    def get_default_config_data(self):    # 默认的设置数据
        return {
            'HideUenter': False,
            'SimpleDanmu': False,
            'DanmuCareList': '',
            'HideSmallGift': False,
            'GiftCareList': '',
            'SuperRocketRemind': False,
            'AllGiftRemind': False,
            'GiftRemindBlacklist': '',
            'BroadcastCareList': '',
            'CloseFrame': 0,
            'StayTop': False,
            'AutoEnter': False,                        
            'OpenRemind': True,
            'OpenRemindSound': True,
            'OpenRemindDuration': 0,
            'TitleRemind': True,
            'TitleRemindSound': True,
            'TitleRemindDuration': 0,
            'Record': False,
            'RecordAll': False,
            'RecordChatmsg': False,
            'RecordUenter': False,
            'RecordNewblackres': False,
            'RecordBlab': False,
            'RecordSetadminres': False,
            'RecordDgb': False,
            'RecordSpbc': False,
            'RecordAnbc': False,
            'RecordRnewbc': False,
            'RecordCthn': False,
            'RecordSsd': False,
            'RecordRss': False,
            'GiftRemindSound': True,
            'GiftRemindDuration': 150,
            'MaxDanmuNum': 0,
            'MaxGiftNum': 0,
            'MaxBroadcastNum': 0,
            'DanmuServer': 'openbarrage.douyutv.com',
            'DanmuPort': '8601',
            'DanmuGroup': '-9999',
        }        

    def get_config_data_from_variables(self):    # 从用户设置变量的值获取设置数据
        return {
            'HideUenter': self.set_hide_uenter,
            'SimpleDanmu': self.set_simple_danmu,
            'DanmuCareList': self.set_danmu_care_list,
            'HideSmallGift': self.set_hide_smallgift,
            'GiftCareList': self.set_gift_care_list,
            'SuperRocketRemind': self.set_sprocket_noble_remind,
            'AllGiftRemind': self.set_all_gift_remind,
            'GiftRemindBlacklist': self.set_gift_remind_blacklist,
            'BroadcastCareList': self.set_broadcast_care_list,
            'CloseFrame': self.set_close_frame,
            'StayTop': self.set_stay_top,            
            'AutoEnter': self.set_auto_enter,
            'OpenRemind': self.set_open_remind,
            'OpenRemindSound': self.set_open_remind_sound,
            'OpenRemindDuration': self.set_open_remind_duration,
            'TitleRemind': self.set_title_remind,
            'TitleRemindSound': self.set_title_remind_sound,
            'TitleRemindDuration': self.set_title_remind_duration,
            'Record': self.set_record,
            'RecordAll': self.set_record_all,
            'RecordChatmsg': self.set_record_chatmsg,
            'RecordUenter': self.set_record_uenter,
            'RecordNewblackres': self.set_record_newblackres,
            'RecordBlab': self.set_record_blab,
            'RecordSetadminres': self.set_record_setadminres,
            'RecordDgb': self.set_record_dgb,
            'RecordSpbc': self.set_record_spbc,
            'RecordAnbc': self.set_record_anbc,
            'RecordRnewbc': self.set_record_rnewbc,
            'RecordCthn': self.set_record_cthn,
            'RecordSsd': self.set_record_ssd,
            'RecordRss': self.set_record_rss,
            'GiftRemindSound': self.set_gift_remind_sound,
            'GiftRemindDuration': self.set_gift_remind_duration,
            'MaxDanmuNum': self.set_max_danmu_num,
            'MaxGiftNum': self.set_max_gift_num,
            'MaxBroadcastNum': self.set_max_broadcast_num,
            'DanmuServer': self.set_danmu_server,
            'DanmuPort': self.set_danmu_port,
            'DanmuGroup': self.set_danmu_group,
        }

    def get_config_data_from_windows(self):    # 从设置窗体的各组件获取用户更改后的设置数据
        return {
            'HideUenter': self.danmu_widget.hide_uenter.isChecked(),
            'SimpleDanmu': self.danmu_widget.simple_danmu.isChecked(),
            'DanmuCareList': self.danmu_widget.danmu_care_list.text(),
            'HideSmallGift': self.danmu_widget.hide_smallgift.isChecked(),
            'GiftCareList': self.danmu_widget.gift_care_list.text(),
            'SuperRocketRemind': self.broadcast_widget.superrocket_noble_remind.isChecked(),
            'AllGiftRemind': self.broadcast_widget.all_gift_remind.isChecked(),
            'GiftRemindBlacklist': self.broadcast_widget.gift_remind_blacklist.text(),
            'BroadcastCareList': self.broadcast_widget.broadcast_care_list.text(),
            'CloseFrame': self.config_widget.close_mainwindow_config.checkedId(),
            'StayTop': self.config_widget.stay_top.isChecked(),
            'AutoEnter': self.config_widget.auto_enter.isChecked(),
            'OpenRemind': self.config_widget.open_remind.isChecked(),
            'OpenRemindSound': self.config_widget.open_remind_sound.isChecked(),
            'OpenRemindDuration': self.config_widget.open_remind_duration.value(),
            'TitleRemind': self.config_widget.title_remind.isChecked(),
            'TitleRemindSound': self.config_widget.title_remind_sound.isChecked(),
            'TitleRemindDuration': self.config_widget.title_remind_duration.value(),
            'Record': self.config_widget.record_message.isChecked(),
            'RecordAll': self.config_widget.record_all.isChecked(),
            'RecordChatmsg': self.config_widget.record_chatmsg.isChecked(),
            'RecordUenter': self.config_widget.record_uenter.isChecked(),
            'RecordNewblackres': self.config_widget.record_newblackres.isChecked(),
            'RecordBlab': self.config_widget.record_blab.isChecked(),
            'RecordSetadminres': self.config_widget.record_setadminres.isChecked(),
            'RecordDgb': self.config_widget.record_dgb.isChecked(),
            'RecordSpbc': self.config_widget.record_spbc.isChecked(),
            'RecordAnbc': self.config_widget.record_anbc.isChecked(),
            'RecordRnewbc': self.config_widget.record_rnewbc.isChecked(),
            'RecordCthn': self.config_widget.record_cthn.isChecked(),
            'RecordSsd': self.config_widget.record_ssd.isChecked(),
            'RecordRss': self.config_widget.record_rss.isChecked(),
            'GiftRemindSound': self.config_widget.gift_remind_sound.isChecked(),
            'GiftRemindDuration': self.config_widget.gift_remind_duration.value(),
            'MaxDanmuNum': self.config_widget.max_danmu_num.value(),
            'MaxGiftNum': self.config_widget.max_gift_num.value(),
            'MaxBroadcastNum': self.config_widget.max_broadcast_num.value(),
            'DanmuServer': self.advanced_setting.danmu_server.text(),
            'DanmuPort': self.advanced_setting.danmu_port.currentText(),
            'DanmuGroup': self.advanced_setting.danmu_group.text(),
        }

    def set_config_data_to_variables(self, config_data):    # 根据所提供的配置数据设置用户设置变量的值
        try:
            self.set_hide_uenter = config_data['HideUenter']
            self.set_simple_danmu = config_data['SimpleDanmu']
            self.set_danmu_care_list = config_data['DanmuCareList']
            self.set_hide_smallgift = config_data['HideSmallGift']
            self.set_gift_care_list = config_data['GiftCareList']
            self.set_sprocket_noble_remind = config_data['SuperRocketRemind']
            self.set_all_gift_remind = config_data['AllGiftRemind']
            self.set_gift_remind_blacklist = config_data['GiftRemindBlacklist']
            self.set_broadcast_care_list = config_data['BroadcastCareList']            
            self.set_close_frame = config_data['CloseFrame']
            self.set_stay_top = config_data['StayTop']
            self.set_auto_enter = config_data['AutoEnter']
            self.set_open_remind = config_data['OpenRemind']
            self.set_open_remind_sound = config_data['OpenRemindSound']
            self.set_open_remind_duration = config_data['OpenRemindDuration']
            self.set_title_remind = config_data['TitleRemind']
            self.set_title_remind_sound = config_data['TitleRemindSound']
            self.set_title_remind_duration = config_data['TitleRemindDuration']
            self.set_record = config_data['Record']
            self.set_record_all = config_data['RecordAll']
            self.set_record_chatmsg = config_data['RecordChatmsg']
            self.set_record_uenter = config_data['RecordUenter']
            self.set_record_newblackres = config_data['RecordNewblackres']
            self.set_record_blab = config_data['RecordBlab']
            self.set_record_setadminres = config_data['RecordSetadminres']
            self.set_record_dgb = config_data['RecordDgb']
            self.set_record_spbc = config_data['RecordSpbc']
            self.set_record_anbc = config_data['RecordAnbc']
            self.set_record_rnewbc = config_data['RecordRnewbc']
            self.set_record_cthn = config_data['RecordCthn']
            self.set_record_ssd = config_data['RecordSsd']
            self.set_record_rss = config_data['RecordRss']
            self.set_gift_remind_sound = config_data['GiftRemindSound']
            self.set_gift_remind_duration = config_data['GiftRemindDuration']
            self.set_max_danmu_num = config_data['MaxDanmuNum']
            self.set_max_gift_num = config_data['MaxGiftNum']
            self.set_max_broadcast_num = config_data['MaxBroadcastNum']
            self.set_mainwindow_style()
            self.set_record_type()
            self.trans_config_to_list()
            self.set_max_message()
            return True
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            return False

    def set_config_data_to_windows(self, config_data):    # 根据所提供的配置数据配置设置窗体中各组件的值
        try:
            self.can_change_config = False
            self.danmu_widget.hide_uenter.setChecked(config_data['HideUenter'])
            self.danmu_widget.simple_danmu.setChecked(config_data['SimpleDanmu'])
            self.danmu_widget.danmu_care_list.setText(config_data['DanmuCareList'])
            self.danmu_widget.hide_smallgift.setChecked(config_data['HideSmallGift'])
            self.danmu_widget.gift_care_list.setText(config_data['GiftCareList'])
            self.broadcast_widget.superrocket_noble_remind.setChecked(config_data['SuperRocketRemind'])
            self.broadcast_widget.all_gift_remind.setChecked(config_data['AllGiftRemind'])
            self.broadcast_widget.gift_remind_blacklist.setText(config_data['GiftRemindBlacklist'])
            self.broadcast_widget.broadcast_care_list.setText(config_data['BroadcastCareList'])           
            self.config_widget.close_mainwindow_config.button(config_data['CloseFrame']).setChecked(True)
            self.config_widget.stay_top.setChecked(config_data['StayTop'])
            self.config_widget.auto_enter.setChecked(config_data['AutoEnter'])
            self.config_widget.open_remind.setChecked(config_data['OpenRemind'])
            self.config_widget.open_remind_sound.setChecked(config_data['OpenRemindSound'])
            self.config_widget.open_remind_duration.setValue(config_data['OpenRemindDuration'])
            self.config_widget.title_remind.setChecked(config_data['TitleRemind'])
            self.config_widget.title_remind_sound.setChecked(config_data['TitleRemindSound'])
            self.config_widget.title_remind_duration.setValue(config_data['TitleRemindDuration'])
            self.config_widget.record_message.setChecked(config_data['Record'])
            self.config_widget.record_all.setChecked(config_data['RecordAll'])
            self.config_widget.record_chatmsg.setChecked(config_data['RecordChatmsg'])
            self.config_widget.record_uenter.setChecked(config_data['RecordUenter'])
            self.config_widget.record_newblackres.setChecked(config_data['RecordNewblackres'])
            self.config_widget.record_blab.setChecked(config_data['RecordBlab'])
            self.config_widget.record_setadminres.setChecked(config_data['RecordSetadminres'])
            self.config_widget.record_dgb.setChecked(config_data['RecordDgb'])
            self.config_widget.record_spbc.setChecked(config_data['RecordSpbc'])
            self.config_widget.record_anbc.setChecked(config_data['RecordAnbc'])
            self.config_widget.record_rnewbc.setChecked(config_data['RecordRnewbc'])
            self.config_widget.record_cthn.setChecked(config_data['RecordCthn'])
            self.config_widget.record_ssd.setChecked(config_data['RecordSsd'])
            self.config_widget.record_rss.setChecked(config_data['RecordRss'])
            self.config_widget.gift_remind_sound.setChecked(config_data['GiftRemindSound'])
            self.config_widget.gift_remind_duration.setValue(config_data['GiftRemindDuration'])
            self.config_widget.max_danmu_num.setValue(config_data['MaxDanmuNum'])
            self.config_widget.max_gift_num.setValue(config_data['MaxGiftNum'])
            self.config_widget.max_broadcast_num.setValue(config_data['MaxBroadcastNum'])
            # 设置托盘图标菜单选项的值
            self.tray_icon.action_superrocket_remind.setChecked(config_data['SuperRocketRemind'])
            self.tray_icon.action_all_remind.setChecked(config_data['AllGiftRemind'])
            self.tray_icon.action_auto_enter.setChecked(config_data['AutoEnter'])
            self.tray_icon.action_open_remind.setChecked(config_data['OpenRemind'])
            self.tray_icon.action_title_remind.setChecked(config_data['TitleRemind'])
            self.can_change_config = True
            return True
        except Exception as exc:
            self.can_change_config = True
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            return False

    def set_advanced_settings(self, config_data):    # 根据所提供的配置数据设置高级设置变量的值和组件的值
        try:
            self.advanced_setting.danmu_server.setText(config_data['DanmuServer'])
            self.advanced_setting.danmu_port.setCurrentText(config_data['DanmuPort'])
            self.advanced_setting.danmu_group.setText(config_data['DanmuGroup'])
            self.set_danmu_server = config_data['DanmuServer']
            self.set_danmu_port = config_data['DanmuPort']
            self.set_danmu_group = config_data['DanmuGroup']
            return True
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            return False

    def set_mainwindow_style(self):    # 设置主窗体状态
        state = self.isVisible()
        if self.set_stay_top:    # 设置了始终保持在其它窗口前端
            self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        else:
            self.setWindowFlag(Qt.WindowStaysOnTopHint, False)
        if state:
            self.show()

    def set_record_type(self):    # 设置记录消息的类型列表
        if self.set_record_all:    # 设置记录全部消息
            self.record_type_list = list(self.message_type_dict.values())    # 设置记录消息类型列表
        else:
            record_type_data = (self.set_record_chatmsg,
                                self.set_record_uenter,
                                self.set_record_newblackres,
                                self.set_record_blab,
                                self.set_record_setadminres,
                                self.set_record_dgb,
                                self.set_record_spbc,
                                self.set_record_anbc,
                                self.set_record_rnewbc,
                                self.set_record_cthn,
                                self.set_record_ssd,
                                self.set_record_rss)
            self.record_type_list = []
            for index in range(12):    # 根据勾选框的值设置记录消息类型列表
                if record_type_data[index]:
                    self.record_type_list.append(self.message_type_dict[index])

    def trans_config_to_list(self):    # 将设置的关注或黑名单转换成列表
        self.gift_remind_blacklist = self.set_gift_remind_blacklist.replace(' ', '').split('/')
        self.danmu_care_list = self.set_danmu_care_list.replace(' ', '').split('/')
        self.gift_care_list = self.set_gift_care_list.replace(' ', '').split('/')
        self.broadcast_care_list = self.set_broadcast_care_list.replace(' ', '').split('/')

    def set_max_message(self):    # 设置各消息框的最大消息数量
        self.danmu_widget.danmu_text.document().setMaximumBlockCount(self.set_max_danmu_num)
        self.danmu_widget.gift_text.document().setMaximumBlockCount(self.set_max_gift_num)
        self.broadcast_widget.broadcast_text.document().setMaximumBlockCount(self.set_max_broadcast_num)

    def changed_config_event(self):    # 设置窗体各组件状态更改的事件处理器
        if self.can_change_config:
            self.set_config_data_to_variables(self.get_config_data_from_windows())
            self.tray_icon.action_superrocket_remind.setChecked(self.set_sprocket_noble_remind)
            self.tray_icon.action_all_remind.setChecked(self.set_all_gift_remind)
            self.tray_icon.action_auto_enter.setChecked(self.set_auto_enter)
            self.tray_icon.action_open_remind.setChecked(self.set_open_remind)
            self.tray_icon.action_title_remind.setChecked(self.set_title_remind)

    def changed_tray_menu_event(self):    # 托盘菜单的事件处理器
        self.broadcast_widget.superrocket_noble_remind.setChecked(self.tray_icon.action_superrocket_remind.isChecked())
        self.broadcast_widget.all_gift_remind.setChecked(self.tray_icon.action_all_remind.isChecked())
        self.config_widget.auto_enter.setChecked(self.tray_icon.action_auto_enter.isChecked())
        self.config_widget.open_remind.setChecked(self.tray_icon.action_open_remind.isChecked())
        self.config_widget.title_remind.setChecked(self.tray_icon.action_title_remind.isChecked())
        self.set_config_data_to_variables(self.get_config_data_from_windows())

    def audition_sound_event(self):    # 声音提示试听
        self.audition_player.stop()
        self.audition_player = QMediaPlayer(self)
        sender = self.sender()
        if sender == self.config_widget.open_remind_file:
            self.audition_player.setMedia(
                QMediaContent(QUrl().fromLocalFile(self.open_remind_sound_path)))
        elif sender == self.config_widget.title_remind_file:
            self.audition_player.setMedia(
                QMediaContent(QUrl().fromLocalFile(self.title_remind_sound_path)))
        elif sender == self.config_widget.gift_remind_file:
            self.audition_player.setMedia(
                QMediaContent(QUrl().fromLocalFile(self.gift_remind_sound_path)))
        self.audition_player.play()

    def save_config_event(self):    # ‘保存设置’按键的事件处理器
        self.save_user_config()
        if self.connect_triggered:
            self.save_room_config()

    def recover_default_event(self):    # ‘默认设置’按键的事件处理器
        self.load_default_config()

    def advanced_setting_event(self):    # ‘高级设置’按键的事件处理器
        self.advanced_setting.danmu_server.setText(self.set_danmu_server)
        self.advanced_setting.danmu_port.setCurrentText(self.set_danmu_port)
        self.advanced_setting.danmu_group.setText(self.set_danmu_group)
        self.advanced_setting.show()

    def about_software_event(self):    # 弹窗显示关于程序的信息
        self.show_about_software(ABOUT_SOFTWARE)

    def setting_confirm_event(self):    # 高级设置窗体中的‘确认’按键的事件处理器
        self.set_danmu_server = self.advanced_setting.danmu_server.text()
        self.set_danmu_port = self.advanced_setting.danmu_port.currentText()
        self.set_danmu_group = self.advanced_setting.danmu_group.text()
        self.advanced_setting.hide()

    def setting_reset_event(self):    # 高级设置窗体中的‘重置’按键的事件处理器
        self.advanced_setting.danmu_server.setText('openbarrage.douyutv.com')
        self.advanced_setting.danmu_port.setCurrentIndex(0)
        self.advanced_setting.danmu_group.setText('-9999')

    def setting_cancel_event(self):    # 高级设置窗体中的‘取消’按键的事件处理器
        self.advanced_setting.hide()
        self.advanced_setting.danmu_server.setText(self.set_danmu_server)
        self.advanced_setting.danmu_port.setCurrentText(self.set_danmu_port)
        self.advanced_setting.danmu_group.setText(self.set_danmu_group)

    #托盘相关事件处理器
    def tray_icon_clicked_event(self, event=None):    # 托盘图标点击事件处理器
        if event == 3:    # 鼠标左键事件
            self.show_mainwindow_event()

    def show_mainwindow_event(self):    # 打开主面板
        self.activateWindow()
        if self.isMaximized():
            self.showMaximized()
        else:
            self.showNormal()

    def enter_config_event(self):
        self.tab_window.setCurrentIndex(4)    # 切换到设置窗体
        self.show_mainwindow_event()

    def closeEvent(self, event):    # 主窗体关闭按键事件处理器
        event.ignore()
        if self.set_close_frame:
            self.quit_event()    # 退出程序            
        else:
            self.hide()    # 隐藏主窗体

    def quit_event(self, event=None):    # 完全退出程序
        self.hide()
        self.tray_icon.setVisible(False)
        # 保存设置
        self.save_user_config()
        if self.connect_triggered:
            self.save_room_config()
        # 停止所有后台线程
        if self.queue_rid_order:
            self.queue_rid_order.put('close', 1)
        self.stop_display_message()
        self.stop_get_details()
        if self.queue_record_data:
            self.run_record_message = False
            self.queue_record_data.put({'type':'close'}, 1)
        self.destroy()
        sys.exit()
        
    # 弹窗事件处理
    def show_gift_remind(self, message, roomid):    # 礼物提醒的弹窗
        self.gift_remind_box = MessageBox(self, u'抢宝箱提醒', message, u'抢宝箱',
                                          u'算了', self.set_gift_remind_duration)
        self.gift_remind_box.set_url(self.douyu_url + roomid)
        self.gift_remind_box.set_sound(self.gift_remind_sound_path, 0)
        self.gift_remind_box.set_stay_top(True)
        if self.set_gift_remind_sound:
            self.gift_remind_box.play_sound()
        self.gift_remind_box.setWindowFlag(Qt.WindowCloseButtonHint, False)
        self.gift_remind_box.show()

    def show_open_remind(self, message, roomid):    # 开播提醒的弹窗
        self.open_remind_box.setParent(None)
        title = u'开播提醒(%s)' % roomid
        self.open_remind_box = MessageBox(self, title, message, u'快去看',
                                          u'算了', self.set_open_remind_duration)
        self.open_remind_box.set_url(self.douyu_url + roomid)
        self.open_remind_box.set_sound(self.open_remind_sound_path, 1)
        self.open_remind_box.set_stay_top(True)
        if self.set_open_remind_sound:
            self.open_remind_box.play_sound()
        self.open_remind_box.show()

    def show_title_remind(self, message, roomid):    # 修改标题提醒的弹窗
        self.title_remind_box.setParent(None)
        title = u'修改标题提醒(%s)' % roomid
        self.title_remind_box = MessageBox(self, title, message, u'', u'确定',
                                           self.set_title_remind_duration)
        self.title_remind_box.set_sound(self.title_remind_sound_path, 0)
        self.title_remind_box.set_stay_top(True)
        if self.set_title_remind_sound:
            self.title_remind_box.play_sound()
        self.title_remind_box.show()

    def show_connect_error(self, message, roomid):    # 提醒连接错误的弹窗
        self.connect_error_box.setParent(None)
        title = u'连接异常(%s)' % roomid
        self.connect_error_box = MessageBox(self, title, message, u'', u'确定')
        self.connect_error_box.set_stay_top(True)
        self.connect_error_box.show()

    def show_record_error(self, message, roomid):    # 提醒记录消息错误的弹窗
        self.record_error_box.setParent(None)
        title = u'记录消息异常(%s)' % roomid
        self.record_error_box = MessageBox(self, title, message, u'', u'确定')
        self.record_error_box.show()
        
    def show_query_error(self, message):    # 提醒查询错误的弹窗
        self.query_error_box.setParent(None)
        self.query_error_box = MessageBox(self, u'查询记录异常', message, u'', u'确定')
        self.query_error_box.show()

    def show_about_software(self, message):    # 关于软件的弹窗
        self.about_software_box.setParent(None)
        self.about_software_box = MessageBox(self, u'关于软件', message, u'', u'确定')
        self.about_software_box.show()
        

# 构建弹窗
class MessageBox(MessageBoxUi):
    def __init__(self, parent=None, title='', message='',
                 yes_button='', no_button=u'关闭', duration=-1):
        super(MessageBox, self).__init__(parent)
        self.setModal(False)    # 设置为非阻塞模式
        self.setWindowTitle(title)
        self.message_text.setText(message)
        self.yes_button.setText(yes_button)
        self.no_button.setText(no_button)
        if not yes_button:           
            self.yes_button.hide()
        self.yes_button.clicked.connect(self.close_event)
        self.no_button.clicked.connect(self.close_event)
        self.duration_timer = QTimer(self)    # 创建弹窗自毁定时器
        self.duration_timer.timeout.connect(self.close_event)
        self.set_duration(duration)
        self.room_url = ''
        self.player = QMediaPlayer(self)    # 创建提示音播放器
        self.adjustSize()
        
    def open_url_event(self):    # 浏览器打开url
        if self.room_url:
            webbrowser.open(self.room_url)
        self.close()
        
    def set_duration(self, duration):    # 设置弹窗自毁的时间
        if duration > 0:
            self.duration_timer.start(int(duration * 1000))    # 开启计时

    def set_url(self, url):    # 设置可用于打开的url
        if url:
            self.room_url = url
            self.yes_button.clicked.disconnect()
            self.yes_button.clicked.connect(self.open_url_event)

    def set_sound(self, file, mode):    # 设置提示音
        playlist = QMediaPlaylist(self)
        playlist.addMedia(QMediaContent(QUrl().fromLocalFile(file)))
        playlist.setPlaybackMode(mode)
        self.player.setPlaylist(playlist)
        
    def play_sound(self):    # 播放提示音
        self.player.play()

    def set_stay_top(self, flag):    # 设置弹窗保持置顶
        self.setWindowFlag(Qt.WindowStaysOnTopHint, flag)

    def show_modal(self):    # 阻塞模式显示弹窗
        self.setModal(True)
        self.show()

    def close_event(self, event=None):
        self.close()

    def closeEvent(self, event):
        event.ignore()
        self.setParent(None)
        self.player.stop()    # 关闭声音提醒
        self.destroy()    # 关闭弹窗


if __name__ == '__main__':
    app = DYApplication(sys.argv)       
    
    win = MainWindow()    # 创建主窗体    
    win.show()    # 显示主窗体
    
    sys.exit(app.exec_())
