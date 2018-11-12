#!/usr/bin/python3
# -*- coding: utf-8 -*-

# filename: douyu_client_gui.py
# version: 1.0.0
# date: 2018-03-26
# last date: 2018-09-08
# os: windows


import datetime
import sys
import webbrowser

from PyQt5.QtCore import Qt, QSize, QMargins, QRegExp
from PyQt5.QtGui import QPixmap, QFont, QRegExpValidator, QIcon, QColor, QPalette, QFontMetrics
from PyQt5.QtWidgets import *
#from PyQt5.QtWidgets import (
#    QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton, QLineEdit,
#    QHBoxLayout, QVBoxLayout, QGridLayout, QTabWidget, QTextEdit, QCheckBox,
#    QSpinBox, QRadioButton, QDateTimeEdit, QComboBox, QGroupBox, QButtonGroup,
#    QStatusBar, QSystemTrayIcon, QMenu, QAction, qApp, QDialog)


DEFAULT_POINTSIZE = 9    # 默认字体大小
DEFAULT_FONT = QFont()    #默认字体
TITLE_FONT = QFont()    #标题字体
CHINESE_SIZE = QSize()
DIGIT_SIZE = QSize()
ALPHA_SIZE = QSize()
POINT_HAND_CURSOR = Qt.PointingHandCursor    # 手形鼠标样式
IBEAM_CURSOR = Qt.IBeamCursor    #I形鼠标样式
DEFAULT_CURSOR = Qt.ArrowCursor    # 默认箭头鼠标样式
VIEW_WAY_LIST = ('', u'浏览器', u'安卓端', u'苹果端', u'电脑端', u'未知')
NOBLE_LEVEL_LIST = ('', u'游侠', u'骑士', u'子爵', u'伯爵', u'公爵', u'国王', u'皇帝', u'无贵族')
MESSAGE_TYPE_LIST = (u'弹幕消息', u'进房消息', u'禁言消息', u'粉丝牌升级',
                     u'任免房管', u'房间礼物', u'广播礼物', u'开通贵族',
                     u'续费贵族', u'喇叭消息', u'系统广播', u'开关播消息',
                     u'用户信息')
PORT_LIST = ('8601', '8602', '12601', '12602')


class DYApplication(QApplication):
    def __init__(self, argv):
        super(DYApplication, self).__init__(argv)
        self.init_UI_data()
        
    def init_UI_data(self):    # 设置字体，并获取字体的像素大小
        global DEFAULT_POINTSIZE, DEFAULT_FONT, TITLE_FONT
        DEFAULT_POINTSIZE = self.font().pointSize()
        DEFAULT_FONT = QFont('Microsoft YaHei', DEFAULT_POINTSIZE)
        TITLE_FONT = QFont('Microsoft YaHei', DEFAULT_POINTSIZE+4)
        TITLE_FONT.setBold(True)
        self.setFont(DEFAULT_FONT)
        global CHINESE_SIZE, DIGIT_SIZE, ALPHA_SIZE
        ref = QLabel()
        ref.hide()
        ref.setText(u'空')
        CHINESE_SIZE = QSize(ref.sizeHint())
        ref.setText('8')
        DIGIT_SIZE = QSize(ref.sizeHint())
        ref.setText('W')
        ALPHA_SIZE = QSize(ref.sizeHint())
        ref.destroy()


class MainWindowUi(QWidget):    # 构建主窗体的UI
    def __init__(self, parent=None):
        super(MainWindowUi, self).__init__(parent)
        # 添加各窗体
        self.topbar_widget = TopbarWidget(self)
        self.tab_window = QTabWidget(self)
        self.danmu_widget = DanmuWidget(self)        
        self.broadcast_widget = BroadcastWidget(self)
        self.list_widget = ListWidget(self)
        self.record_widget = RecordWidget(self)
        self.config_widget = ConfigWidget(self)
        self.advanced_setting = AdvancedSettingWidget(self)
        #self.advanced_setting.show()

        self.config_scroll_area = QScrollArea(self)
        self.config_scroll_area.setAlignment(Qt.AlignTop)
        self.config_scroll_area.setAlignment(Qt.AlignHCenter)
        self.config_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn) # 总是显示垂直滚动条
        self.config_scroll_area.setWidget(self.config_widget)
     
        self.tab_window.setDocumentMode(True)
        self.tab_window.tabBar().setCursor(POINT_HAND_CURSOR)
        self.tab_window.addTab(self.danmu_widget, u'弹幕')        
        self.tab_window.addTab(self.broadcast_widget, u'广播')
        self.tab_window.addTab(self.list_widget, u'榜单')
        self.tab_window.addTab(self.record_widget, u'记录')
        self.tab_window.addTab(self.config_scroll_area, u'设置')
        
        self.statusbar = StatusBar(self)    # 添加状态栏

        # 主窗体布局
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.topbar_widget)
        main_layout.addWidget(self.tab_window)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 0)

        all_widget_layout = QVBoxLayout()
        all_widget_layout.addLayout(main_layout)
        all_widget_layout.addWidget(self.statusbar)
        all_widget_layout.setContentsMargins(0, 0, 0, 0)

        all_widget_layout.setStretch(0, 1)
        self.setLayout(all_widget_layout)        
        self.resize(all_widget_layout.sizeHint())

    def closeEvent(self, event):
        self.destroy()
        sys.exit()
        
        
class TopbarWidget(QFrame):    # 构建显示直播间信息的顶栏
    def __init__(self, parent=None):
        super(TopbarWidget, self).__init__(parent)
        self.owner_avatar = QPushButton(self)    # 主播头像
        self.room_name = QLabel(u'直播间标题', self)    # 直播间标题
        self.cate_name = QLabel(u'分类：', self)    # 直播间所属分类
        self.room_status = QLabel(u'开播状态：', self)    # 直播间开播状态
        self.owner_name = QLabel(u'主播：', self)    # 主播名称
        self.hot_value = QLabel(u'热度：', self)    # 热度值
        self.fans_num = QLabel(u'关注：', self)    # 关注数 
        self.start_time = QLabel(u'最近开播时间：', self)    # 最近开播时间
        self.roomid_label = QLabel(u'直播间号：', self)
        self.roomid_enter = QLineEdit(self)    # 直播间号输入框
        self.connect_danmu = QPushButton(u'连接', self)    # 连接弹幕按钮

        self.setFrameShape(QFrame.StyledPanel)    # 顶栏显示边框
        self.setFrameShadow(QFrame.Plain)    # 无阴影样式
        
        self.room_name.setFont(TITLE_FONT)
        details_short_width = CHINESE_SIZE.width() * 11
        details_long_width = CHINESE_SIZE.width() * 20
        self.cate_name.setFixedWidth(details_short_width)
        self.room_status.setFixedWidth(details_short_width)
        self.owner_name.setMinimumWidth(details_long_width)
        self.hot_value.setFixedWidth(details_short_width)
        self.fans_num.setFixedWidth(details_short_width)
        self.start_time.setMinimumWidth(details_long_width)
        self.roomid_enter.setFixedWidth(DIGIT_SIZE.width() * 12)
        self.connect_danmu.setFixedWidth(CHINESE_SIZE.width() * 5)
        self.roomid_enter.setValidator(QRegExpValidator(QRegExp(r"[0-9]+")))    # 设置过滤器，只能输入数字
        self.owner_avatar.setFlat(True)    # 无边框
        self.owner_avatar.setCursor(POINT_HAND_CURSOR)    # 设置鼠标形状
        self.connect_danmu.setCursor(POINT_HAND_CURSOR)

        connect_danmu_layout = QHBoxLayout()
        connect_danmu_layout.addWidget(self.roomid_label)
        connect_danmu_layout.addWidget(self.roomid_enter)
        connect_danmu_layout.addWidget(self.connect_danmu)

        topbar_layout = QGridLayout()
        topbar_layout.addWidget(self.room_name, 0, 0, 1, 3)
        topbar_layout.addWidget(self.cate_name, 1, 0, 1, 1)
        topbar_layout.addWidget(self.room_status, 1, 1, 1, 1)
        topbar_layout.addWidget(self.owner_name, 1, 2, 1, 1)
        topbar_layout.addWidget(self.hot_value, 2, 0, 1, 1)
        topbar_layout.addWidget(self.fans_num, 2, 1, 1, 1)
        topbar_layout.addWidget(self.start_time, 2, 2, 1, 1)
        topbar_layout.addLayout(connect_danmu_layout, 0, 3, 1, 1)
        topbar_layout_spacer = 5
        topbar_layout.setSpacing(topbar_layout_spacer)
        topbar_layout.setContentsMargins(10, 10, 10, 10)
        topbar_layout.setColumnStretch(2, 1)

        all_widget_layout = QHBoxLayout()
        all_widget_layout.addWidget(self.owner_avatar)
        all_widget_layout.addLayout(topbar_layout)
        all_widget_layout.setSpacing(0)
        all_widget_layout.setContentsMargins(0, 0, 0, 0)
      
        avatar_height = topbar_layout.sizeHint().height()
        self.owner_avatar.setFixedSize(avatar_height, avatar_height)
        self.owner_avatar.setIconSize(self.owner_avatar.size())
        self.owner_avatar.setToolTip(u'打开直播间')

        self.setLayout(all_widget_layout)
        self.resize(all_widget_layout.sizeHint())

    def set_owner_avatar(self, pixmap):    # 设置直播间头像
        self.owner_avatar.setIcon(QIcon(pixmap))

    def set_room_details(self, room_name, cate_name, room_status, owner_name,
                         hot_value, fans_num, start_time):    # 设置直播间信息
        self.room_name.setText(room_name)
        self.cate_name.setText(u'分类：'+cate_name)
        self.room_status.setText(u'开播状态：'+room_status)
        self.owner_name.setText(u'主播：'+owner_name)
        self.hot_value.setText(u'热度：'+hot_value)
        self.fans_num.setText(u'关注：'+fans_num)
        self.start_time.setText(u'最近开播时间：'+start_time)

    def clear_room_details(self):    # 清空直播间信息
        self.set_room_details(u'直播间标题', '', '', '', '', '', '')


class DanmuWidget(QWidget):    # 构建弹幕窗体
    def __init__(self, parent=None):
        super(DanmuWidget, self).__init__(parent)
        self.danmu_text = QTextEdit(self)
        self.clear_danmu_button = QPushButton(u'清屏', self)
        self.hide_uenter = QCheckBox(u'屏蔽进房消息', self)
        self.simple_danmu = QCheckBox(u'简化弹幕', self)
        self.danmu_care_list_label = QLabel(u'关注列表：', self)
        self.danmu_care_list = QLineEdit(self)
        
        self.gift_text = QTextEdit(self)
        self.clear_gift_button = QPushButton(u'清屏', self)
        self.hide_smallgift = QCheckBox(u'屏蔽小礼物', self)
        self.gift_care_list_label = QLabel(u'关注列表：', self)
        self.gift_care_list = QLineEdit(self)
        
        text_edit_size = QSize(CHINESE_SIZE.width()*40, CHINESE_SIZE.height()*30)
        self.danmu_text.setMinimumSize(text_edit_size)
        self.gift_text.setMinimumSize(text_edit_size)
        spinbox_width = DIGIT_SIZE.width() * 8
        button_width = CHINESE_SIZE.width() * 3
        #self.danmu_care_list.setFixedWidth(spinbox_width)
        self.clear_danmu_button.setFixedWidth(button_width)
        #self.gift_care_list.setFixedWidth(spinbox_width)
        self.clear_gift_button.setFixedWidth(button_width)
        self.danmu_text.setReadOnly(True)
        self.danmu_text.setAcceptRichText(True)
        self.danmu_text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn) # 总是显示垂直滚动条
        self.gift_text.setReadOnly(True)        
        self.gift_text.setAcceptRichText(True)
        self.gift_text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn) # 总是显示垂直滚动条
        #self.danmu_text.setOverwriteMode(True)
        self.danmu_care_list.setToolTip(
            u'水友名称，用斜杠"/"分割，被关注的水友名称用红色显示，并在记录窗中显示')
        self.gift_care_list.setToolTip(
            u'水友名称，用斜杠"/"分割，被关注的水友名称用红色显示，并在记录窗中显示')
        self.clear_danmu_button.setCursor(POINT_HAND_CURSOR)
        self.clear_gift_button.setCursor(POINT_HAND_CURSOR)

        danmu_care_layout = QHBoxLayout()
        danmu_care_layout.setSpacing(0)
        danmu_care_layout.addWidget(self.danmu_care_list_label)
        danmu_care_layout.addWidget(self.danmu_care_list)        

        gift_care_layout = QHBoxLayout()
        gift_care_layout.setSpacing(0)
        gift_care_layout.addWidget(self.gift_care_list_label)
        gift_care_layout.addWidget(self.gift_care_list)

        danmu_config_layout = QHBoxLayout()
        danmu_config_layout.setSpacing(20)
        danmu_config_layout.addWidget(self.clear_danmu_button)
        danmu_config_layout.addWidget(self.hide_uenter)
        danmu_config_layout.addWidget(self.simple_danmu)
        danmu_config_layout.addLayout(danmu_care_layout)        
        danmu_config_layout.addStretch(1)

        gift_config_layout = QHBoxLayout()
        gift_config_layout.setSpacing(20)
        gift_config_layout.addWidget(self.clear_gift_button)
        gift_config_layout.addWidget(self.hide_smallgift)
        gift_config_layout.addLayout(gift_care_layout)        
        gift_config_layout.addStretch(1)

        danmu_widget_layout = QGridLayout()
        danmu_widget_layout.addWidget(self.danmu_text, 0, 0, 1, 1)
        danmu_widget_layout.addLayout(danmu_config_layout, 1, 0, 1, 1)
        danmu_widget_layout.addWidget(self.gift_text, 0, 1, 1, 1)
        danmu_widget_layout.addLayout(gift_config_layout, 1, 1, 1, 1)

        danmu_widget_layout.setSpacing(10)
        danmu_widget_layout.setContentsMargins(0, 0, 0, 0)
        danmu_widget_layout.setRowStretch(0, 1)
        danmu_widget_layout.setColumnStretch(0, 1)
        danmu_widget_layout.setColumnStretch(1, 1)

        self.setLayout(danmu_widget_layout)
        self.resize(danmu_widget_layout.sizeHint())
        

class BroadcastWidget(QWidget):    # 构建广播窗体
    def __init__(self, parent=None):
        super(BroadcastWidget, self).__init__(parent)
        self.broadcast_text = TextEdit(self)
        self.clear_broadcast_button = QPushButton(u'清屏', self)
        self.superrocket_noble_remind = QCheckBox(u'超级火箭和开通贵族宝箱提醒', self)
        self.all_gift_remind = QCheckBox(u'所有礼物宝箱提醒', self)
        self.gift_remind_blacklist_label = QLabel(u'--不提醒：', self)
        self.gift_remind_blacklist = QLineEdit(self)
        self.broadcast_care_list_label = QLabel(u'关注列表：', self)
        self.broadcast_care_list = QLineEdit(self)

        #self.broadcast_care_list.setFixedWidth(DIGIT_SIZE.width() * 8)
        self.clear_broadcast_button.setFixedWidth(CHINESE_SIZE.width() * 3)
        self.broadcast_text.setReadOnly(True)
        self.broadcast_text.setAcceptRichText(True)
        self.broadcast_text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn) # 总是显示垂直滚动条
        self.gift_remind_blacklist.setToolTip(u'礼物名称，用斜杠"/"分割')
        self.broadcast_care_list.setToolTip(
            u'水友名称，用斜杠"/"分割，被关注的水友名称用红色显示，并在记录窗中显示')
        self.clear_broadcast_button.setCursor(POINT_HAND_CURSOR)

        broadcast_remind_layout = QHBoxLayout()
        broadcast_remind_layout.setSpacing(0)
        broadcast_remind_layout.addWidget(self.all_gift_remind)
        broadcast_remind_layout.addWidget(self.gift_remind_blacklist_label)
        broadcast_remind_layout.addWidget(self.gift_remind_blacklist)
        
        broadcast_care_layout = QHBoxLayout()
        broadcast_care_layout.setSpacing(0)
        broadcast_care_layout.addWidget(self.broadcast_care_list_label)
        broadcast_care_layout.addWidget(self.broadcast_care_list)

        broadcast_config_layout = QHBoxLayout()
        broadcast_config_layout.setSpacing(20)
        broadcast_config_layout.addWidget(self.clear_broadcast_button)
        broadcast_config_layout.addWidget(self.superrocket_noble_remind)
        broadcast_config_layout.addLayout(broadcast_remind_layout)
        broadcast_config_layout.addLayout(broadcast_care_layout)        
        broadcast_config_layout.addStretch(1)

        broadcast_widget_layout = QGridLayout()
        broadcast_widget_layout.addWidget(self.broadcast_text, 0, 0, 1, 1)
        broadcast_widget_layout.addLayout(broadcast_config_layout, 1, 0, 1, 1)

        broadcast_layout_spacer = 10
        broadcast_widget_layout.setSpacing(broadcast_layout_spacer)
        broadcast_widget_layout.setContentsMargins(0, 0, 0, 0)
        broadcast_widget_layout.setRowStretch(0, 1)
        broadcast_widget_layout.setColumnStretch(0, 1)
        
        self.setLayout(broadcast_widget_layout)
        self.resize(broadcast_widget_layout.sizeHint())

        
class ListWidget(QWidget):    # 构建榜单窗体
    def __init__(self, parent=None):
        super(ListWidget, self).__init__(parent)        
        self.rank_window = QTabWidget(self)    # 贡献榜窗体
        self.noble_window = QTabWidget(self)    # 贵族列表窗体
        self.fans_window = QTabWidget(self)    # 粉丝列表窗体
        self.rank_day = DisplayListWindow(self)    # 贡献值日榜
        self.rank_week = DisplayListWindow(self)    # 贡献值周榜
        self.rank_all = DisplayListWindow(self)    # 贡献值总榜
        self.noble_list = DisplayListWindow(self)    # 贵族列表
        self.fans_all = DisplayListWindow(self)    # 粉丝等级总榜
        self.fans_week = DisplayListWindow(self)    # 粉丝7天亲密度排行

        self.rank_window.addTab(self.rank_day, u'日榜')
        self.rank_window.addTab(self.rank_week, u'周榜')
        self.rank_window.addTab(self.rank_all, u'总榜')
        self.noble_window.addTab(self.noble_list, u'贵族（0）')
        self.fans_window.addTab(self.fans_week, u'粉丝7天排行')
        self.fans_window.addTab(self.fans_all, u'粉丝等级总榜')

        self.rank_window.setCurrentIndex(1)
        self.rank_window.tabBar().setCursor(POINT_HAND_CURSOR)
        self.noble_window.tabBar().setCursor(POINT_HAND_CURSOR)
        self.fans_window.tabBar().setCursor(POINT_HAND_CURSOR)
        self.rank_window.tabBar().setDocumentMode(True)
        self.noble_window.tabBar().setDocumentMode(True)
        self.fans_window.tabBar().setDocumentMode(True)
        self.rank_day.label.hide()
        self.rank_week.label.hide()
        self.rank_all.label.hide()

        list_widget_layout = QHBoxLayout()
        list_widget_layout.setSpacing(10)
        list_widget_layout.addWidget(self.rank_window)
        list_widget_layout.addWidget(self.noble_window)
        list_widget_layout.addWidget(self.fans_window)
        list_widget_layout.setContentsMargins(0, 10, 0, 0)
        
        self.setLayout(list_widget_layout)
        self.resize(list_widget_layout.sizeHint())
        

class RecordWidget(QWidget):    # 构建记录窗体
    def __init__(self, parent=None):
        super(RecordWidget, self).__init__(parent)
        self.record_text = QTextEdit(self)        
        self.message_type_label = QLabel(u'消息类型：', self)
        self.begin_time_label = QLabel(u'开始时间：', self)
        self.end_time_label = QLabel(u'结束时间：', self)
        self.room_num_label = QLabel(u'直播间号：', self)
        self.view_way_label = QLabel(u'观看方式：', self)
        self.noble_level_label = QLabel(u'贵族等级：', self)
        self.user_id_label = QLabel(u'用户ID：', self)
        self.user_name_label = QLabel(u'用户名称：', self)
        self.danmu_text_label = QLabel(u'弹幕内容：', self)
        self.gift_name_label = QLabel(u'礼物名称：', self)
        self.anthor_name_label = QLabel(u'主播名称：', self)
        self.message_type = QComboBox(self)
        self.begin_time = QDateTimeEdit(self)
        self.not_begin = QCheckBox(u'不限', self)
        self.end_time = QDateTimeEdit(self)
        self.not_end = QCheckBox(u'不限', self)
        self.room_num = QLineEdit(self)
        self.view_way = QComboBox(self)
        self.noble_level = QComboBox(self)
        self.user_id = QLineEdit(self)
        self.user_name = QLineEdit(self)
        self.danmu_text = QLineEdit(self)
        self.gift_name = QLineEdit(self)
        self.anthor_name = QLineEdit(self)
        self.max_result_label = QLabel(u'查询结果最大显示数量：', self)
        self.max_result = QSpinBox(self)
        self.query_button = QPushButton(u'查询', self)
        self.reset_button = QPushButton(u'重置', self)
        self.clear_record_button = QPushButton(u'清屏', self)
        self.tips = QLabel(u'添加“%”可模糊查询，例如“%条件%”。\n' +
                           u'若查询结果超过设置的最大显示数量，' +
                           u'则只显示最近的结果（查询用户信息不受限制）。', self)
        self.result_tips = QLabel(self)

        self.record_text.setReadOnly(True)
        self.record_text.setAcceptRichText(True)
        self.record_text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn) # 总是显示垂直滚动条
        self.message_type.addItems(MESSAGE_TYPE_LIST)
        self.begin_time.setDisplayFormat('yyyy-MM-dd HH:mm:ss')
        self.end_time.setDisplayFormat('yyyy-MM-dd HH:mm:ss')
        self.room_num.setValidator(QRegExpValidator(QRegExp(r"[0-9]+")))
        self.view_way.addItems(VIEW_WAY_LIST)
        self.noble_level.addItems(NOBLE_LEVEL_LIST)
        self.query_button.setCursor(POINT_HAND_CURSOR)
        self.reset_button.setCursor(POINT_HAND_CURSOR)
        self.clear_record_button.setCursor(POINT_HAND_CURSOR)
        self.tips.setWordWrap(True)
        self.result_tips.setWordWrap(True)
        self.max_result.setWrapping(True)
        self.max_result.setRange(0, 100000000)
        self.max_result.setToolTip(u'范围：0--100000000，0表示不限数量')
        
        self.reset_button.clicked.connect(self.reset_widgets)
        self.message_type.currentIndexChanged.connect(self.selected_message_type_event)

        condition_layout = QGridLayout()
        condition_layout.addWidget(self.message_type_label, 0, 0)
        condition_layout.addWidget(self.begin_time_label, 1, 0)
        condition_layout.addWidget(self.end_time_label, 2, 0)
        condition_layout.addWidget(self.room_num_label, 3, 0)
        condition_layout.addWidget(self.view_way_label, 4, 0)
        condition_layout.addWidget(self.noble_level_label, 5, 0)
        condition_layout.addWidget(self.user_id_label, 6, 0)
        condition_layout.addWidget(self.user_name_label, 7, 0)
        condition_layout.addWidget(self.danmu_text_label, 8, 0)
        condition_layout.addWidget(self.gift_name_label, 9, 0)
        condition_layout.addWidget(self.anthor_name_label, 10, 0)
        condition_layout.addWidget(self.message_type, 0, 1, 1, 2)
        condition_layout.addWidget(self.begin_time, 1, 1)
        condition_layout.addWidget(self.not_begin, 1, 2)
        condition_layout.addWidget(self.end_time, 2, 1)
        condition_layout.addWidget(self.not_end, 2, 2)
        condition_layout.addWidget(self.room_num, 3, 1, 1, 2)
        condition_layout.addWidget(self.view_way, 4, 1, 1, 2)
        condition_layout.addWidget(self.noble_level, 5, 1, 1, 2)
        condition_layout.addWidget(self.user_id, 6, 1, 1, 2)
        condition_layout.addWidget(self.user_name, 7, 1, 1, 2)
        condition_layout.addWidget(self.danmu_text, 8, 1, 1, 2)
        condition_layout.addWidget(self.gift_name, 9, 1, 1, 2)
        condition_layout.addWidget(self.anthor_name, 10, 1, 1, 2)
        condition_layout.setColumnStretch(1, 1)

        max_result_layout = QHBoxLayout()
        max_result_layout.addWidget(self.max_result_label)
        max_result_layout.addWidget(self.max_result)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.query_button)
        button_layout.addWidget(self.reset_button)
        button_layout.addWidget(self.clear_record_button)
        button_layout.addStretch(1)

        right_layout = QVBoxLayout()
        right_layout.addLayout(condition_layout)
        right_layout.addLayout(max_result_layout)
        right_layout.addLayout(button_layout)
        right_layout.addWidget(self.tips)
        right_layout.addWidget(self.result_tips)
        right_layout.addStretch(1)
        right_layout.setContentsMargins(10, 10, 0, 0)

        record_widget_layout = QHBoxLayout()
        record_widget_layout.addWidget(self.record_text, 1)
        record_widget_layout.addLayout(right_layout)
        record_widget_layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(record_widget_layout)
        self.resize(record_widget_layout.sizeHint())
        self.reset_widgets()
        self.selected_message_type_event()

    def reset_widgets(self):    # 重置查询条件
        #self.message_type.setCurrentIndex(0)
        self.begin_time.setDateTime(datetime.datetime.now())
        self.not_begin.setChecked(False)
        self.end_time.setDateTime(datetime.datetime.now())
        self.not_end.setChecked(False)
        self.room_num.clear()
        self.view_way.setCurrentIndex(0)
        self.noble_level.setCurrentIndex(0)
        self.user_id.clear()
        self.user_name.clear()
        self.danmu_text.clear()
        self.gift_name.clear()
        self.anthor_name.clear()
        self.max_result.setValue(10000)

    def selected_message_type_event(self, event=None):
        sele_type = self.message_type.currentText()
        self.view_way.setDisabled(True)
        self.noble_level.setDisabled(True)
        self.user_id.setDisabled(True)
        self.user_name.setDisabled(True)
        self.danmu_text.setDisabled(True)
        self.gift_name.setDisabled(True)
        self.anthor_name.setDisabled(True)
        if sele_type == u'弹幕消息':    # 查询弹幕消息
            self.view_way.setEnabled(True)    # 观看方式可用
            self.noble_level.setEnabled(True)    # 贵族等级可用
            self.user_id.setEnabled(True)    # 用户ID可用
            self.user_name.setEnabled(True)    # 用户名称可用
            self.danmu_text.setEnabled(True)    # 弹幕内容可用
        elif sele_type == u'进房消息':    # 查询进房消息
            self.noble_level.setEnabled(True)    # 贵族等级可用
            self.user_id.setEnabled(True)    # 用户ID可用
            self.user_name.setEnabled(True)    # 用户名称可用
        elif sele_type == u'禁言消息':    # 查询禁言消息
            self.user_id.setEnabled(True)    # 用户ID可用
            self.user_name.setEnabled(True)    # 用户名称可用
        elif sele_type == u'粉丝牌升级':    # 查询粉丝牌升级消息
            self.user_id.setEnabled(True)    # 用户ID可用
            self.user_name.setEnabled(True)    # 用户名称可用
        elif sele_type == u'任免房管':    # 查询任免房管消息
            self.user_id.setEnabled(True)    # 用户ID可用
            self.user_name.setEnabled(True)    # 用户名称可用
        elif sele_type == u'房间礼物':    # 查询房间礼物
            self.noble_level.setEnabled(True)    # 贵族等级可用
            self.user_id.setEnabled(True)    # 用户ID可用
            self.user_name.setEnabled(True)    # 用户名称可用
            self.gift_name.setEnabled(True)    # 礼物名称可用
        elif sele_type == u'广播礼物':    # 查询广播礼物
            self.user_name.setEnabled(True)    # 用户名称可用
            self.gift_name.setEnabled(True)    # 礼物名称可用
            self.anthor_name.setEnabled(True)     # 主播名称可用
        elif sele_type == u'开通贵族':    # 查询开通贵族
            self.noble_level.setEnabled(True)    # 贵族等级可用
            self.user_id.setEnabled(True)    # 用户ID可用
            self.user_name.setEnabled(True)    # 用户名称可用
            self.anthor_name.setEnabled(True)    # 主播名称可用
        elif sele_type == u'续费贵族':    # 查询续费贵族
            self.noble_level.setEnabled(True)    # 贵族等级可用
            self.user_id.setEnabled(True)    # 用户ID可用
            self.user_name.setEnabled(True)    # 用户名称可用
            self.anthor_name.setEnabled(True)    # 主播名称可用
        elif sele_type == u'喇叭消息':    # 查询喇叭消息
            self.user_name.setEnabled(True)    # 用户名称可用
            self.anthor_name.setEnabled(True)    # 主播名称可用
        elif sele_type == u'系统广播':    # 查询系统广播
            pass
        elif sele_type == u'开关播消息':    # 查询开关播消息
            pass
        elif sele_type == u'用户信息':    # 查询用户信息
            self.user_id.setEnabled(True)    # 用户ID可用
            self.user_name.setEnabled(True)    # 用户名称可用        

class ConfigWidget(QWidget):    # 构建设置窗体
    def __init__(self, parent=None):
        super(ConfigWidget, self).__init__(parent)
        self.close_mainwindow_label = QLabel(u'关闭主面板时：', self)
        self.close_mainwindow_config = QButtonGroup(self)
        self.option_minimize_window = QRadioButton(u'最小化到系统托盘', self)
        self.option_close_program = QRadioButton(u'关闭程序', self)
        self.stay_top = QCheckBox(u'始终保持在其它窗口前端', self)
        self.auto_enter = QCheckBox(u'开播自动打开直播间', self)
        self.open_remind = QCheckBox(u'开播弹窗提醒', self)
        self.open_remind_sound = QCheckBox(u'开启铃声提醒', self)
        self.open_remind_file = QPushButton(u'（声音文件：OpenRemind.wav）', self)
        self.open_remind_duration_label = QLabel(u'弹窗显示时间：', self)
        self.open_remind_duration = QSpinBox(self)
        self.open_remind_duration_tip = QLabel(u'秒（范围：0--900，0表示持续显示）', self)
        self.title_remind = QCheckBox(u'修改直播间标题弹窗提醒', self)
        self.title_remind_sound = QCheckBox(u'开启铃声提醒', self)
        self.title_remind_file = QPushButton(u'（声音文件：TitleRemind.wav）', self)
        self.title_remind_duration_label = QLabel(u'弹窗显示时间：', self)
        self.title_remind_duration = QSpinBox(self)
        self.title_remind_duration_tip = QLabel(u'秒（范围：0--900，0表示持续显示）', self)
        self.record_message = QCheckBox(u'记录消息', self)
        self.record_all = QCheckBox(u'全部消息', self)
        self.record_chatmsg = QCheckBox(u'弹幕消息', self)
        self.record_uenter = QCheckBox(u'进房消息', self)
        self.record_newblackres = QCheckBox(u'禁言消息', self)
        self.record_blab = QCheckBox(u'粉丝牌升级', self)
        self.record_setadminres = QCheckBox(u'任免房管', self)
        self.record_dgb = QCheckBox(u'房间礼物', self)
        self.record_spbc = QCheckBox(u'广播礼物', self)
        self.record_anbc = QCheckBox(u'开通贵族', self)
        self.record_rnewbc = QCheckBox(u'续费贵族', self)
        self.record_cthn = QCheckBox(u'喇叭消息', self)
        self.record_ssd = QCheckBox(u'系统广播', self)
        self.record_rss = QCheckBox(u'开关播消息', self)
        self.gift_remind = QLabel(u'抢宝箱弹窗提醒设置：', self)
        self.gift_remind_sound = QCheckBox(u'开启铃声提醒', self)
        self.gift_remind_file = QPushButton(u'（声音文件：GiftRemind.wav）', self)
        self.gift_remind_duration_label = QLabel(u'弹窗显示时间：', self)
        self.gift_remind_duration = QSpinBox(self)
        self.gift_remind_duration_tip = QLabel(u'秒（范围：0--180，0表示持续显示）', self)
        self.max_message_config = QLabel(
            u'消息框最大显示数量设置（范围：0--100000，0表示不限数量）：', self)
        self.max_danmu_label = QLabel(u'弹幕：', self)
        self.max_danmu_num = QSpinBox(self)
        self.max_gift_label = QLabel(u'礼物：', self)
        self.max_gift_num = QSpinBox(self)
        self.max_broadcast_label = QLabel(u'广播：', self)
        self.max_broadcast_num = QSpinBox(self)
        self.save_config_button = QPushButton(u'保存设置', self)
        self.default_config_button = QPushButton(u'默认设置', self)
        self.advanced_setting_button = QPushButton(u'高级设置', self)
        self.about_software_button = QPushButton(u'关于软件', self)
        self.save_config_tip = QLabel(
            u'说明：设置更改立即生效，正常退出程序时会自动保存', self)

        self.close_mainwindow_config.addButton(self.option_minimize_window, 0)
        self.close_mainwindow_config.addButton(self.option_close_program, 1)
        self.close_mainwindow_config.button(0).setChecked(True)
        self.open_remind_duration.setRange(0, 900)
        self.title_remind_duration.setRange(0, 900)
        self.gift_remind_duration.setRange(0, 180)
        self.max_danmu_num.setRange(0, 100000)
        self.max_gift_num.setRange(0, 100000)
        self.max_broadcast_num.setRange(0, 100000)
        self.open_remind_duration.setWrapping(True)
        self.title_remind_duration.setWrapping(True)
        self.gift_remind_duration.setWrapping(True)
        self.max_danmu_num.setWrapping(True)
        self.max_gift_num.setWrapping(True)
        self.max_broadcast_num.setWrapping(True)
        self.open_remind_file.setFlat(True)
        self.title_remind_file.setFlat(True)
        self.gift_remind_file.setFlat(True)
        self.open_remind_file.setCursor(POINT_HAND_CURSOR)
        self.title_remind_file.setCursor(POINT_HAND_CURSOR)
        self.gift_remind_file.setCursor(POINT_HAND_CURSOR)
        self.save_config_button.setCursor(POINT_HAND_CURSOR)
        self.default_config_button.setCursor(POINT_HAND_CURSOR)
        self.advanced_setting_button.setCursor(POINT_HAND_CURSOR)
        self.about_software_button.setCursor(POINT_HAND_CURSOR)

        indent_margins = QMargins(20, 0, 0, 0)

        close_mainwindow_layout = QHBoxLayout()
        close_mainwindow_layout.addWidget(self.close_mainwindow_label)
        close_mainwindow_layout.addWidget(self.option_minimize_window)
        close_mainwindow_layout.addWidget(self.option_close_program)
        close_mainwindow_layout.addStretch(1)

        open_remind_sound_layout = QHBoxLayout()
        open_remind_sound_layout.setSpacing(0)
        open_remind_sound_layout.addWidget(self.open_remind_sound)
        open_remind_sound_layout.addWidget(self.open_remind_file)
        open_remind_sound_layout.addStretch(1)
        open_remind_sound_layout.setContentsMargins(indent_margins)
        open_remind_duration_layout = QHBoxLayout()
        open_remind_duration_layout.addWidget(self.open_remind_duration_label)
        open_remind_duration_layout.addWidget(self.open_remind_duration)
        open_remind_duration_layout.addWidget(self.open_remind_duration_tip)
        open_remind_duration_layout.addStretch(1)
        open_remind_duration_layout.setContentsMargins(indent_margins)

        title_remind_sound_layout = QHBoxLayout()
        title_remind_sound_layout.setSpacing(0)
        title_remind_sound_layout.addWidget(self.title_remind_sound)
        title_remind_sound_layout.addWidget(self.title_remind_file)
        title_remind_sound_layout.addStretch(1)
        title_remind_sound_layout.setContentsMargins(indent_margins)
        title_remind_duration_layout = QHBoxLayout()
        title_remind_duration_layout.addWidget(self.title_remind_duration_label)
        title_remind_duration_layout.addWidget(self.title_remind_duration)
        title_remind_duration_layout.addWidget(self.title_remind_duration_tip)
        title_remind_duration_layout.addStretch(1)
        title_remind_duration_layout.setContentsMargins(indent_margins)

        record_message_type_layout = QGridLayout()
        record_message_type_layout.addWidget(self.record_chatmsg, 0, 0)
        record_message_type_layout.addWidget(self.record_uenter, 0, 1)
        record_message_type_layout.addWidget(self.record_newblackres, 0, 2)
        record_message_type_layout.addWidget(self.record_blab, 0, 3)
        record_message_type_layout.addWidget(self.record_setadminres, 1, 0)
        record_message_type_layout.addWidget(self.record_dgb, 1, 1)
        record_message_type_layout.addWidget(self.record_spbc, 1, 2)
        record_message_type_layout.addWidget(self.record_anbc, 1, 3)
        record_message_type_layout.addWidget(self.record_rnewbc, 2, 0)
        record_message_type_layout.addWidget(self.record_cthn, 2, 1)
        record_message_type_layout.addWidget(self.record_ssd, 2, 2)
        record_message_type_layout.addWidget(self.record_rss, 2, 3)
        record_message_type_layout.addWidget(self.record_all, 3, 0)
        record_message_type_layout.setContentsMargins(indent_margins)

        gift_remind_sound_layout = QHBoxLayout()
        gift_remind_sound_layout.setSpacing(0)
        gift_remind_sound_layout.addWidget(self.gift_remind_sound)
        gift_remind_sound_layout.addWidget(self.gift_remind_file)
        gift_remind_sound_layout.addStretch(1)
        gift_remind_sound_layout.setContentsMargins(indent_margins)
        gift_remind_duration_layout = QHBoxLayout()
        gift_remind_duration_layout.addWidget(self.gift_remind_duration_label)
        gift_remind_duration_layout.addWidget(self.gift_remind_duration)
        gift_remind_duration_layout.addWidget(self.gift_remind_duration_tip)
        gift_remind_duration_layout.addStretch(1)
        gift_remind_duration_layout.setContentsMargins(indent_margins)

        max_danmu_layout = QHBoxLayout()
        max_danmu_layout.setSpacing(0)
        max_danmu_layout.addWidget(self.max_danmu_label)
        max_danmu_layout.addWidget(self.max_danmu_num)

        max_gift_layout = QHBoxLayout()
        max_gift_layout.setSpacing(0)
        max_gift_layout.addWidget(self.max_gift_label)
        max_gift_layout.addWidget(self.max_gift_num)

        max_broadcast_layout = QHBoxLayout()
        max_broadcast_layout.setSpacing(0)
        max_broadcast_layout.addWidget(self.max_broadcast_label)
        max_broadcast_layout.addWidget(self.max_broadcast_num)

        max_massage_config_layout = QHBoxLayout()
        max_massage_config_layout.setSpacing(15)
        max_massage_config_layout.addLayout(max_danmu_layout)
        max_massage_config_layout.addLayout(max_gift_layout)
        max_massage_config_layout.addLayout(max_broadcast_layout)
        max_massage_config_layout.addStretch(1)
        max_massage_config_layout.setContentsMargins(indent_margins)
        
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.save_config_button)
        button_layout.addWidget(self.default_config_button)
        button_layout.addWidget(self.advanced_setting_button)
        button_layout.addWidget(self.about_software_button)
        button_layout.addStretch(1)
        button_layout.setContentsMargins(0, 10, 0, 0)

        config_vertical_layout = QVBoxLayout()
        #config_vertical_layout.addStretch(1)
        config_vertical_layout.addLayout(close_mainwindow_layout)
        config_vertical_layout.addWidget(self.stay_top)
        config_vertical_layout.addWidget(self.auto_enter)
        config_vertical_layout.addWidget(self.open_remind)
        config_vertical_layout.addLayout(open_remind_sound_layout)
        config_vertical_layout.addLayout(open_remind_duration_layout)
        config_vertical_layout.addWidget(self.title_remind)
        config_vertical_layout.addLayout(title_remind_sound_layout)
        config_vertical_layout.addLayout(title_remind_duration_layout)
        config_vertical_layout.addWidget(self.record_message)
        config_vertical_layout.addLayout(record_message_type_layout)
        config_vertical_layout.addWidget(self.gift_remind)
        config_vertical_layout.addLayout(gift_remind_sound_layout)
        config_vertical_layout.addLayout(gift_remind_duration_layout)
        config_vertical_layout.addWidget(self.max_message_config)
        config_vertical_layout.addLayout(max_massage_config_layout)
        config_vertical_layout.addWidget(self.save_config_tip)        
        config_vertical_layout.addLayout(button_layout)       
        config_vertical_layout.addStretch(1)

        config_widget_layout = QHBoxLayout()
        config_widget_layout.addStretch(1)
        config_widget_layout.addLayout(config_vertical_layout)
        config_widget_layout.addStretch(1)

        self.setLayout(config_widget_layout)
        self.resize(config_widget_layout.sizeHint())


class AdvancedSettingWidget(QDialog):    # 构建高级设置窗体
    def __init__(self, parent=None):
        super(AdvancedSettingWidget, self).__init__(parent)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)    # 无帮助按钮
        self.setWindowFlag(Qt.MSWindowsFixedSizeDialogHint, True)    # 窗体大小固定
        self.setWindowTitle(u'高级设置')

        self.danmu_server_label = QLabel(u'服务器：', self)
        self.danmu_server = QLineEdit(self)
        self.danmu_port_label = QLabel(u'端口号：', self)
        self.danmu_port = QComboBox(self)
        self.danmu_group_label = QLabel(u'弹幕组：', self)
        self.danmu_group = QLineEdit(self)
        self.confirm_button = QPushButton(u'确认', self)
        self.reset_button = QPushButton(u'重置', self)
        self.cancel_button = QPushButton(u'取消', self)

        self.danmu_server.setText('openbarrage.douyutv.com')
        self.danmu_port.addItems(PORT_LIST)
        self.danmu_group.setText('-9999')

        settings_layout = QGridLayout()
        settings_layout.addWidget(self.danmu_server_label, 0, 0)
        settings_layout.addWidget(self.danmu_server, 0, 1)
        settings_layout.addWidget(self.danmu_port_label, 1, 0)
        settings_layout.addWidget(self.danmu_port, 1, 1)
        settings_layout.addWidget(self.danmu_group_label, 2, 0)
        settings_layout.addWidget(self.danmu_group, 2, 1)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.confirm_button)
        button_layout.addWidget(self.reset_button)
        button_layout.addWidget(self.cancel_button)

        widget_layout = QVBoxLayout()
        widget_layout.addLayout(settings_layout)
        widget_layout.addLayout(button_layout)

        self.setLayout(widget_layout)
        self.resize(widget_layout.sizeHint())
        

class StatusBar(QStatusBar):    # 构建状态栏
    def __init__(self, parent=None):
        super(StatusBar, self).__init__(parent)        
        self.connect_status = QLabel(u'连接状态：未连接', self)
        self.danmu_num = QLabel(u'弹幕消息数量：0', self)
        self.gift_num = QLabel(u'礼物消息数量：0', self)
        self.broadcast_num = QLabel(u'广播消息数量：0', self)
        self.record_num = QLabel(u'记录消息数量：0', self)
        self.get_html_status = QLabel(self)

        self.addWidget(self.connect_status, 1)
        self.addWidget(self.danmu_num, 1)
        self.addWidget(self.gift_num, 1)
        self.addWidget(self.broadcast_num, 1)
        self.addWidget(self.record_num, 1)
        self.addWidget(self.get_html_status, 1)
        

class TrayIcon(QSystemTrayIcon):    # 构建托盘菜单
    def __init__(self, parent=None):
        super(TrayIcon, self).__init__(parent)
        self.tray_menu = QMenu()
        self.setContextMenu(self.tray_menu)
        self.action_connect = self.tray_menu.addAction(u'连接 (空)')
        self.action_open_room = self.tray_menu.addAction(u'打开直播间')
        self.tray_menu.addSeparator()
        self.action_superrocket_remind = self.tray_menu.addAction(u'超火和贵族宝箱提醒')
        self.action_all_remind = self.tray_menu.addAction(u'所有礼物宝箱提醒')
        self.tray_menu.addSeparator()
        self.action_auto_enter = self.tray_menu.addAction(u'开播自动打开直播间')
        self.action_open_remind = self.tray_menu.addAction(u'开播提醒')
        self.action_title_remind = self.tray_menu.addAction(u'修改标题提醒')
        self.tray_menu.addSeparator()
        self.action_main_window = self.tray_menu.addAction(u'打开主面板')
        self.action_enter_config = self.tray_menu.addAction(u'设置')
        self.action_about_software = self.tray_menu.addAction(u'关于')
        self.tray_menu.addSeparator()
        self.action_software_quit = self.tray_menu.addAction(u'退出')

        self.action_superrocket_remind.setCheckable(True)
        self.action_all_remind.setCheckable(True)
        self.action_auto_enter.setCheckable(True)
        self.action_open_remind.setCheckable(True)
        self.action_title_remind.setCheckable(True)


class MessageBoxUi(QDialog):    # 构建弹窗的UI
    def __init__(self, parent=None):
        super(MessageBoxUi, self).__init__(parent)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setWindowFlag(Qt.MSWindowsFixedSizeDialogHint, True)
        #self.setWindowFlag(Qt.WindowCloseButtonHint, False)

        self.message_text = QLabel(self)
        self.yes_button = QPushButton(self)
        self.no_button = QPushButton(self)
        
        palette = QPalette(QColor('#FFFFFF'))
        self.message_text.setAutoFillBackground(True)
        self.message_text.setPalette(palette)    # 设置背景颜色为白色
        self.message_text.setAlignment(Qt.AlignCenter)    # 居中显示
        self.message_text.setMargin(20)
        self.message_text.setWordWrap(True)    # 自动换行
        self.message_text.setMinimumSize(300, 100)
        self.yes_button.setCursor(POINT_HAND_CURSOR)
        self.no_button.setCursor(POINT_HAND_CURSOR)

        button_layout = QHBoxLayout() 
        button_layout.addStretch(1)
        button_layout.addWidget(self.yes_button)
        button_layout.addWidget(self.no_button)
        button_layout.setContentsMargins(10, 10, 10, 10)

        message_layout = QVBoxLayout()
        message_layout.addWidget(self.message_text)
        message_layout.addLayout(button_layout)
        message_layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(message_layout)
        self.resize(message_layout.sizeHint())


class TextEdit(QTextEdit):    # 重构文本框，增加鼠标事件，用于打开url
    def __init__(self, parent=None):
        super(TextEdit, self).__init__(parent)
        self.press_cursor = None
        self.setMouseTracking(True)    # 设置不用按下鼠标就可触发鼠标移动事件

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:    # 鼠标左键事件
            point = event.pos()
            self.press_cursor = self.cursorForPosition(point)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:    # 鼠标左键事件
            point = event.pos()    # 鼠标点击位置
            text_cursor = self.cursorForPosition(point)    # 文本指针位置
            if text_cursor == self.press_cursor:
                press_block_text = text_cursor.block().text()    # 获取点击的消息文本
                position = text_cursor.positionInBlock()    # 点击的位置
                url_position = press_block_text.rfind('https://www.douyu.com/')    # url的起始位置
                if (url_position != -1 and position >= url_position and
                    position < len(press_block_text)):    # 判断是否点击url
                    webbrowser.open(press_block_text[url_position:])
            self.press_cursor = None

    def mouseMoveEvent(self, event):
        if event.button() == Qt.NoButton:    # 鼠标左键事件
            point = event.pos()    # 鼠标位置            
            text_cursor = self.cursorForPosition(point)    # 文本指针位置
            press_block_text = text_cursor.block().text()    # 鼠标所在的消息文本
            position = text_cursor.positionInBlock()
            url_position = press_block_text.rfind('https://www.douyu.com/')    # url的起始位置
            if (url_position != -1 and position >= url_position and
                position < len(press_block_text)):    # 判断鼠标是否位于url上
                self.viewport().setCursor(POINT_HAND_CURSOR)
            else:
                self.viewport().setCursor(IBEAM_CURSOR)


class DisplayListWindow(QWidget):    # 构建显示榜单的窗体，显示完整的信息
    def __init__(self, parent=None):
        super(DisplayListWindow, self).__init__(parent)
        self.list = DisplayListWidget(self)
        self.label = QLabel(self)
        self.time = QLabel(self)

        self.label.setStyleSheet('background-color: #FFFFFF;')    # 设置背景颜色为白色
        self.label.setFrameShape(QFrame.StyledPanel)    # 显示边框
        self.label.setFrameShadow(QFrame.Plain)
        self.time.setAlignment(Qt.AlignCenter)
        self.time.setMargin(5)

        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.addWidget(self.list)
        layout.addWidget(self.label)
        layout.addWidget(self.time)
        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)
        self.resize(layout.sizeHint())
                

class DisplayListWidget(QTableWidget):    # 构建显示榜单列表信息的窗体
    def __init__(self, parent=None):
        super(DisplayListWidget, self).__init__(parent)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)    # 设置成整行选中
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)    # 设置不可编辑
        self.setShowGrid(False)    # 设置不显示表格线

        self.setColumnCount(1)    # 只有1列
        self.horizontalHeader().setVisible(False)    # 行列表头不显示
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)    # 自动填充窗体
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)    # 自动调整单元格大小
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.verticalHeader().setMinimumSectionSize(CHINESE_SIZE.height())    # 设置最小行高


class UserInfoWidget(QWidget):    # 显示榜单中一行的信息
    def __init__(self, number, noble, level, name, brand, value, parent=None):
        super(UserInfoWidget, self).__init__(parent)
        self.number_label = NumberLabel(number)    # 序号
        self.noble_label = NobleLabel(noble)    # 贵族
        self.level_label = LevelLabel(level)    # 等级
        self.name_label = NameLabel(name)    # 用户名
        self.brand_label = FansBrandLabel(brand)    # 粉丝牌
        self.value_label = ValueLabel(value)    # 值（贡献值或亲密度）

        if number == None or number == '':    # 隐藏内容为空的控件
            self.number_label.hide()
        if noble == None or noble == '':
            self.noble_label.hide()
        if brand == None or noble == '':
            self.brand_label.hide()
        if value == None or value == '':
            self.value_label.hide()

        layout = QHBoxLayout()
        layout.addWidget(self.number_label)
        layout.addWidget(self.noble_label)
        layout.addWidget(self.level_label)
        layout.addWidget(self.name_label)
        layout.addWidget(self.brand_label)
        layout.addWidget(self.value_label)
        layout.setSpacing(4)
        layout.setStretch(3, 1)
        layout.setContentsMargins(4, 0, 10, 0)

        self.setLayout(layout)
        self.resize(layout.sizeHint())
        
        
class NumberLabel(QLabel):    # 用于显示序号
    def __init__(self, text, parent=None):
        super(NumberLabel, self).__init__(text, parent)
        self.setAlignment(Qt.AlignCenter)    # 设置文字居中
        self.setStyleSheet('color: #888888;')
        self.setFixedWidth(DIGIT_SIZE.width() * 3)    # 设置固定大小
        self.setFixedHeight(CHINESE_SIZE.height())
        

class NameLabel(QLabel):    # 用于显示用户名
    def __init__(self, text, parent=None):
        super(NameLabel, self).__init__(text, parent)
        self.dsp_text = text
        self.setAlignment(Qt.AlignLeft)
        #self.setStyleSheet('color: #000000; background-color: #FFFFFF;')
        self.setFixedHeight(CHINESE_SIZE.height())
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.setCursor(IBEAM_CURSOR)
        self.setToolTip(text)

    def resizeEvent(self, event=None):    # 判断是否文字过长，过长则显示省略号
        self.setText(self.dsp_text)
        fontwidth = QFontMetrics(self.font())
        text_width = fontwidth.width(self.dsp_text)    # 文字长度
        widget_width = self.size().width()    # 控件长度
        if text_width >= widget_width:
            self.setText(fontwidth.elidedText(self.dsp_text, Qt.ElideRight, widget_width))


class ValueLabel(QLabel):    # 用于显示贡献值或亲密度
    def __init__(self, text, parent=None):
        super(ValueLabel, self).__init__(text, parent)
        self.setAlignment(Qt.AlignRight)
        #self.setStyleSheet('color: #000000; background-color: #FFFFFF;')
        self.setFixedWidth(DIGIT_SIZE.width() * 10)
        self.setFixedHeight(CHINESE_SIZE.height())
        

class LevelLabel(QLabel):    # 用于显示用户等级
    def __init__(self, text, parent=None):
        super(LevelLabel, self).__init__(text, parent)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet('color: #FFFFFF; background-color: #2B94FF;')
        self.setFixedWidth(DIGIT_SIZE.width() * 4)
        self.setFixedHeight(CHINESE_SIZE.height())


class NobleLabel(QLabel):    # 用于显示贵族
    def __init__(self, text, parent=None):
        super(NobleLabel, self).__init__(text, parent)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet('color: #FFFFFF; background-color: #FF5500;')
        self.setFixedWidth(CHINESE_SIZE.width() * 2)
        self.setFixedHeight(CHINESE_SIZE.height())


class FansBrandLabel(QLabel):    # 用于显示粉丝牌
    def __init__(self, text, parent=None):
        super(FansBrandLabel, self).__init__(text, parent)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet('color: #FFFFFF; background-color: #FF69B4;')
        self.setFixedHeight(CHINESE_SIZE.height())

        
    
if __name__ == '__main__':
    app = DYApplication(sys.argv)    
    
    win = MainWindowUi()    # 创建主窗体         
    win.show()    # 显示主窗体

    sys.exit(app.exec_())
   
