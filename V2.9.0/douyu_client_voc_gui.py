#!/usr/bin/python3
# -*- coding: utf-8 -*-

# filename: douyu_client_gui.py
# version: 1.0.0
# date: 2018-03-26
# last date: 2018-10-14
# os: windows


import datetime
import sys
import webbrowser

from PyQt5.QtCore import Qt, QMargins
from PyQt5.QtWidgets import *

from douyu_client_gui import DYApplication, POINT_HAND_CURSOR

class VoicerWidget(QWidget):    # “语音助手”按键
    def __init__(self, parent=None):
        super(VoicerWidget, self).__init__(parent)
        self.voicer_button = QPushButton(u'语音助手', self)
        self.voicer_button.setCursor(POINT_HAND_CURSOR)

        voicer_button_layout = QHBoxLayout()
        voicer_button_layout.addWidget(QWidget())
        voicer_button_layout.addWidget(self.voicer_button)
        voicer_button_layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(voicer_button_layout)
        #self.resize(voicer_button_layout.sizeHint())
        
    
class VoiceConfigWidget(QDialog):    # 构建语音设置窗体
    def __init__(self, parent=None):
        super(VoiceConfigWidget, self).__init__(parent)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)    # 无帮助按钮
        self.setWindowFlag(Qt.MSWindowsFixedSizeDialogHint, True)    # 窗体大小固定
        self.setWindowTitle(u'语音助手设置')

        self.start_voicer = QCheckBox(u'开启语音助手', self)
        self.volume_label = QLabel(u'音量：', self)
        self.volume = QSlider(Qt.Horizontal, self)
        self.volume_value = QLabel('0', self)
        self.rate_label = QLabel(u'语速：', self)
        self.rate = QSlider(Qt.Horizontal, self)
        self.rate_value = QLabel('0', self)
        self.speak_chatmsg = QCheckBox(u'读弹幕', self)
        self.include_name = QCheckBox(u'读弹幕时包含用户名', self)
        self.pattern_chatmsg = QLabel(u'模式：', self)
        self.pattern_chatmsg_config = QButtonGroup(self)
        self.speak_chatmsg_all = QRadioButton(u'全读（弹幕较多时会有延迟）', self)
        self.speak_chatmsg_continuity = QRadioButton(u'连读（忽略朗读时的其它弹幕）', self)
        self.speak_chatmsg_interval = QRadioButton(u'间读（接收到弹幕的时间间隔）', self)
        self.chatmsg_time_interval_label = QLabel(u'间隔时间(s)：', self)
        self.chatmsg_time_interval = QSpinBox(self)
        self.chatmsg_voice_care_label = QLabel(u'关注用户：', self)
        self.chatmsg_voice_care = QLineEdit(self)
        self.speak_dgb = QCheckBox(u'读礼物', self)
        self.only_big_gift = QCheckBox(u'只读大礼物', self)
        self.dgb_voice_care_label = QLabel(u'关注用户：', self)
        self.dgb_voice_care = QLineEdit(self)
        self.dgb_whitelist_label = QLabel(u'礼物白名单：', self)
        self.dgb_whitelist = QLineEdit(self)
        self.dgb_blacklist_label = QLabel(u'礼物黑名单：', self)
        self.dgb_blacklist = QLineEdit(self)

        self.confirm_button = QPushButton(u'保存', self)
        self.reset_button = QPushButton(u'重置', self)
        self.cancel_button = QPushButton(u'取消', self)

        from douyu_client_gui import DIGIT_SIZE, CHINESE_SIZE, ALPHA_SIZE

        self.volume.setRange(0, 100)
        self.volume.setSingleStep(10)    # 滚轮的步长
        self.volume.setPageStep(10)    # 点击的步长
        self.volume.setTracking(False)    # 拖动滑块时不触发valueChanged事件
        self.volume.setFixedWidth(DIGIT_SIZE.width() * 20)
        self.volume_value.setFixedWidth(DIGIT_SIZE.width() * 4)
        self.rate.setRange(-10, 10)
        self.rate.setSingleStep(1)
        self.rate.setPageStep(1)
        self.rate.setTracking(False)
        self.rate.setFixedWidth(DIGIT_SIZE.width() * 20)
        self.rate_value.setFixedWidth(DIGIT_SIZE.width() * 4)
        self.chatmsg_time_interval.setRange(0, 600)
        self.chatmsg_time_interval.setWrapping(True)
        self.pattern_chatmsg_config.addButton(self.speak_chatmsg_all, 0)
        self.pattern_chatmsg_config.addButton(self.speak_chatmsg_continuity, 1)
        self.pattern_chatmsg_config.addButton(self.speak_chatmsg_interval, 2)
        self.confirm_button.setCursor(POINT_HAND_CURSOR)
        self.reset_button.setCursor(POINT_HAND_CURSOR)
        self.cancel_button.setCursor(POINT_HAND_CURSOR)

        indent_margins = QMargins(20, 0, 0, 0)
        
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(self.volume_label)
        volume_layout.addWidget(self.volume)
        volume_layout.addWidget(self.volume_value)
        volume_layout.addStretch(1)

        rate_layout = QHBoxLayout()
        rate_layout.addWidget(self.rate_label)
        rate_layout.addWidget(self.rate)
        rate_layout.addWidget(self.rate_value)
        rate_layout.addStretch(1)

        pattern_chatmsg_layout = QVBoxLayout()
        pattern_chatmsg_layout.addWidget(self.speak_chatmsg_all)
        pattern_chatmsg_layout.addWidget(self.speak_chatmsg_continuity)
        pattern_chatmsg_layout.addWidget(self.speak_chatmsg_interval)

        chatmsg_time_interval_layout = QHBoxLayout()
        chatmsg_time_interval_layout.setSpacing(0)
        chatmsg_time_interval_layout.addWidget(self.chatmsg_time_interval_label)
        chatmsg_time_interval_layout.addWidget(self.chatmsg_time_interval)
        chatmsg_time_interval_layout.addStretch(1)
        chatmsg_time_interval_layout.setContentsMargins(indent_margins)

        chatmsg_voice_care_layout = QHBoxLayout()
        chatmsg_voice_care_layout.addWidget(self.chatmsg_voice_care_label)
        chatmsg_voice_care_layout.addWidget(self.chatmsg_voice_care)

        set_pattern_chatmsg_layout = QVBoxLayout()
        set_pattern_chatmsg_layout.addLayout(pattern_chatmsg_layout)
        set_pattern_chatmsg_layout.addLayout(chatmsg_time_interval_layout)
        set_pattern_chatmsg_layout.setContentsMargins(indent_margins)

        chatmsg_voice_config_layout = QVBoxLayout()
        chatmsg_voice_config_layout.addWidget(self.include_name)
        chatmsg_voice_config_layout.addWidget(self.pattern_chatmsg)
        chatmsg_voice_config_layout.addLayout(set_pattern_chatmsg_layout)
        chatmsg_voice_config_layout.addLayout(chatmsg_voice_care_layout)
        chatmsg_voice_config_layout.setContentsMargins(indent_margins)

        dgb_voice_care_layout = QHBoxLayout()
        dgb_voice_care_layout.addWidget(self.dgb_voice_care_label)
        dgb_voice_care_layout.addWidget(self.dgb_voice_care)

        dgb_whitelist_layout = QHBoxLayout()
        dgb_whitelist_layout.addWidget(self.dgb_whitelist_label)
        dgb_whitelist_layout.addWidget(self.dgb_whitelist)

        dgb_blacklist_layout = QHBoxLayout()
        dgb_blacklist_layout.addWidget(self.dgb_blacklist_label)
        dgb_blacklist_layout.addWidget(self.dgb_blacklist)
        
        dgb_voice_config_layout = QVBoxLayout()
        dgb_voice_config_layout.addWidget(self.only_big_gift)
        dgb_voice_config_layout.addLayout(dgb_voice_care_layout)
        dgb_voice_config_layout.addLayout(dgb_whitelist_layout)
        dgb_voice_config_layout.addLayout(dgb_blacklist_layout)
        dgb_voice_config_layout.setContentsMargins(indent_margins)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.confirm_button)
        button_layout.addWidget(self.reset_button)
        button_layout.addWidget(self.cancel_button)        

        widget_layout = QVBoxLayout()
        widget_layout.addWidget(self.start_voicer)
        widget_layout.addLayout(volume_layout)
        widget_layout.addLayout(rate_layout)
        widget_layout.addWidget(self.speak_chatmsg)
        widget_layout.addLayout(chatmsg_voice_config_layout)        
        widget_layout.addWidget(self.speak_dgb)
        widget_layout.addLayout(dgb_voice_config_layout)
        widget_layout.addLayout(button_layout)

        self.setLayout(widget_layout)
        self.resize(widget_layout.sizeHint())

        self.volume.valueChanged.connect(self.volume_slider_event)
        self.rate.valueChanged.connect(self.rate_slider_event)

    def volume_slider_event(self, value=None):    # 显示音量
        self.volume_value.setText(str(value))

    def rate_slider_event(self, value=None):    # 显示语速
        self.rate_value.setText(str(value))

    def keyPressEvent(self, event):    # 不响应ESC键
        if event.key() == Qt.Key_Escape:
            pass

if __name__ == '__main__':
    app = DYApplication(sys.argv)    
    
    win = VoiceConfigWidget()    # 创建窗体         
    win.show()    # 显示窗体

    sys.exit(app.exec_())
   
