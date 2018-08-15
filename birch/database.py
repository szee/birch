#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-
# Part of Birch. See LICENSE file for full copyright and licensing details.

'''
database.py -- отдельное приложение-хэндлер базы данных:

из-за того, что то ли я -- криворукая мудила, то ли sqlite реально не
поддерживает внешние ключи, все представления приходится делать здесь.
(через жопу, кстати.)

в таблице desks -- permission_list -- это список кухонь, с которых можно делать заказы на этом деске
(ричи, ты очень удобно и понятно это сделал, ога)

еще момент: файл сейчас рефакторится. тут есть много говна и легаси. скоро этот модуль
разделится на нормальный пакет, поэтому ВЕСЬ код будет пересмотрен
'''

import sqlite3 as db
import time
import re
import random
import json
import os
from string import ascii_letters, digits
from .timetools import nowTime, strTimeToInt, intTimeToStr, getStatus
from .order_pool import order_pool
import requests
import threading

from . import utils

name = __name__.capitalize()

class VegangaDB:
    '''
    хэндлер для базы данных кипера (название осталось, что бы не нарушать совместимость)
    (а вообще клевое название для технологии, пускай остается)

    db = VegangaDB('/path/to/db')

    задача этой бд -- сохранить определенные данные (но не передать)
    в консистентной форме. получать информацию от бд могут только администраторы
    с определенными полномочиями.

    большинство методов является фактически алиасами sql запросов,
    либо представлениями таблиц (например, метод get_menu())


    абстракции:
        кассовые смены называются шифтами (shift -- +-"смена");
        кассовые аппараты называются десками (desk; shift desk -- формально, 
                                на каком аппарате/в каком зале открыт шифт);

    основные данные в базе -- данные о шифтах. все остальные (включая заказы)
    кокретизация данных шифта.

    абстракции созданы потому, что реализация кассовой смены здесь
    реализована не по законодательству РФ, а по требованиям поставленной задачи.

    открывается шифт только с первым заказом, открыть может любой кассир
    закрыть шифт может только администратор, причем ответственный за свой деск

    после закрытия шифта, и формирования z-отчета шифт редактировать ЗАПРЕЩЕНО 
    вне зависимости от ситуации.
    в данные шифта можно добавлять данные, но не редактировать или удалять
    '''
    # возврат ошибки реализован через словарь, а не через raise. можно
    # что-то и получше придумать 


    def __init__(self, path, logging=False):
        self.path = path
        if not os.path.exists(path):
            utils.log(name, 'warn','файл базы в '+str(path)+' не найден')
            utils.log(name, 'warn','создание пустой базы...')
            init_database(path)

        self.conn = db.connect(self.path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.lock = threading.Lock()
        self.logging = logging
        
        
        self.cache = {} #кеш табиц и др. из базы или откуда либо вообще (любые данные)
        self.update_cache()
        self.pool = order_pool(self) # используем order_pool как помощник в обработке заказов
        utils.log(name, 'info','база успешно инициализирована')


    def update_cache(self):
        utils.log(name, 'dbug','кэш базы обновлен')
        self.cache['workers'] = {}
        result = self.fetchQuery('select id, position, department_id from workers')
        for row in result:
            positions = row[1].split(';')
            self.cache['workers'][row[0]] = {'position':positions,
                                             'department':row[2]
                                            }
            if 'waiter' in positions:
                self.cache['workers'][row[0]]['desk_id']=self.fetchQuery('select id from desks where department='+str(row[2]))[0][0]
            if 'cooker' in positions:
                self.cache['workers'][row[0]]['kitchen_id']=self.fetchQuery('select kitchen_id from kitchens where department_id='+str(row[2]))[0][0]

        self.cache['menu'] = {}
        result = self.fetchQuery('select id, name from menu')
        for row in result:
            self.cache['menu'][row[0]] = {'name':row[1]}
        

##############################################################################################################
#############################обработка и реадктирование отделов и кухонь######################################
##############################################################################################################


    def new_department(self, name):
        '''задел на будущее'''
        pass
    
    def del_department(self, id):
        '''задел на будущее'''
        pass

    def get_departments(self):
        '''
        метод устарел.
        выводит список всех отделов, которые существуют в базе
        '''
        utils.log(name, 'dbug','использован устаревший метод db.get_departments!')
        result = self.fetchQuery('select department_id, department_name from departments')
        out = {}
        for row in result:
            out[row[0]] = row[1]
        return out

    def get_departments_extended(self):
        '''
        выводит информацию о всех отделах, которые существуют в базе
        '''
        result = self.fetchQuery('select department_id, department_name, department_color from departments')
        out = []
        for row in result:
            out.append({'id':row[0],'name':row[1],'color':row[2]})
        return out

    def get_kitchens(self):
        result = self.fetchQuery('select kitchen_id, kitchen_name, department_id from kitchens')
        out = []
        for row in result:
            out.append({'id':row[0], 'name':row[1], 'department_id':row[2]})
        return out

    def get_kitchen_info(self,kitchen_id):
        kitchen_id = int(kitchen_id)
        result = self.fetchQuery('select kitchen_name, department_id from kitchens where kitchen_id={0}'.format(kitchen_id))[0]
        return {'name':result[0],'department_id':result[1]}

##############################################################################################################
#####################################обработка заказов и инвойсов#############################################
##############################################################################################################


    def new_order(self, orderlist, amount, pay_method, waiter_id, desk_id, discount, comment, add_invoice=False):
        '''
        устарел. пользоваться при особой необходимости
        добавляет в базу заказов собственно информацию о заказе
        '''
        utils.log(name, 'dbug','использован устаревший метод db.new_order!')
        open_desks = self.get_open_desks()
        if desk_id not in open_desks.keys():
            self.open_shift(waiter_id,desk_id)
            
            time.sleep(1) #для надежности, что бы шифт открылся раньше приема заказа
        self.commitQuery('insert into orders (orderlist, amount, ordertime, desk_id, pay_method, created_id, discount,comment) values (\'{0}\',{1},{2},{3},{4},{5},{6},\'{7}\')'.format(orderlist,amount,strTimeToInt(nowTime()),desk_id,pay_method,waiter_id, discount,comment))
        order_id = self.fetchQuery('select last_insert_rowid()')
        return order_id[0][0] # cause order_id = [(x,)]... WATAFAK



    def new_order_extended(self, waiter_id, orderlist, amount, pay_method, comment, invoice=False):
        '''
        добавляет в базу заказов информацию о НОВОМ заказе

        invoice=False -- если не указан, без инвойса
                         если строка (ну или "нечисло") -- создается новый инвойс
                         если число -- заказ добавляется в инвойс
        подробней об инвойсах в invoice.md
        '''
        utils.log(name, 'dbug','новый заказ! '+str(comment)+"заказ: "+str(orderlist))
        desk_id=0

        if not waiter_id in self.cache['workers']:
            raise Exception('невалидный id работника.')

        waiter_data = self.cache['workers'][waiter_id]
        if 'waiter' in waiter_data['position']:
            desk_id = waiter_data['desk_id']

        if desk_id == 0:
            raise Exception('в кэше не найден деск, за которым стоит данный работник')

        open_desks = self.get_open_desks()
        if desk_id not in open_desks.keys():
            self.open_shift(waiter_id,desk_id)
            time.sleep(0.5) #для надежности, что бы шифт открылся раньше приема заказа

        base_amount = 0
        list_string = '' # желательно это чудо переименовать такто
        for index, position in enumerate(orderlist):
            base_amount += self.get_position_info(position)['amount']
            list_string += str(position)+';' if index+1 != len(orderlist) else str(position)+''
            self.add_stock(position, -1)
        
        discount = base_amount - amount
        
        self.commitQuery('insert into orders (orderlist, amount, ordertime, desk_id, pay_method, created_id, discount,comment) values (\'{0}\',{1},{2},{3},{4},{5},{6},\'{7}\')'.format(list_string,amount,strTimeToInt(nowTime()),desk_id,pay_method,waiter_id, discount,comment))
        order_id = self.fetchQuery('select last_insert_rowid()')[0][0]

        ####
        try:
            invoice = int(invoice)
        except:
            pass

        if not invoice:
            return {'order_id':order_id}
        elif type(invoice) is int:
            self.add_order_to_invoice(invoice, order_id)
            return {'order_id':order_id}
        elif type(invoice) is str:
            invoice_id = self.new_invoice(invoice, order_id, waiter_id)
            return {'order_id':order_id,'invoice_id':invoice_id}

    


    def cook_order(self, order_id, cooker_id, assembled=False):
        '''
        меняет статус заказа на приготовленный (но не собраный)
        '''
        cookers = self.fetchQuery('select cook_id from orders where id='+str(order_id))[0][0] 
        cooker_id = cookers+str(cooker_id) if cookers != None else str(cooker_id)
        if assembled:
            self.commitQuery('update orders set status=\'assembled\', cook_id=\'{0}\' where id={1}'.format(cooker_id, order_id))
        else:
            self.commitQuery('update orders set status=\'cooking\', cook_id=\'{0};\' where id={1}'.format(cooker_id, order_id))



    def done_order(self, order_id):
        '''
        меняет статус заказа на выданный
        с этого момента заказ изменить более нельзя
        '''
        self.commitQuery('update orders set status=\'gaved\' where id={0}'.format(order_id))



##############################################################################################################



    def new_invoice(self, name, orders_list, created_id):
        # orders_list --  это НЕ список позиций, а список ЗАКАЗОВ.
        # в orders_list указываются ссылки на заказы, в которых уже есть позиции
        '''
        создает новый инвойс.
        подробнее об инвойсах в invoice.md
        '''
        if type(orders_list) is int:
            invoice_orders = '('+str(orders_list)+')'
        elif type(orders_list) is list:
            invoice_orders = str(tuple(orders_list)) # приводим list в вид tuple, без replace('[','(')
        elif type(orders_list) is tuple:
            invoice_orders = str(orders_list)
        else:
            raise Exception('orderlist должен быть int, list или tuple')
        
        orders = self.fetchQuery('select amount from orders where id in '+invoice_orders)
        total_amount = 0 
        for amount in orders:
            total_amount += amount[0] #cause amount = (x,)

        self.commitQuery('insert into invoices (invoice_name, invoice_orders, invoice_amount, created_time, created_id) values (\'{0}\',\'{1}\',{2}, {3}, {4})'.format(name, orders_list, total_amount, strTimeToInt(nowTime()),created_id))

        return self.fetchQuery('select last_insert_rowid()')[0][0]



    def add_order_to_invoice(self, invoice_id, order_id):
        '''
        добавляет ОДИН ЕДИНСТВЕННЫЙ ID в список заказов инвойса
        '''
        try:
            invoice_id = int(invoice_id)
            order_id = str(order_id)
        except:
            raise Exception('invoice_id не число и/или order_id не типа databse.LIST')
        
        try:
            order_amount = self.fetchQuery('select amount from orders where id={0}'.format(order_id))[0][0]
        except:
            raise Exception('невалидный order_id')
        try:
            invoice_data = self.fetchQuery('select invoice_orders, invoice_amount from invoices where invoice_id={0} and is_payed=0'.format(invoice_id))[0]
        except:
            raise Exception('невалидный invoice_id')
        if str(order_id) in invoice_data[0]: #order_id in invoice_orders
            raise Exception('заказ уже прикреплен к инвойсу')

        total_amount = invoice_data[1] + order_amount
        total_orders = invoice_data[0] + ';' + order_id

        self.commitQuery('update invoices set invoice_orders=\'{0}\', invoice_amount={1} where invoice_id={2}'.format(total_orders, total_amount, invoice_id))



    def pay_invoice(self, invoice_id): #, pay_method):
        '''
        "погасить" заказ формально. меняет is_payed с 0 на 1
        '''
        try: 
            int(invoice_id)
        except:
            raise Exception('невалидный invoice_id: '+invoice_id)
        try:
            invoice_data = self.fetchQuery('select invoice_amount, is_payed from invoices where invoice_id={0}'.format(invoice_id))[0]
        except:
            raise Exception('invoice_id не найден: '+invoice_id)
        if invoice_data[1] == 1:
            raise Exception('инвойс уже погашен: '+invoice_id)

        self.commitQuery('update invoices set is_payed=1, payed_time={0} where invoice_id={1}'.format(strTimeToInt(nowTime()),invoice_id))



    def get_invoices(self, full_order_list=False, by_name=False):
        '''
        выдает список непогашеных инвойсов
        TODO: при удалении позиции, которая существует в непогашеном инвойсе,
              вылетает исключение, якобы нельзя конвертировать несуществующий id в название
              быстрофиксом стала настройка в self.get_menu_names(strict=False)
              по=хорошему она должна обрабатываться здесь, но нет времени ее реализовать.
        '''
        if not full_order_list and by_name:
            raise Exception('нельзя получить имена позиций без full_order_list')

        invoice_data = self.fetchQuery('select invoice_id, invoice_name, invoice_orders, invoice_amount, created_time from invoices where is_payed=0')
        out = []
        for invoice in invoice_data:
            x = {'id':invoice[0],
                 'name':invoice[1],
                 'amount':invoice[3],
                 'create_time':invoice[4]
                 }

            if full_order_list:
                order_list = self.fetchQuery('select orderlist from orders where id in ('+invoice[2].replace(';',',')+')')
                order_list2 = [x[0] for x in order_list] # достаем из последовательностей для удобства
                order_list = [] # очищаем order_list
                for o in order_list2:
                    order_list += [int(a) for a in o.split(';')] # конвертируем из str в int

                if by_name:
                    x['position_list'] = self.get_menu_names(*order_list)
                else:
                    x['position_list'] = order_list

            else:
                x['orders'] = invoice[2].split(';')

            out.append(x)

        return out


    def get_invoice_info(self, invoice_id, full_order_list=False, by_name=False):
        '''
        отдает информацию о конкретном инвойсе
        в отличии от VegangaDB.get_invoices, может отдавать информацию по закрытым заказам
        '''
        try: int(invoice_id)
        except:
            raise Exception('невалидный invoice_id: '+invoice_id)

        if not full_order_list and by_name:
            raise Exception('нельзя получить имена позиций без full_order_list')

        try:
            invoice = self.fetchQuery('select invoice_id, invoice_name, invoice_orders, invoice_amount, created_time, payed_time from invoices where invoice_id='+str(invoice_id))[0]
        except:
            raise Exception('invoice_id не найден')

        out = {'id':invoice[0],
               'name':invoice[1],
               'amount':invoice[3],
               'create_time':invoice[4],
               'is_payed':False
               }

        if full_order_list:
            order_list = self.fetchQuery('select orderlist from orders where id in ('+invoice[2].replace(';',',')+')')
            order_list2 = [x[0] for x in order_list] # достаем из последовательностей для удобства
            order_list = [] # очищаем order_list
            for o in order_list2:
                order_list += [int(a) for a in o.split(';')] # конвертируем из str в int

            if by_name:
                out['position_list'] = self.get_menu_names(*order_list)
            else:
                out['position_list'] = order_list

        else:
            out['orders'] = invoice[2].split(';')
        
        if invoice[5]:
            out.update({'is_payed':True,'payed_time':invoice[5]})
        
        return out
    


##############################################################################################################
##########################################шифты и репорты#####################################################
##############################################################################################################


    def open_shift(self, opened_id, desk_id):
        '''
        открыть шифт может любой кассир, напрямую, либо через первый заказ
        если на деске есть еще открытый шифт, то новый открыть нельзя.
        '''
        utils.log(name, 'info','шифт на деске '+str(desk_id)+' открыт.')
        if not self.fetchQuery('select * from desks where id={0}'.format(desk_id)): # проверяем, есть ли вообще деск
            raise Exception('деск не зарегестрирован в системе')

        result = self.fetchQuery('select shift_id from shifts where (close_time is null or reports_list is null) and desk_id={0}'.format(desk_id))
        if result:
            raise Exception('последний шифт №'+str(result[0][0])+' не закрыт (или не содержит z-отчета)')
        else:
            self.commitQuery('insert into shifts (desk_id, open_time,opened_id) values ({0},{1},{2})'.format(desk_id,strTimeToInt(nowTime()),opened_id))
            result = self.fetchQuery('select shift_id, desk_id from shifts where close_time is null')
            for x in result:
                if x[1] == desk_id: #возвращаем только id шифта открываемого деска
                    result = x[0] 

            return {'text':result,'result':'done'}


    def close_shift(self, desk_id, closed_id):
        '''
        закрыть шифт может только администратор, у которого есть доступ к деску данного шифта
        здесь на всякий случай еще раз проверяется, есть ли права у закрывающего шифт 
        (вообще-то, проверять надо на всякий пожарный несколько раз)
        '''
        utils.log(name, 'info','шифт на деске '+str(desk_id)+' закрыт.')
        try:
            user = self.fetchQuery('select department_id, position from workers where id={0}'.format(closed_id))[0]    # cause return is [x]
        except:
            raise Exception('пользователь не найден')
        
        try:
            desk_owner = self.fetchQuery('select department from desks where id={0}'.format(desk_id))[0][0]         # cause return is [(x,)]
        except:
            raise Exception('деск не найден')

        # user[0] == 1 поскольку department(1) = service
        if (user[0] not in [1,desk_owner]) and 'admin' not in user[1]:
            raise Exception('неадминистратор или сотрудник из другого отдела не может закрыть этот шифт')

        shift_id = self.fetchQuery('select shift_id from shifts where desk_id={0} and close_time is null'.format(desk_id))[0][0]
        self.commitQuery('update shifts set close_time={0}, closed_id={1} where desk_id={2} and close_time is null'.format(strTimeToInt(nowTime()), closed_id, desk_id))
        
        self.make_z_report(desk_id)

        return shift_id
            

            
    def make_x_report(self, desk_id):
        '''
        формирует x-отчет по форме, приведенной ниже.
        x-отчет можно проводить в любое время на открытой кассе 
        только администраторам.
        '''
        report = {"daily_report_id":0,
                  "desk_id":int(desk_id),
                  "report_time":0,
                  "start_time":0,
                  "opened_id":0,
                  "amount":{
                      "cash":0,
                      "card_transfer":0,
                      "acquiring": 0,
                      "bitcoin": 0,
                      "etherium": 0
                  },
                  "pf_amount":{
                      "cash":0
                  },
                  "total_amount":0,
                  "total_bills":0,
                  "average_bill_amount": 0,
                  "average_bill_value": 0
                  }
        
        shift = self.fetchQuery('select shift_id, open_time, opened_id, reports_list from shifts where close_time is null and desk_id={0}'.format(desk_id))
        if not len(shift):
            raise Exception('нельзя составлять x-отчет у закрытого деска')
            
        shift_id,start_time, opened_id, reports = shift[0]
        try:
            report['daily_report_id'] = len(reports.split(';'))+1 # если reports is None (нет отчетов за шифт)
        except:
            report['daily_report_id'] = 1                         # тогда этот отчет будет первым
     
        report['report_time'] = strTimeToInt(nowTime())
        report['start_time']  = int(start_time)
        report['opened_id']   = int(opened_id)
        orders = self.fetchQuery('select orderlist, amount, pay_method from orders where ordertime>={0} and ordertime<={1}'.format(start_time,strTimeToInt(nowTime())))
        total_bill_value = 0
        for order in orders:
            orderlist = order[0].split(';')
            amount = order[1]
            payment = order[2]
            if payment == 10:
                report['amount']['cash'] += amount
            elif payment == 11:
                report['amount']['card_transfer'] += amount
            elif payment == 13:
                report['amount']['acquiring'] += amount
            elif payment == 12:
                report['pf_amount']['cash'] += amount
            elif payment == 20:
                report['amount']['bitcoin'] += amount
            elif payment == 21:
                report['amount']['etherium'] += amount
            for x in orderlist:
                if len(x):
                    total_bill_value += 1

        report['total_amount'] = int(sum(report['amount'].values()) + sum(report['pf_amount'].values()))  
        report['total_bills'] = len(orders)
        report['average_bill_value'] = float('{0:.2f}'.format(total_bill_value / len(orders)))
        report['average_bill_amount'] = float('{0:.2f}'.format(report['total_amount'] / len(orders)))
        json_report = str(report).replace("'",'"') # заменяем обычные кавычки на двойные, как того требует стандарт json

        self.commitQuery('insert into reports (report_time, type, json) values ({0},\'x\', \'{1}\')'.format(strTimeToInt(nowTime()),json_report))
        report_id = self.fetchQuery('select last_insert_rowid()')[0][0]
        try:
            reports += ';{0}'.format(report_id)
        except:
            reports = str(report_id)
        
        self.commitQuery('update shifts set reports_list=\'{0}\' where shift_id={1}'.format(reports,shift_id))
        return report_id


    def make_z_report(self, desk_id):
        '''
        составляет репорт по последнему ЗАКРЫТОМУ шифту, деск указан в аргументе.
        проверка кем составляется отчет здесь смысла не имеет. (make_z_report вызывается сраз после закрытия шифта)
        форма указана в report'e
        '''

        shift_id = self.fetchQuery('select max(shift_id) from shifts where desk_id={0}'.format(desk_id))[0][0]
        shift = self.fetchQuery('select open_time, close_time, opened_id, closed_id, reports_list from shifts where shift_id={0}'.format(shift_id))
        if not len(shift):
            raise Exception('нельзя составить z-отчет с открытым деском')
        shift_reports = shift[0][4]
        try:    # смотрим, есть ли у шифта z-отчет. z-отчет всегда будет последним в отчетах.
            last_shift_report = shift_reports.split(',')[-1]
        except: # если отчетов вообще нет, то тогда говорим, что последний -- нулевой (не существует)
            last_shift_report = 0

        if last_shift_report:
            last_report_type = self.fetchQuery('select type from reports where id={0}'.format(last_shift_report))
            if last_report_type == 'z':
                raise Exception('отчет уже сформирован под номером: '+str(last_shift_report))

        report = {"report_time":strTimeToInt(nowTime()),
                  "start_time": shift[0][0],
                  "close_time": shift[0][1],
                  "opened_id": shift[0][2],
                  "closed_id": shift[0][3],
                  "amount":{
                      "cash":0,
                      "card_transfer":0,
                      "acquiring": 0,
                      "bitcoin": 0,
                      "etherium": 0
                  },
                  "pf_amount":{
                      "cash":0
                  },
                  "discount_cost":0,
                  "total_amount":0,
                  "total_bills":0,
                  "average_bill_amount": 0,
                  "average_bill_value": 0,
                  "encashment":0,
                  "cash_deposit":0
                  }
                
        orders = self.fetchQuery('select orderlist, amount, pay_method from orders where ordertime>={0} and ordertime<={1}'.format(shift[0][0],shift[0][1]))
        total_bill_value = 0
        for order in orders:
            orderlist = order[0].split(';')
            amount = order[1]
            payment = order[2]
            if payment == 10:
                report['amount']['cash'] += amount
            elif payment == 11:
                report['amount']['card_transfer'] += amount
            elif payment == 13:
                report['amount']['acquiring'] += amount
            elif payment == 12:
                report['pf_amount']['cash'] += amount
            elif payment == 20:
                report['amount']['bitcoin'] += amount
            elif payment == 21:
                report['amount']['etherium'] += amount

            for x in orderlist:
                if len(x):
                    total_bill_value += 1

        report['total_amount'] = sum(report['amount'].values()) + sum(report['pf_amount'].values())  
        report['total_bills'] = len(orders)
        report['average_bill_value'] = total_bill_value / len(orders)
        report['average_bill_amount'] = report['total_amount'] / len(orders)
        json_report = str(report).replace("'",'"') # заменяем обычные кавычки на двойные, как того требует стандарт json

        self.commitQuery('insert into reports (report_time, type, json) values ({0}, \'z\', \'{1}\')'.format(strTimeToInt(nowTime()), json_report))
        report_id = self.fetchQuery('select last_insert_rowid()')[0][0]
        try:
            shift_reports += ';{0}'.format(report_id)
        except: # if shift_report is nul then shift_report is report_id
            shift_reports = str(report_id)
        
        self.commitQuery('update shifts set reports_list=\'{0}\' where shift_id={1}'.format(shift_reports,shift_id))
        return report_id



    def make_kitchen_report(self, kitchen_id, start_time, end_time):
        '''
        метод нерабочий. использовать определенно не стоит
        '''
        if end_time == 'now':
            end_time = strTimeToInt(nowTime())
        report = {
                  "report_time":strTimeToInt(nowTime()),
                  "start_time": int(start_time),
                  "end_time": int(end_time),
                  "position_stats":{},
                  "total_amount":0,
                  "total_bills":0}
        orders = self.fetchQuery('select orderlist, amount, discount from orders where ordertime>={0} and ordertime<={1}'.format(start_time,end_time))

        stock = self.get_kitchen_stock(kitchen_id)
        for position in stock:
            report['position_stats'][int(position)] = 0

        for order in orders:
            orderlist = [int(a) for a in order[0].split(';')]
            if any(report['position_stats'].keys()) in orderlist:
                report['total_bills'] += 1

            for x in orderlist:
                if x in report['position_stats']:
                    report['position_stats'][x] +=1
        

        for x in report['position_stats']:
            report['total_amount'] += stock[x]['amount'] * report['position_stats'][x]
        
        return report
        #TODO: из-за того, что изначальная архитектура ВООБЩЕ не предполагала репорты с кухонь, мы их не возвращаем из базы, а генерим каждый раз
        #      ты просто говноед, рич...

    def get_report(self, report_id, full_name=True, str_time=True):
        try:
            resp = self.fetchQuery('select report_time, type, json from reports where id={0}'.format(report_id))[0]
        except:
            raise Exception('report_id не найден: '+str(report_id))

        out = {'id':int(report_id),
               'time':resp[0],
               'type':resp[1],
               'report':json.loads(resp[2])}
        

        if str_time:
            out['report']['report_time'] = intTimeToStr(out['report']['report_time'])[3:-3]
            out['report']['start_time'] = intTimeToStr(out['report']['start_time'])[3:-3]
            try: out['report']['close_time'] = intTimeToStr(out['report']['close_time'])[3:-3]
            except: pass
            out['time'] = intTimeToStr(out['time'])[3:-3]

        if full_name:
            out['report']['opened_id'] = self.get_employee_info(out['report']['opened_id'])['full_name']
            try: out['report']['closed_id'] = self.get_employee_info(out['report']['closed_id'])['full_name']
            except: pass
        
        return out


    def get_all_reports(self,start_time):
        '''
        выводит список последних репортов
        ''' 
        res = self.fetchQuery('select id, type, report_time, json from reports where report_time>={0}'.format(start_time))
        out = []
        for row in res:
            out.append({'id':row[0],
                        'type':row[1],
                        'time':row[2],
                        'report':json.loads(row[3])})
        
        return out

    def get_shift_reports(self, start_time, shift_id):
        '''
        выводит список последних репортов по шифту
        '''
        shift_reports = self.fetchQuery('select reports_list from shifts where shift_id={0}'.format(shift_id))[0][0]
        shift_reports = tuple(shift_reports.split(';'))
        res = self.fetchQuery('select id, type, json from reports where report_time={0} and id in {1}'.format(start_time, shift_reports))
        out = []
        for row in res:
            out.append({'id':row[0],
                        'type':row[1],
                        'report':json.loads(row[2])})
        return out
    
    def get_desk_reports(self, start_time, desk_id, full_name=True, str_time=True):
        try:
            start_time = int(start_time)
            desk_id = int(desk_id)
        except:
            raise Exception('невалидные аргументы: time:'+str(start_time)+', desk:'+str(desk_id))

        desk_shifts = [d for d in self.get_desk_shifts(desk_id) if d['open_time']>=start_time]
        reports_id = []
        for shift in desk_shifts:
            try:
                reports_id += shift['reports_list'].split(';')
            except:
                pass

        out = [r for r in map(lambda x: self.get_report(x,full_name=full_name, str_time=str_time),reports_id)]
        return out

    def get_department_reports(self, start_time, department_id, full_name=True, str_time=True):
        try:
            start_time = int(start_time)
            department_id = int(department_id)
        except:
            raise Exception('невалидные аргументы: time:'+str(start_time)+', desk:'+str(department_id))

        out = []
        department_desks = [d['id'] for d in self.get_desks_extended(department_id)]
        for d in department_desks:
            out += self.get_desk_reports(start_time, d, full_name=full_name, str_time=str_time)
        return out


    def get_open_desks(self):
        '''
        отдает открытые дески в данный момент

        x = db.get_open_desks()
        print(x)

        {'1':'18-04-11 12:00:34','3':'18-04-11 09:12:22'}
        '''
        result = self.fetchQuery('select desk_id, open_time from shifts where close_time is null')
        out = {}
        for x in result:
            out[x[0]] = intTimeToStr(x[1])
        return out

    def get_desks(self):
        '''
        список существующих в базе десков.
        отличается от get_desks_extended() тем, что дает информацию о десках без привязки к шифтам
        метод рабочий, устаревшим не считается.
        '''
        result = self.fetchQuery('select id, desk_name, department, permission_list from desks')
        out = []
        for row in result:
            out.append({'id':row[0],
                        'name':row[1],
                        'department':row[2],
                        'permission_list':[int(x) for x in row[3].split(';')]
                        })
        return out
    
    def get_desks_extended(self, department_id):
        '''
        список существующих в базе десков отдела с привязкой к шифтам
        отличается от get_desks() расширеной информацией по дескам
        с учетом шифтов, а так же выборкой по отделу
        '''
        department_id = int(department_id)

        if department_id == 1:
            desks = self.fetchQuery('select id, desk_name, permission_list from desks')
            # если service, то забираем все дески без вариантов
        else:
            desks = self.fetchQuery('select id, desk_name, permission_list from desks where department={0}'.format(department_id))

        shifts = self.fetchQuery('select shift_id, desk_id, open_time, opened_id, close_time, closed_id, reports_list from shifts where open_time>={0}'.format(strTimeToInt(nowTime())-100000000))
        # strTimeToInt(nowTime())-100000000 т.е. за последний месяц. считаем, что шифт не может быть открыт более 1 месяца

        out = []
        for row in desks:
            shift_data = None
            opened_time = 0
            for shift in shifts:
                #shift[1] is desk_id and row[0] is desk_id
                #shift[2] is open_time, здесь нет смысла фетчить постоянно в базу, это только нагрузит ее.
                if shift[1] == row[0] and shift[2] > opened_time:
                    shift_data = list(shift)


            if not shift_data:
                # TODO: облагородить как-то этот треш
                # по хорошему, надо как-то предупреждать 
                shift_data = [0,row[0],0,0,None,None,None]

            if shift_data[6] == None:
                # shift_data[6][-1] при None нельзя, поэтому last_report_id = 0
                shift_data[6] = [0]
            else: shift_data[6] = shift_data[6].split(';')
            out.append({'id':row[0],
                        'name':row[1],
                        'last_shift_id':shift_data[0],
                        'status':getStatus(shift_data[2],shift_data[4]),
                        'permission_list':row[2],
                        'opened_time':intTimeToStr(shift_data[2])[3:-3],
                        'opened_id':shift_data[3],
                        'closed_time':intTimeToStr(shift_data[4])[3:-3],
                        'closed_id':shift_data[5],
                        'last_report_id':shift_data[6][-1]
                        })
        
        return out


    def get_desks_info(self):
        '''
        метод устарел. что бы не нарушать зависимости, этот метод был оставлен.
        пользуйтесь методом get_desks()
        '''
        utils.log(name, 'dbug','использован устаревший метод db.get_desks_info!')
        result = self.fetchQuery('select id, desk_name, department, permission_list from desks')
        out = {}
        for x in result:
            out[x[0]] = {'name':x[1],
                         'department':x[2],
                         'permission_list':[int(a) for a in x[3].split(';')]}
        return out

    def get_desk_shifts(self, desk_id):
        res = self.fetchQuery('select shift_id,open_time,opened_id,close_time,closed_id,reports_list from shifts where desk_id={0}'.format(desk_id))
        out = []
        for row in res:
            out.append({'shift_id':row[0],
                        'open_time':row[1],
                        'opened_id':row[2],
                        'close_time':row[3],
                        'closed_id':row[4],
                        'reports_list':row[5]
                        })
        return out

##############################################################################################################
#########################################обработка работников#################################################
##############################################################################################################

    def new_employee(self, login, password, department, position, full_name):
        '''
        добавляет нового работника в базу       
        '''
        utils.log(name, 'ntce',str(full_name)+' был добавлен в базу. прикреплен к отделу '+str(department))
        salt = ''.join([random.choice(ascii_letters+digits+'.,;"!@#$%^&*()[]{}?\\|/<>-+_=~') for n in range(12)])
        pwd_with_salt = password+':'+salt
        # проблема с type(hashed) описана в app/usertools.py
        # issues на bitbucket
        hashed = utils.sha3(pwd_with_salt)
        if type(hashed) == bytes:
            hashed = hashed.decode('utf-8')

        self.commitQuery('insert into workers (login, secret_value, password, department_id, position, full_name) values (\'{0}\',\'{1}\',\'{2}\',{3},\'{4}\',\'{5}\')'.format(login, salt,hashed, department, position, full_name))
        employee_id = self.fetchQuery('select last_insert_rowid()')[0][0]
        self.update_cache()
        self.pool.update_data()
        return employee_id





    def rst_pwd_employee(self,user_id, pwd_revoked, new_salt, new_hash):
        '''
        обновляет хэш пароля и соль пользователя
        '''
        if self.checkPassword(user_id,pwd_revoked):
            if re.match('[A-Fa-f0-9]{128}', new_hash):
                self.commitQuery('update workers set secret_value=\'{1}\',password=\'{2}\' where id={0}'.format(user_id,new_salt,new_hash))

            else:
                raise Exception('пароли сохраняются только в sha512 хэше')

        else:
            raise Exception('старый пароль неверен')





    def del_employee(self, worker_id):
        '''
        удаляет работника из базы. возвращается информационное сообщение
        '''
        self.commitQuery('delete from workers where id={0}'.format(worker_id))
        return {'text':'работник удален из базы.','result':'done'}





    def get_employee_id(self, user_login):
        '''возвращает логин работника'''
        try:
            return self.fetchQuery('select id from workers where login=\'{0}\''.format(user_login))[0][0]
        except: 
            raise Exception('пользователь не найден')





    def get_employee_info(self, user_id):
        user_id = int(user_id)
        '''
        возвращает информацию о работнике, например для авторизации
        '''
        result = self.fetchQuery('select login, password, secret_value, department_id, position, full_name from workers where id={0}'.format(user_id))[0]
        out = {'login':result[0],
               'password':result[1],
               'secret_value':result[2],
               'department':result[3],
               'position':result[4],
               'full_name':result[5]}
        try:
            out['desk_id']=self.cache['workers'][user_id]['desk_id']
        except:
            pass
        try:
            out['kitchen_id']=self.cache['workers'][user_id]['kitchen_id']
        except:
            pass

        return out

    

    def get_employees_by_position(self, position):
        '''
        выводит список работников с должностью, указаной в position

        НЕ ГОТОВО:
        с аргументом должности: список ВСЕХ работников
        с аргументом department_id=x: список работников из этого отдела
        с аргументом desk_id=x (только position='waiter'): список работников к с прикрепленным деском desk_id
        '''
        out = {}
        result = self.cache['workers']

        for worker_id in result:
            positions = result[worker_id]['position']
            if position in positions:
                out[worker_id] = result[worker_id]
        if out:
            return out
        else:
            raise Exception('работников с этой должностью не существует')
            


##############################################################################################################
########################################обработка меню и позиций##############################################
##############################################################################################################

    def get_menu(self, department_id, is_kitchen=False):
        '''
        метод устарел. чтобы не нарушать совместимость, к нему добавлен аргумент is_kitchen

        алиас. достает из базы меню одного из отделений(или кухонь), только те позиции, что в наличии
        
        если использовать is_kitchen=True, то отдает меню по кухне, без аргумента -- по отделению 
        ''' 
        utils.log(name, 'dbug','использован устаревший метод db.get_menu!')
        if is_kitchen:
            result = self.fetchQuery('select id,name,amount,menu_group, quantity from menu where kitchen_id={0} and quantity!=0 order by display_priority asc'.format(department_id))
            out = []
            for x in result:
                out.append({'id':x[0],'name':x[1],'amount':x[2],'menu_group':x[3], 'quantity':x[4]})
            return out

        result = self.fetchQuery('select id,name,amount,menu_group, quantity from menu where department_id={0} and quantity!=0 order by display_priority asc'.format(department_id))
        out = []
        for x in result:
            out.append({'id':x[0],'name':x[1],'amount':x[2],'menu_group':x[3], 'quantity':x[4]})
        return out

    def get_position_info(self, position_id):
        '''
        алиас. отдает информацию по позиции в списке
        '''
        x = self.fetchQuery('select name,amount,kitchen_id,quantity,menu_group from menu where id={0}'.format(position_id))[0]
        if not len(x):
            raise Exception('такого id не существует')
        else:
            return {'name':x[0],'amount':x[1],'kitchen':x[2],'quantity':x[3], 'menu_group':x[4]}



    def get_stock(self, department_id):
        '''
        алиас. достает из базы список всех позиций по отделению, с количеством остатка
        '''        
        response = self.fetchQuery('select id,name,amount,quantity from menu where department_id={0}'.format(department_id))
        if department_id == '1': #если service department, тогда выдаем вообще все меню
            response = self.fetchQuery('select id,name,amount,quantity from menu')
        out = []
        if not len(response):
            raise Exception('в отделе нет позиций на продажу')
        
        for x in response:
            out.append({'id':x[0],'name':x[1],'amount':x[2],'quantity':x[3]})
        
        return out

    def get_kitchen_stock(self, kitchen_id):
        '''
        алиас. достает из базы список всех позиций по кухне, с количеством остатка
        '''        
        response = self.fetchQuery('select id,name,amount,quantity from menu where kitchen_id={0}'.format(kitchen_id))
        out = {}
        if not len(response):
            raise Exception('в кухне '+kitchen_id+'нет позиций')
        
        for x in response:
            out[x[0]] = {'name':x[1],'amount':x[2],'quantity':x[3]}
        
        return out


    def add_stock(self, menu_id, add_value):
        '''
        алиас. увеличивает количество остатка menu_id на add_value едениц. работает и с отрицательными числами.
        '''  
        now_value = self.fetchQuery('select quantity from menu where id={0}'.format(menu_id))[0][0]
        if (-int(add_value)) > now_value:
            raise Exception('невозможно уменьшить кол-во позиции: склад '+str(now_value)+'; уменьшение '+str(add_value))
        self.commitQuery('update menu set quantity=quantity+{0} where id={1}'.format(add_value,menu_id))

    def update_stock(self, menu_id, value):
        '''
        алиас. увеличивает количество остатка menu_id на add_value едениц. работает и с отрицательными числами.
        '''  
        self.commitQuery('update menu set quantity={0} where id={1}'.format(value,menu_id))
        utils.log(name, 'dbug','апдейт кэша после обновления склада...')
        self.update_cache()
        self.pool.update_data()
        utils.log(name, 'dbug','обновление завершено.')
        return {'result':'done'}



    def new_position(self, name, amount, kitchen_id, menu_group, priority):
        '''
        добавляет в таблицу меню новую позицию. возвращает id позиции, под которой была создана позиция
        '''
        utils.log(name, 'dbug','новая позиция: кухня '+str(kitchen_id)+', название '+str(name))

        department_id = self.fetchQuery('select department_id from kitchens where kitchen_id={0}'.format(kitchen_id))[0][0]

        self.commitQuery('insert into menu (name, amount, department_id, kitchen_id, menu_group, display_priority) values (\'{0}\',{1},{2},{3},\'{4}\',{5})'.format(name, amount, department_id,kitchen_id, menu_group,priority))
        utils.log(name, 'dbug', 'обновление кэша пула и базы...')
        self.update_cache()
        self.pool.update_data()
        utils.log(name, 'dbug', 'команда на обновление выполнена.')
        return {'text':self.fetchQuery('select last_insert_rowid()')[0][0],'result':'done'}

    def del_position(self, pos_id):
        '''
        изменяет удаляет позицию из базы (TODO:заменять статус позиции на "недействительный")
        '''
        self.commitQuery('delete from menu where id={0}'.format(pos_id))

    def edit_position(self, id, name, amount, menu_group):
        '''
        изменяет информацию о позиции меню.
        '''
        
        self.commitQuery('update menu set name=\'{1}\', amount={2}, menu_group=\'{3}\' where id={0}'.format(id, name, amount,menu_group))

##############################################################################################################
######################################обрабоnка и применение скидок###########################################
##############################################################################################################

    def unrealised_dicount_function(self):
        '''
        задел на будущее. вместо оплаты по факту,
        нужно проверять цену со скидкой, и формировать ее нормально короче.
        это безопасней, все таки.
        '''
        pass

##############################################################################################################
###############################################методы оплаты##################################################
##############################################################################################################

    def get_pay_methods(self):
        out = {}
        response = self.fetchQuery('select id,method_name from pay_methods')
        for x in response:
            out[x[0]] = x[1]
        return out

##############################################################################################################
###################################технические ф-ции для удобства#############################################
##############################################################################################################



    def fetchQuery(self, cmd):
        '''
        абстракция ф-ции execute+fetch из sqlite. 
        планируется оптимизировать функцию для уменьшеня
        нагрузки на файловую систему
        '''
        # метод блокируется, что бы никто не нарушал однопоточность запросами
        self.lock.acquire()

        if self.logging:
            print('command: \033[0;34m'+cmd+'\033[0m')
        self.cursor.execute(cmd)
        out = self.cursor.fetchall()
        if self.logging:
            print('result:  \033[1;34m'+str(out)+'\033[0m')

        self.lock.release()
        return out



    def commitQuery(self, cmd):
        '''
        абстракция ф-ции execute+commit из sqlite. 
        планируется оптимизировать функцию для уменьшеня
        нагрузки на файловую систему
        '''
        # метод блокируется, что бы никто не нарушал однопоточность запросами
        self.lock.acquire()

        if self.logging:
            print('command: \033[0;32m'+cmd+'\033[0m')
        self.cursor.execute(cmd)
        self.conn.commit()

        self.lock.release()
        return None



##############################################################################################################



    def get_menu_names(self, *pargs, strict=False):
        out = []
        for i in pargs:
            try:
                out.append(self.cache['menu'][int(i)]['name'])
            except KeyError:
                if strict:
                    raise Exception('позиция с id #'+str(i)+' не существует')
                else:
                    pass
            except ValueError: 
                raise Exception('невалидный menu_id: '+str(i))

        return out



    def checkPassword(self, user_id, password):
        '''
        проверяет кэш пароля при замене. старый пароль публикуется свободно (он ведь уже изменен)
        '''


        if not user_id or not password:
            return False

        user_info = self.get_employee_info(user_id)

        salt = user_info['secret_value']
        pwd_with_salt = password+':'+salt
        hashed = utils.sha3(pwd_with_salt)

        if user_info['password'] == hashed:
            return True
        else:
            return False

    def check_api_key(self, api_key):
        '''NOT IMPLEMENTED'''
        pass



##############################################################################################################
###########################################################################################памагити###########
##############################################################################################################



def init_database(path):
    # prepare new file
    basedir = os.path.dirname(path)
    if not os.path.exists(basedir):
        os.makedirs(basedir)
        
    open(path, 'a').close()
    # prepare complete, try to connect db

    conn = db.connect(path)
    cursor = conn.cursor()
    cursor.executescript('''
    CREATE TABLE `departments` (
	`department_id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
	`department_name`	TEXT NOT NULL,
	`department_report`	TEXT DEFAULT '',
	`department_color`	TEXT DEFAULT 'primary'
    );
    CREATE TABLE `desks` (
	`id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
	`desk_name`	TEXT NOT NULL UNIQUE,
	`department`	INTEGER NOT NULL,
	`permission_list`	TEXT NOT NULL
    );
    CREATE TABLE `discounts` (
	`id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
	`name`	TEXT NOT NULL UNIQUE,
	`discount_rule`	INTEGER NOT NULL
    );
    CREATE TABLE `invoices` (
	`invoice_id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
	`invoice_name`	TEXT NOT NULL DEFAULT 'без названия',
	`invoice_orders`	TEXT,
	`invoice_amount`	INTEGER NOT NULL DEFAULT 0,
	`created_time`	INTEGER NOT NULL UNIQUE,
	`created_id`	INTEGER NOT NULL,
	`is_payed`	INTEGER NOT NULL DEFAULT 0,
	`payed_time`	INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE `kitchens` (
	`kitchen_id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
	`kitchen_name`	TEXT NOT NULL UNIQUE,
	`department_id`	INTEGER NOT NULL DEFAULT 1
    );
    CREATE TABLE `menu` (
	`id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
	`name`	TEXT NOT NULL,
	`amount`	INTEGER NOT NULL DEFAULT 0,
	`kitchen_id`	INTEGER NOT NULL,
	`department_id`	INTEGER DEFAULT 1,
	`quantity`	INTEGER NOT NULL DEFAULT 0,
	`menu_group`	TEXT NOT NULL DEFAULT 'undefined',
	`display_priority`	INTEGER DEFAULT 1000
    );
    CREATE TABLE `orders` (
	`id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
	`orderlist`	TEXT NOT NULL,
	`amount`	INTEGER NOT NULL,
	`discount`	INTEGER NOT NULL DEFAULT 0,
	`ordertime`	INTEGER NOT NULL,
	`desk_id`	INTEGER NOT NULL,
	`pay_method`	INTEGER NOT NULL DEFAULT 10,
	`created_id`	INTEGER,
	`cook_id`	TEXT,
	`status`	TEXT NOT NULL DEFAULT 'formed',
	`comment`	TEXT NOT NULL DEFAULT 'undefined'
    );
    CREATE TABLE `pay_methods` (
	`id`	INTEGER NOT NULL,
	`method_name`	INTEGER NOT NULL
    );
    CREATE TABLE `reports` (
	`id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
	`report_time`	INTEGER,
	`type`	TEXT NOT NULL,
	`json`	TEXT NOT NULL
    );
    CREATE TABLE `shifts` (
	`shift_id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
	`desk_id`	INTEGER NOT NULL,
	`open_time`	INTEGER NOT NULL UNIQUE,
	`opened_id`	INTEGER NOT NULL,
	`close_time`	INTEGER UNIQUE,
	`closed_id`	INTEGER,
	`reports_list`	TEXT UNIQUE
    );
    CREATE TABLE `workers` (
	`id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
	`login`	TEXT NOT NULL UNIQUE,
	`password`	TEXT NOT NULL UNIQUE,
	`secret_value`	TEXT NOT NULL UNIQUE,
	`department_id`	INTEGER NOT NULL,
	`position`	TEXT NOT NULL,
	`full_name`	TEXT NOT NULL
    );

    INSERT INTO workers
    (id, login, password, secret_value, department_id, position, full_name)
    VALUES
    (1,
     "admin",
     "348a17505f454063fb716e3e40a4dcbaae430c626c9ba402c24c37deabc5281276b31d91034e4bd57a2f5309c508587f5f2d0058d991f4fd5a2d8c2ca805fe97",
     "~=C(;ENgK%FX",
     1,
     "admin;cooker;waiter",
     "Admin Admin"
    );

    INSERT INTO departments
    (department_id, department_name, department_color)
    VALUES
    (1,
     "SERVICE",
     "purple"
    );

    INSERT INTO desks
    (id, desk_name, department, permission_list)
    VALUES
    (1,
     "SERVICE_DESK",
     1,
     "1"
    );

    INSERT INTO kitchens
    (kitchen_id, kitchen_name, department_id)
    VALUES
    (1,
     "SERVICE_KITCHEN",
     1
    );
    INSERT INTO pay_methods
    (id, method_name)
    VALUES
    (10,"наличные"),
    (11,"перевод сбер.онлайн"),
    (12,"за счет пф"),
    (13,"эквайринг карта"),
    (20,"bitcoin"),
    (21,"etherium");
    ''')
    conn.commit()
    conn.close()
    utils.log(name, 'ntce','новая база успешно создана!')