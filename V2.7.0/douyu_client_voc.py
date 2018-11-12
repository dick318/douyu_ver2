#!usr/bin/python3
# -*- coding: utf-8 -*-

# filename: douyu_sp.py
# version: 1.0.0
# date: 2018-10-02
# last date: 2018-10-14
# os: windows

import os
import pickle
import pythoncom
import re
import sys
import time
import win32com.client

from PyQt5.QtCore import Qt
from queue import Queue
from threading import Thread, Event

from douyu_client_gui import DYApplication
from douyu_client import *
from douyu_client_voc_gui import VoicerWidget, VoiceConfigWidget

#LOGGER.addHandler(PRINT_LOG)    # 输出所有信息到控制台!!

# 关于软件的说明
ABOUT_SOFTWARE_VOC = (u'Design by 枫轩\n'
                      u'当前版本：2.7.0(2018-10-14)VOC\n'
                      u'联系方式：990761629(QQ)')

VOICER_CONFIG_FILE = 'VoicerConfig'    # 保存语音设置的文件名

EMOT_TEXT = {'101': u'666', '102': u'发呆', '103': u'拜拜', '104': u'晕',
             '105': u'弱', '106': u'傲慢', '107': u'开心', '108': u'奋斗',
             '109': u'很酷', '110': u'流泪', '111': u'鄙视', '112': u'得意',
             '113': u'抠鼻', '114': u'亲亲', '115': u'偷笑', '116': u'口罩',
             '117': u'委屈', '118': u'难过', '119': u'吐血', '120': u'大怒',
             '121': u'赞', '122': u'睡觉', '123': u'骷髅', '124': u'调皮',
             '125': u'惊讶', '126': u'撇嘴', '127': u'拥抱', '128': u'背锅',
             '129': u'闭嘴', '130': u'吃药', '131': u'可怜', '132': u'呕吐',
             '133': u'敲打', '134': u'心碎', '135': u'嘘', '136': u'中箭',
             '137': u'抓狂', '001': u'流汗', '002': u'丢药', '003': u'白眼',
             '004': u'火箭', '005': u'色', '006': u'点蜡', '007': u'抽烟',
             '008': u'可爱', '009': u'炸弹', '010': u'吃丸子', '011': u'害怕',
             '012': u'疑问', '013': u'阴险', '014': u'害羞', '015': u'笑哭',
             '016': u'猪头', '017': u'困'}


class Speaker:    # 语音引擎，参照pyttsx3语音模块
    def __init__(self):
        self.engine = win32com.client.Dispatch("SAPI.SpVoice")    # 创建引擎
        self.flags = {'SpeakDefault': 0,    # 默认同步模式，会阻塞线程
                     'SpeakAsync': 1,    # 异步模式，不会阻塞线程
                     'SpeakSync': 2,    # 同步模式，会阻塞线程
                     'PurgeBeforeSpeak': 3    # 清除队列中的其它语句，不会阻塞线程
                     }
        self.loop = True
        self.speaking = False    # 标志是否正在朗读
        self.has_loop = False    # 标志是否已存在语音循环
        self.voice_queue = Queue()    # 语音队列
        self.voice_event = Event()    # 用于清空语音队列

    def setRate(self, rate):    # 设置语速-10到10
        self.engine.Rate = rate

    def setVolume(self, volume):    # 设置音量0到100
        self.engine.Volume = volume

    def say(self, text):    # 将语句放到语音队列中
        self.voice_queue.put({'type': 'text', 'text': text}, 1)

    def pause(self):    # 暂停朗读
        self.engine.Pause()

    def resume(self):    # 继续朗读
        self.engine.Resume()

    def stop(self):    # 停止朗读并清空语音队列
        self.purge()
        self.engine.Speak('', self.flags['PurgeBeforeSpeak'])        

    def purge(self):    # 清空语音队列
        try:
            self.voice_event.clear()
            while not self.voice_queue.empty():
                temp = self.voice_queue.get(1)
        finally:
            self.voice_event.set()

    def isBusy(self):    # 查询是否正在朗读
        return self.speaking or not self.voice_queue.empty()
    
    def startLoop(self):    # 开启语音循环
        if not self.has_loop:
            self.has_loop = True
            self.loop = True
            self.voice_event.set()
            while self.loop:
                try:
                    self.voice_event.wait()
                    data = self.voice_queue.get(1)
                    if data['type'] == 'end':
                        break
                    elif data['type'] == 'text':
                        self.speaking = True
                        pythoncom.CoInitialize()    # 缺少该语句可能会报异常
                        self.engine.Speak(data['text'], self.flags['SpeakAsync'])    # 异步朗读
                        self.engine.WaitUntilDone(-1)    # 等待当前朗读结束
                        self.speaking = False
                except Exception as exc:
                    exc_msg = exception_message(exc)
                    ERROR_LOGGER.error(exc_msg)
        else:
            exc_msg = u'已存在语音循环'
            ERROR_LOGGER.error(exc_msg)

    def endLoop(self):    # 结束语音循环
        self.loop = False
        self.has_loop = False
        self.stop()
        self.voice_queue.put({'type': 'end', 'text': ''}, 1)
    

class DisplayWindowVOC(MainWindow):    # 重构主窗体，添加语音模块
    def __init__(self):
        super(DisplayWindowVOC, self).__init__()
        self.voice_config = VoiceConfigWidget(self)    # 创建语音设置窗体
        self.voicer_widget = VoicerWidget(self)    # 创建“语音助手”按键
        self.voice_config.setWindowFlag(Qt.WindowCloseButtonHint, False)    # 去除窗体的关闭按键
        self.topbar_widget.topbar_right_widget.layout().addWidget(self.voicer_widget)    # 添加“语音助手”按键

        self.voicer_config_file_path = os.path.join(PROGRAM_CONFIG_FOLDER, VOICER_CONFIG_FILE)    # 保存语音设置文件的路径
        # 语音设置相关变量
        self.set_start_voicer = False
        self.set_voice_volume = 100
        self.set_voice_rate = 0
        self.set_speak_chatmsg = True
        self.set_include_name = True
        self.set_pattern_chatmsg = 0
        self.set_chatmsg_interval = 0
        self.set_chatmsg_voice_care = ''
        self.set_speak_dgb = True
        self.set_only_big_gift = True
        self.set_dgb_voice_care = ''
        self.set_dgb_whitelist = ''
        self.set_dgb_blacklist = ''

        self.chatmsg_voice_care_list = []
        self.dgb_voice_care_list = []
        self.dgb_whitelist_list = []
        self.dgb_blacklist_list = []

        # 保存设置改变前的值
        self.last_volume = self.set_voice_volume
        self.last_rate = self.set_voice_rate
        self.last_pattern_chatmsg = self.set_pattern_chatmsg

        self.speaker = Speaker()    # 创建语音引擎
        self.queue_voice_data = Queue()        

        self.voicer_widget.voicer_button.clicked.connect(self.voicer_button_event)
        self.voice_config.confirm_button.clicked.connect(self.save_voicer_config_event)
        self.voice_config.reset_button.clicked.connect(self.reset_voicer_config_event)
        self.voice_config.cancel_button.clicked.connect(self.cancel_voicer_config_event)
        
        self.voice_config.volume.valueChanged.connect(self.volume_change_event)
        self.voice_config.volume.sliderPressed.connect(self.volume_slider_pressed)
        self.voice_config.volume.sliderReleased.connect(self.volume_slider_released)
        self.voice_config.rate.valueChanged.connect(self.rate_change_event)
        self.voice_config.rate.sliderPressed.connect(self.rate_slider_pressed)
        self.voice_config.rate.sliderReleased.connect(self.rate_slider_released)

        self.load_voicer_config()    # 导入语音设置
        self.speaker.stop()
        self.start_voicer()    # 开启语音助手线程

#    def test(self):
#        self.speaker.stop()
        
    def process_message_event(self, data):    # 处理显示消息，由触发显示线程触发        
        try:
            if data['type'] in self.danmu_message_type:                    
                self.display_danmu_message(data)                
            elif data['type'] in self.gift_message_type:
                self.display_gift_message(data)
            elif data['type'] in self.broadcast_message_type:
                self.display_broadcast_message(data)
            elif data['type'] in self.list_message_type:
                self.display_list_message(data)
            elif data['type'] == 'rss':
                self.display_rss_message(data)
            elif data['type'] == 'loginres':
                self.process_loginres_message()
            elif data['type'] in ('keeplive', 'live'):
                self.process_keeplive_message(data)
            elif data['type'] in ('exception', 'error'):
                self.process_error_message(data)               
            elif data['type'] == 'disconnected':
                self.process_disconnected_message()

            # 设置了记录消息，则将数据发送给记录消息线程
            if self.set_record and data['type'] in self.record_type_list:
                if self.new_record:
                    self.new_record = False
                    self.start_record_message()    # 开启记录消息线程
                self.queue_record_data.put(data, 1)

            # 将消息发送给语音助手线程
            if self.set_start_voicer and data['type'] in ('chatmsg', 'dgb'):
                self.queue_voice_data.put(data, 1)
                
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            ERROR_LOGGER.error(repr(data))
        finally:
            self.event_display.set()
            pass
                
    def volume_change_event(self, value=None):    # 调整音量事件处理器
        self.speaker.setVolume(value)

    def volume_slider_pressed(self, event=None):
        self.last_volume = self.voice_config.volume.sliderPosition()

    def volume_slider_released(self, event=None):    # 点击滑块事件，测试当前音量
        if self.last_volume == self.voice_config.volume.sliderPosition():
            if not self.speaker.isBusy():
                self.speaker.say(u'音量设置')
        
    def rate_change_event(self, value=None):    # 调整语速事件处理器
        self.speaker.setRate(value)

    def rate_slider_pressed(self, event=None):
        self.last_rate = self.voice_config.rate.sliderPosition()

    def rate_slider_released(self, event=None):    # 点击滑块事件，测试当前语速
        if self.last_rate == self.voice_config.rate.sliderPosition():
            if not self.speaker.isBusy():
                self.speaker.say(u'语速设置')
        
    def start_voicer(self):    # 开启语音助手线程
        thread_speaker_loop = Thread(target=self.speaker.startLoop)
        thread_speaker_loop.setDaemon(True)
        thread_speaker_loop.start()
        thread_voice = Thread(target=self.thread_voicer,
                              args=(self.queue_voice_data, self.speaker))
        thread_voice.setDaemon(True)
        thread_voice.start()

    def thread_voicer(self, queue_data, engine):
        say_chatmsg_time = 0
        while True:            
            try:
                data = queue_data.get(1)
                say_txt = ''
                if data['type'] == 'close':
                    break
                elif data['type'] == 'chatmsg' and self.set_speak_chatmsg:    # 读弹幕
                    speak_chatmsg = True
                    if data['nn'] in self.chatmsg_voice_care_list:    # 是否在用户关注列表中
                        say_txt = u'%s说：%s' % (data['nn'], data['txt'])
                        speak_chatmsg = False
                    elif self.set_pattern_chatmsg == 0:    # 全读
                        speak_chatmsg = True
                    elif self.set_pattern_chatmsg == 1:    # 连读
                        if engine.isBusy():    # 正在朗读则忽略
                            speak_chatmsg = False
                    elif self.set_pattern_chatmsg == 2:    # 间读                        
                        if (int(time.time()) - say_chatmsg_time) < self.set_chatmsg_interval:    # 小于间隔时间则忽略
                            speak_chatmsg = False
                    if speak_chatmsg:
                        if self.set_include_name:    # 是否包含用户名
                            say_txt = u'%s说：%s' % (data['nn'], data['txt'])
                        else:
                            say_txt = data['txt']
                    if say_txt:
                        say_chatmsg_time = int(time.time())    # 记录朗读时间
                        emot_list = re.findall('\[emot\:dy\d{3}\]', say_txt)
                        for emot in emot_list:    # 将斗鱼表情换成说明文字
                            if emot[8:-1] in EMOT_TEXT:
                                say_txt = say_txt.replace(emot, ',%s,' % EMOT_TEXT[emot[8:-1]])
                        engine.say(say_txt)

                elif data['type'] == 'dgb' and self.set_speak_dgb:    # 读礼物
                    speak_dgb = True
                    if (data['nn'] in self.dgb_voice_care_list or
                        data['gn'] in self.dgb_whitelist_list):    # 在用户关注列表或礼物白名单中
                        speak_dgb = True
                    elif data['gn'] in self.dgb_blacklist_list:    # 在礼物黑名单中
                        speak_dgb = False
                    elif self.set_only_big_gift and data['bg'] == '0':    # 只读大礼物
                        speak_dgb = False
                    if speak_dgb:
                        say_txt = u'%s赠送给主播%s' % (data['nn'], data['gn'])
                        if data['gfcnt'] == '1':
                            say_txt += (u'%s连击' % data['hits']) if data['hits'] not in ('0', '1') else ''
                        else:
                            say_txt += u'×%s' % data['gfcnt']
                    if say_txt:
                        engine.say(say_txt)

            except Exception as exc:
                exc_msg = exception_message(exc)
                ERROR_LOGGER.error(exc_msg)
                ERROR_LOGGER.error(repr(data))

    def voicer_button_event(self, event=None):    # “语音助手”按键事件处理器
        self.set_voicer_config_to_windows(self.get_voicer_config_from_variables())
        self.last_pattern_chatmsg = self.set_pattern_chatmsg
        self.voice_config.show()    # 显示语音设置窗体
        
    def save_voicer_config_event(self, event=None):    # “保存”按键事件处理器
        self.voice_config.hide()
        self.set_voicer_config_to_variables(self.get_voicer_config_from_windows())
        self.save_voicer_config()
        if not self.set_start_voicer:
            self.speaker.stop()
        if self.last_pattern_chatmsg != self.set_pattern_chatmsg:
            self.speaker.purge()

    def reset_voicer_config_event(self, event=None):    # “重置”按键事件处理器
        self.set_voicer_config_to_windows(self.get_voicer_default_config())

    def cancel_voicer_config_event(self, event=None):    # “取消”按键事件处理器
        self.voice_config.hide()
        self.set_voicer_config_to_windows(self.get_voicer_config_from_variables())
        self.speaker.setVolume(self.set_voice_volume)
        self.speaker.setRate(self.set_voice_rate)        

    def load_voicer_config(self):    # 加载保存在文件中的语音设置
        if os.path.exists(self.voicer_config_file_path):
            try:
                with open(self.voicer_config_file_path, 'rb') as config_file:
                    config_data = pickle.load(config_file)
            except Exception as exc:
                exc_msg = exception_message(exc) + u'#加载语音设置文件失败'
                ERROR_LOGGER.error(exc_msg)
                os.remove(self.voicer_config_file_path)
                self.load_voicer_default_config()
                self.save_voicer_config()
            else:
                if not (config_data and                        
                        self.set_voicer_config_to_windows(config_data) and
                        self.set_voicer_config_to_variables(config_data)):
                    exc_msg = u'#加载语音设置失败'
                    ERROR_LOGGER.error(exc_msg)
                    os.remove(self.voicer_config_file_path)
                    self.load_voicer_default_config()
                    self.save_voicer_config()
        else:    # 加载默认语音设置
            self.load_voicer_default_config()
            self.save_voicer_config()
            
    def load_voicer_default_config(self):    # 加载默认语音设置
        self.set_voicer_config_to_windows(self.get_voicer_default_config())
        self.set_voicer_config_to_variables(self.get_voicer_default_config())

    def save_voicer_config(self):    # 保存语音设置
        try:
            with open(self.voicer_config_file_path, 'wb') as config_file:
                pickle.dump(self.get_voicer_config_from_windows(), config_file)
        except Exception as exc:
            os.remove(self.voicer_config_file_path)
            if not os.path.exists(self.voicer_config_file_path):
                self.save_voicer_config()
            else:
                exc_msg = exception_message(exc) + u'#保存语音设置失败'
                ERROR_LOGGER.warning(exc_msg)
                
    def get_voicer_default_config(self):    # 默认的语音设置数据
        return {
            'StartVoicer': False,
            'VoiceVolume': 100,
            'VoiceRate': 0,
            'SpeakChatmsg': True,
            'IncludeName': True,
            'PatternChatmsg': 0,
            'ChatmsgInterval': 0,
            'ChatmsgVoiceCare': '',
            'SpeakDgb': True,
            'OnlyBigGift': True,
            'DgbVoiceCare': '',
            'DgbWhitelist': '',
            'DgbBlacklist': '',
        }

    def get_voicer_config_from_variables(self):    # 从语音设置变量获取语音设置数据
        return {
            'StartVoicer': self.set_start_voicer,
            'VoiceVolume': self.set_voice_volume,
            'VoiceRate': self.set_voice_rate,
            'SpeakChatmsg': self.set_speak_chatmsg,
            'IncludeName': self.set_include_name,
            'PatternChatmsg': self.set_pattern_chatmsg,
            'ChatmsgInterval': self.set_chatmsg_interval,
            'ChatmsgVoiceCare': self.set_chatmsg_voice_care,
            'SpeakDgb': self.set_speak_dgb,
            'OnlyBigGift': self.set_only_big_gift,
            'DgbVoiceCare': self.set_dgb_voice_care,
            'DgbWhitelist': self.set_dgb_whitelist,
            'DgbBlacklist': self.set_dgb_blacklist,
        }

    def get_voicer_config_from_windows(self):    # 从语音设置窗体获取语音设置数据
        return {
            'StartVoicer': self.voice_config.start_voicer.isChecked(),
            'VoiceVolume': self.voice_config.volume.value(),
            'VoiceRate': self.voice_config.rate.value(),
            'SpeakChatmsg': self.voice_config.speak_chatmsg.isChecked(),
            'IncludeName': self.voice_config.include_name.isChecked(),
            'PatternChatmsg': self.voice_config.pattern_chatmsg_config.checkedId(),
            'ChatmsgInterval': self.voice_config.chatmsg_time_interval.value(),
            'ChatmsgVoiceCare': self.voice_config.chatmsg_voice_care.text(),
            'SpeakDgb': self.voice_config.speak_dgb.isChecked(),
            'OnlyBigGift': self.voice_config.only_big_gift.isChecked(),
            'DgbVoiceCare': self.voice_config.dgb_voice_care.text(),
            'DgbWhitelist': self.voice_config.dgb_whitelist.text(),
            'DgbBlacklist': self.voice_config.dgb_blacklist.text(),
        }

    def set_voicer_config_to_variables(self, config_data):    # 用数据配置语音设置变量
        try:
            self.set_start_voicer = config_data['StartVoicer']
            self.set_voice_volume = config_data['VoiceVolume']
            self.set_voice_rate = config_data['VoiceRate']
            self.set_speak_chatmsg = config_data['SpeakChatmsg']
            self.set_include_name = config_data['IncludeName']
            self.set_pattern_chatmsg = config_data['PatternChatmsg']
            self.set_chatmsg_interval = config_data['ChatmsgInterval']
            self.set_chatmsg_voice_care = config_data['ChatmsgVoiceCare']
            self.set_speak_dgb = config_data['SpeakDgb']
            self.set_only_big_gift = config_data['OnlyBigGift']
            self.set_dgb_voice_care = config_data['DgbVoiceCare']
            self.set_dgb_whitelist = config_data['DgbWhitelist']
            self.set_dgb_blacklist = config_data['DgbBlacklist']
            self.speaker.setVolume(self.set_voice_volume)
            self.speaker.setRate(self.set_voice_rate)
            self.chatmsg_voice_care_list = self.set_chatmsg_voice_care.replace(' ', '').split('/')
            self.dgb_voice_care_list = self.set_dgb_voice_care.replace(' ', '').split('/')
            self.dgb_whitelist_list = self.set_dgb_whitelist.replace(' ', '').split('/')
            self.dgb_blacklist_list = self.set_dgb_blacklist.replace(' ', '').split('/')
            return True
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            return False
        
    def set_voicer_config_to_windows(self, config_data):    # 用数据配置语音设置窗体
        try:
            self.voice_config.start_voicer.setChecked(config_data['StartVoicer'])
            self.voice_config.volume.setValue(config_data['VoiceVolume'])
            self.voice_config.rate.setValue(config_data['VoiceRate'])
            self.voice_config.speak_chatmsg.setChecked(config_data['SpeakChatmsg'])
            self.voice_config.include_name.setChecked(config_data['IncludeName'])
            self.voice_config.pattern_chatmsg_config.button(config_data['PatternChatmsg']).setChecked(True)
            self.voice_config.chatmsg_time_interval.setValue(config_data['ChatmsgInterval'])
            self.voice_config.chatmsg_voice_care.setText(config_data['ChatmsgVoiceCare'])
            self.voice_config.speak_dgb.setChecked(config_data['SpeakDgb'])
            self.voice_config.only_big_gift.setChecked(config_data['OnlyBigGift'])
            self.voice_config.dgb_voice_care.setText(config_data['DgbVoiceCare'])
            self.voice_config.dgb_whitelist.setText(config_data['DgbWhitelist'])
            self.voice_config.dgb_blacklist.setText(config_data['DgbBlacklist'])
            return True
        except Exception as exc:
            exc_msg = exception_message(exc)
            ERROR_LOGGER.error(exc_msg)
            return False
        
    def about_software_event(self):    # 弹窗显示关于程序的信息
        self.show_about_software(ABOUT_SOFTWARE_VOC)
        
    
if __name__ == '__main__':
    app = DYApplication(sys.argv)    
       
    win = DisplayWindowVOC()    # 创建主窗体       
    win.show()    # 居中显示主窗体 

    sys.exit(app.exec_())
