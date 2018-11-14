#!/usr/bin/python3
# -*- coding: utf-8 -*-

# filename: douyu_database_manage.py
# version: 1.0.0
# date: 2017-12-20
# last date: 2018-10-03
# os: windows


import os
import re
import sqlite3
import time


class MyDataBase(object):
    def __init__(self, dbname):
        self.db_name = dbname    # 数据库文件名
        self.connection = sqlite3.connect(self.db_name)    # 连接数据库，不存在则创建
        self.cursor = self.connection.cursor()

    def disconnect(self):    # 关闭数据库连接
        self.cursor.close()
        self.connection.commit()
        self.connection.close()

    def create(self, table_name, table_header):
        # 创建表格，表名str table_name，表头list table_header
        sql = 'CREATE TABLE IF NOT EXISTS %s (%s)' % (table_name, ', '.join(table_header))
        self.cursor.execute(sql)
        self.connection.commit()
        return self.check_table(table_name, table_header)

    def insert(self, table_name, table_data):
        # 判断表格是否存在，在表格中新增数据，表名str table_name，数据list table_data
        if not self.table_exists(table_name):    # 判断是否存在该表格
            return False
        sql = 'INSERT INTO %s VALUES (%s)' % (table_name, ', '.join(['?']*len(table_data)))
        self.cursor.execute(sql, tuple(table_data))
        self.connection.commit()
        return True

    def insert_n(self, table_name, table_data):
        # 不判断表格是否存在，在表格中新增数据，表名str table_name，数据list table_data
        sql = 'INSERT INTO %s VALUES (%s)' % (table_name, ', '.join(['?']*len(table_data)))
        self.cursor.execute(sql, tuple(table_data))
        self.connection.commit()

    def insert_dict(self, table_name, table_data):
        # 不判断表格是否存在，在表格中新增数据，表名str table_name，数据dict table_data
        header = ()
        data = ()
        for key in table_data:
            header += (key,)    # 获取行列名的元组
            data += (table_data[key],)    # 获取数据的元组
        sql = 'INSERT INTO %s (%s) VALUES (%s)' % (
            table_name, ', '.join(header), ', '.join(['?']*len(data)))
        self.cursor.execute(sql, data)
        self.connection.commit()        

    def update(self, table_name, data, condition=None):
        # 更新表格中的数据，表名str table_name，数据dict data，条件dict condition
        if not self.table_exists(table_name):
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
            
        self.cursor.execute(sql, data_tuple)
        self.connection.commit()
        return True                

    def query_one(self, table_name, field=None, condition=None, exclude=None):
        # 查询第一条数据，表名str table_name，获取字段str field，条件dict condition，排除条件list exclude
        if not self.table_exists(table_name):
            return None        
        sql_tuple = ()
        cond_tuple = ()
        field_str = field if field else '*'
            
        if condition:
            if 'begin_time' in condition and 'end_time' in condition:    # 查询条件中是否存在开始和结束时间
                sql_tuple += ('time >= ?', 'time <= ?')
                cond_tuple += (condition.pop('begin_time'), condition.pop('end_time'))
            elif 'begin_time' in condition:
                sql_tuple += ('time >= ?', )
                cond_tuple += (condition.pop('begin_time'), )
            elif 'end_time' in condition:
                sql_tuple += ('time <= ?', )
                cond_tuple += (condition.pop('end_time'), )
            for key in condition:    # 将查询条件中的表头和值分开      
                sql_tuple += (key + ' LIKE ?', )
                cond_tuple += (condition[key], )
        if exclude:
            for each in exclude:
                sql_tuple += (each[0] + ' != ?', )
                cond_tuple += (each[1], )

        if sql_tuple and cond_tuple:
            sql = 'SELECT %s FROM %s WHERE %s' % (field_str, table_name, ' AND '.join(sql_tuple))
            self.cursor.execute(sql, cond_tuple)
        else:
            self.cursor.execute('SELECT %s FROM %s' % (field_str, table_name))

        return self.cursor.fetchone()

    def query_all(self, table_name, field=None, condition=None, exclude=None):
        # 查询所有数据，表名str table_name，获取字段str field，条件dict condition，排除条件list exclude
        if not self.table_exists(table_name):
            return None        
        sql_tuple = ()
        cond_tuple = ()
        field_str = field if field else '*'
            
        if condition:
            if 'begin_time' in condition and 'end_time' in condition:    # 查询条件中是否存在开始和结束时间
                sql_tuple += ('time >= ?', 'time <= ?')
                cond_tuple += (condition.pop('begin_time'), condition.pop('end_time'))
            elif 'begin_time' in condition:
                sql_tuple += ('time >= ?', )
                cond_tuple += (condition.pop('begin_time'), )
            elif 'end_time' in condition:
                sql_tuple += ('time <= ?', )
                cond_tuple += (condition.pop('end_time'), )
            for key in condition:    # 将查询条件中的表头和值分开      
                sql_tuple += (key + ' LIKE ?', )
                cond_tuple += (condition[key], )
        if exclude:
            for each in exclude:
                sql_tuple += (each[0] + ' != ?', )
                cond_tuple += (each[1], )

        if sql_tuple and cond_tuple:
            sql = 'SELECT %s FROM %s WHERE %s' % (field_str, table_name, ' AND '.join(sql_tuple))
            self.cursor.execute(sql, cond_tuple)
        else:
            self.cursor.execute('SELECT %s FROM %s' % (field_str, table_name))

        return self.cursor.fetchall()
    
    def table_exists(self, table_name):    # 判断表格是否存在，表名str table_name
        self.cursor.execute('SELECT name FROM sqlite_master WHERE type = "table"')
        lists = self.cursor.fetchall()
        if lists == []:
            return False
        name_list = [lis[0] for lis in lists]
        if table_name in name_list:
            return True
        else:
            return False
    
    def del_table(self,table_name):    # 删除表格，表名str table_name
        self.cursor.execute('DROP TABLE ' + table_name)
        self.connection.commit()

    def all_table(self):    # 列出所有表格
        self.cursor.execute('SELECT name FROM sqlite_master WHERE type = "table"')
        lists = self.cursor.fetchall()
        if lists == []:
            return []
        name_list = [lis[0] for lis in lists]
        return name_list

    def count_row(self, table_name):    # 查询表格的行数，表名str table_name
        self.cursor.execute('SELECT count(*) FROM ' + table_name)
        count = self.cursor.fetchone()
        return count[0]

    def count_col(self, table_name):    # 查询表格的列数，并列出表头，表名str table_name
        self.cursor.execute('SELECT * FROM ' + table_name + ' LIMIT 1')
        count = self.cursor.fetchone()
        self.cursor.execute('SELECT sql FROM sqlite_master WHERE type = "table" AND name = ?', (table_name,))
        sql = self.cursor.fetchone()
        cn = len(count) if count else 0
        return cn, sql[0]

    def re_name(self, table_name, new_name):    # 修改表名，旧表名str table_name，新表名str new_name
        self.cursor.execute('ALTER TABLE ' + table_name + ' RENAME TO ' + new_name)
        self.connection.commit()

    def check_table(self, table_name, columns):    # 检查表格的表头是否正确
        self.cursor.execute('SELECT sql FROM sqlite_master WHERE type = "table" AND name = ?', (table_name,))
        sql = self.cursor.fetchone()
        cols = re.search('\((.*)\)', sql[0]).group(1)
        cols_list = cols.split(', ')
        return cols_list == list(columns)


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
                    if db.table_exists(name):
                        db.del_table(name)
                        if not db.table_exists(name):
                            print(u'%s 删除成功' % name)
                        else:
                            print(u'%s 删除失败' % name)
                    else:
                        print(u'%s 不存在' % name)
            elif do == 'E':
                print(u'输入要查询的表名: ')
                table_name = input()
                if db.table_exists(table_name):
                    print(u'%s 存在' % table_name)
                else:
                    print(u'%s 不存在' % table_name)
            elif do == 'CR':
                print(u'输入要查询的表名: ')
                table_name = input()
                if not db.table_exists(table_name):
                    print(u'%s 不存在' % table_name)
                    continue
                cn = db.count_row(table_name)
                print(u'%s 的行数: %s' % (table_name, cn))
            elif do == 'CC':
                print(u'输入要查询的表名: ')
                table_name = input()
                if not db.table_exists(table_name):
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
                if not db.table_exists(table_name):
                    print(u'%s 不存在' % table_name)
                    continue
                if db.table_exists(new_name):
                    print(u'%s 已存在' % new_name)
                    continue
                db.re_name(table_name, new_name)
                if db.table_exists(new_name):
                    print(u'%s 修改成功' % new_name)
                    continue
                else:
                    print(u'%s 修改失败' % new_name)

            elif do == 'Q':
                db.disconnect()
                break


if __name__ == '__main__':
    main()
