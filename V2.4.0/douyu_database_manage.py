#!/usr/bin/python3
# -*- coding: utf-8 -*-

# filename: douyu_database_manage.py
# version: 1.0.0
# date: 2017-12-20
# last date: 2018-06-24
# os: windows


import os
import sqlite3
import time


class MyDataBase(object):
    def __init__(self, dbname):
        self.db_name = dbname    # 数据库文件名
        self.connect = sqlite3.connect(self.db_name)    # 连接数据库，不存在则创建

    def disconnect(self):    # 关闭数据库连接
        self.connect.close()

    def create(self, table_name, table_header):
        # 创建表格，表名str table_name，表头list table_header
        cur = self.connect.cursor()
        sql = 'CREATE TABLE IF NOT EXISTS %s (%s)' % (table_name, ', '.join(table_header))
        cur.execute(sql)
        cur.close()
        self.connect.commit()

    def insert(self, table_name, table_data):
        # 判断表格是否存在，在表格中新增数据，表名str table_name，数据list table_data
        if not self.exists(table_name):    # 判断是否存在该表格
            return False
        sql = 'INSERT INTO %s VALUES (%s)' % (table_name, ', '.join(['?']*len(table_data)))
        cur = self.connect.cursor()
        cur.execute(sql, tuple(table_data))
        cur.close()
        self.connect.commit()
        return True

    def insert_n(self, table_name, table_data):
        # 不判断表格是否存在，在表格中新增数据，表名str table_name，数据list table_data
        sql = 'INSERT INTO %s VALUES (%s)' % (table_name, ', '.join(['?']*len(table_data)))
        cur = self.connect.cursor()
        cur.execute(sql, tuple(table_data))
        cur.close()
        self.connect.commit()

    def insert_dict(self, table_name, table_data):
        # 不判断表格是否存在，在表格中新增数据，表名str table_name，数据dict table_data
        header = ()
        data = ()
        for key in table_data:
            header += (key,)    # 获取行列名的元组
            data += (table_data[key],)    # 获取数据的元组
        sql = 'INSERT INTO %s (%s) VALUES (%s)' % (
            table_name, ', '.join(header), ', '.join(['?']*len(data)))
        cur = self.connect.cursor()
        cur.execute(sql, data)
        cur.close()
        self.connect.commit()        

    def update(self, table_name, data, condition=None):
        # 更新表格中的数据，表名str table_name，数据dict data，条件dict condition
        if not self.exists(table_name):
            return False
        sql_tuple_1 = ()
        data_tuple = ()
        for key in data:
            sql_tuple_1 += (key + ' = ?', )
            data_tuple += (data[key], )
        if condition:
            sql_tuple_2 = ()
            for key in condition:
                sql_tuple_2 += (key + ' LIKE ?', )
                data_tuple += (condition[key], )
            sql = 'UPDATE %s SET %s WHERE %s' % (
                table_name, ', '.join(sql_tuple_1), ' AND '.join(sql_tuple_2))    
        else:
            sql = 'UPDATE %s SET %s' % (table_name, ', '.join(sql_tuple_1))
            
        cur = self.connect.cursor()
        cur.execute(sql, data_tuple)
        cur.close()
        self.connect.commit()
        return True                

    def query(self, table_name, condition=None):
        # 查询数据，表名str table_name，条件dict condition
        if not self.exists(table_name):
            return None
        cur = self.connect.cursor()        
        sql_tuple = ()
        cond_tuple = ()
        if condition:
            if condition['begin_time'] < condition['end_time']:    # 查询条件中是否存在开始和结束时间
                sql_tuple += ('time >= ?', 'time <= ?')
                cond_tuple += (condition.pop('begin_time'), condition.pop('end_time'))
            else:
                condition.pop('begin_time')
                condition.pop('end_time')
            for key in condition:    # 将查询条件中的表头和值分开                
                if condition[key]:
                    sql_tuple += (key + ' LIKE ?', )
                    cond_tuple += ('%'+condition[key]+'%', )

        if sql_tuple and cond_tuple:
            sql = 'SELECT * FROM %s WHERE %s' % (table_name, ' AND '.join(sql_tuple))
            cur.execute(sql, cond_tuple)
        else:
            cur.execute('SELECT * FROM ' + table_name)

        table_data = cur.fetchall()
        cur.close()
        self.connect.commit()
        if len(table_data) > 10000:
            table_data = table_data[-10000:]
        return table_data

    def exists(self, table_name):    # 判断表格是否存在，表名str table_name
        cur = self.connect.cursor()
        cur.execute('SELECT name FROM sqlite_master WHERE type = "table"')
        lists = cur.fetchall()
        cur.close()
        self.connect.commit()
        if lists == []:
            return False
        name_list = [lis[0] for lis in lists]
        if table_name in name_list:
            return True
        else:
            return False
    
    def drop(self,table_name):    # 删除表格，表名str table_name
        cur = self.connect.cursor()
        cur.execute('DROP TABLE ' + table_name)
        cur.close()
        self.connect.commit()

    def all_table(self):    # 列出所有表格
        cur = self.connect.cursor()
        cur.execute('SELECT name FROM sqlite_master WHERE type = "table"')
        lists = cur.fetchall()
        cur.close()
        self.connect.commit()
        if lists == []:
            return []
        name_list = [lis[0] for lis in lists]
        return name_list

    def count_row(self, table_name):    # 查询表格的行数，表名str table_name
        cur = self.connect.cursor()
        cur.execute('SELECT count(*) FROM ' + table_name)
        count = cur.fetchone()
        cur.close()
        self.connect.commit()
        return count[0]

    def count_col(self, table_name):    # 查询表格的列数，并列出表头，表名str table_name
        cur = self.connect.cursor()
        cur.execute('SELECT * FROM ' + table_name + ' LIMIT 1')
        count = cur.fetchone()
        cur.execute('SELECT sql FROM sqlite_master WHERE type = "table" AND name = ?', (table_name,))
        sql = cur.fetchone()
        cur.close()
        self.connect.commit()
        cn = len(count) if count else 0
        return cn, sql[0]

    def re_name(self, table_name, new_name):    # 修改表名，旧表名str table_name，新表名str new_name
        cur = self.connect.cursor()
        cur.execute('ALTER TABLE ' + table_name + ' RENAME TO ' + new_name)
        cur.close()
        self.connect.commit()


def main():    # 直接运行本程序可对数据库进行管理
    while True:
        print(u'''
        L. 列出数据库中的所有表
        D. 删除数据库中的表
        E. 查询数据库中是否存在该表
        CR. 查询表中的行数
        CC. 查询表中的列数和表头
        RN. 修改表名
        Q. 退出
        ''')
        print(u'输入数据库名称(Q-退出): ')
        dbname = input()
        if dbname == 'Q':
            break
        if not os.path.exists(dbname):
            print(u'不存在该数据库')
            continue
        db = MyDataBase(dbname)
        while True:
            print(u'输入操作: ')
            do = input()
            if do == 'L':
                for table in db.all_table():
                    print(table)
            elif do == 'D':
                print(u'输入要删除的表名(可输入多个，以空格隔开): ')
                table_name = input()
                name_list = table_name.split(' ')
                for name in name_list:
                    if db.exists(name):
                        db.drop(name)
                        if not db.exists(name):
                            print(u'%s 删除成功' % name)
                        else:
                            print(u'%s 删除失败' % name)
                    else:
                        print(u'%s 不存在' % name)
            elif do == 'E':
                print(u'输入要查询的表名: ')
                table_name = input()
                if db.exists(table_name):
                    print(u'%s 存在' % table_name)
                else:
                    print(u'%s 不存在' % table_name)
            elif do == 'CR':
                print(u'输入要查询的表名: ')
                table_name = input()
                if not db.exists(table_name):
                    print(u'%s 不存在' % table_name)
                    continue
                cn = db.count_row(table_name)
                print(u'%s 的行数: %s' % (table_name, cn))
            elif do == 'CC':
                print(u'输入要查询的表名: ')
                table_name = input()
                if not db.exists(table_name):
                    print(u'%s 不存在' % table_name)
                    continue
                (cn, sql) = db.count_col(table_name)
                print(u'%s 的列数: %s' % (table_name, cn))
                print(sql)
            elif do == 'RN':
                print(u'输入要修改的表名')
                table_name = input()
                print(u'输入新的表名')
                new_name = input()
                if not db.exists(table_name):
                    print(u'%s 不存在' % table_name)
                    continue
                if db.exists(new_name):
                    print(u'%s 已存在' % new_name)
                    continue
                db.re_name(table_name, new_name)
                if db.exists(new_name):
                    print(u'%s 修改成功' % new_name)
                    continue
                else:
                    print(u'%s 修改失败' % new_name)

            elif do == 'Q':
                db.disconnect()
                break


if __name__ == '__main__':
    main()
