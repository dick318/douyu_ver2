#!usr/bin/python3
# -*- coding: utf-8 -*-

# filename: douyu_client_launch.py
# version: 1.0.0
# date: 2018-04-06
# last date: 2018-05-08
# os: windows

import sys

from douyu_client_gui import DYApplication
from douyu_client import MainWindow
    
if __name__ == '__main__':
    app = DYApplication(sys.argv)       
    
    win = MainWindow()    # 创建主窗体    
    win.show()    # 显示主窗体
    
    sys.exit(app.exec_())
