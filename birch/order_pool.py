#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-
# Part of Birch. See LICENSE file for full copyright and licensing details.

'''
!!!ДЛЯ МЕЙНТЕЙНЕРОВ: пожалуста, не пугайтесь, что тут так много дерьма. код был написан за ночь из-за дедлайна.
все будет переписано начисто


архитектура была придумана буквально в амфетаминовом угаре, так что большинство покажется здесь пиздец сложным и
и не понятным, но ты справишься, анон

order_pool.py предназначен для разделения заказов по кухням и дескам с которых были подтверждены заказы

каждый заказ -- объект обладающий следующими свойствами:
*время заказа
*списка позицицй
*кто и на каком деске принял
*кто приготовил (массив из айдишников)
*тип оплаты
*стоимость
*наличие и сумма скидки
*статус

существует три группы массивов с инфой о заказах:
дески (n-ное кол-во)
кухня (n-ное кол-во)
пул готовящихся заказов (только один)

в десках хранится информация о принятых и НЕ ВЫДАНЫХ заказах (выданые сразу летят в бд, без вариантов)
в кухнях зранится РАЗДЕЛЕННАЯ информация о принятых и НЕ СОБРАНЫХ заказах (собраные уходят в пул)
в пуле хранится статус заказа ПО КАЖДОМУ ЗАКАЗУ НЕ ВЫДАНОМУ(кто принял, где, готово ли по каждой кухне или нет)


при принятии заказа, информация о нем уходит в 1)базу 2)массив деска 3)пул заказов
после того как информация о заказе разошлась по трем местам, заказ берется из ОБЪЕКТА В ДЕСКЕ и разделяется по кухням
в пул уходит дополнение к инфе, какие кухни должны приготовить, и к каждой кухне добавляется новый объект заказа
'''

import copy
import os
import requests

from . import database
from . import utils
from .timetools import nowTime, strTimeToInt, intTimeToStr

name = __name__.capitalize()

class order_pool():
    '''
    order_pool -- надстройка над VegangaDB. более нигде не используется.
    order_pool хранит в себе невыданные заказы разделяя информацию о заказах по дескам и по кухням.

    напрямую взаимодействовать с объектами данного класса, кроме как с его методами не рекомендуется
    серьезно, не надо.
    '''

    def __init__(self, db):
        self.db = db
        self.update_data() #инициализируемся при создании

    def update_data(self):
        self.pool = {}#сам пул заказов НЕ ВЫДАНЫХ. выданые здесь находиться могут но они удаляются
        self.desks = {}#взять из базы список десков
        for x in self.db.get_desks():
            self.desks[x['id']] = {}
        self.kitchens = {}#взять из базы список кухонь
        for x in self.db.get_kitchens():
            self.kitchens[x['id']] = {}
        self.menu = {}#по id кухонь взять позиции каждого
        for x in self.db.get_departments_extended():
            self.menu[x['id']] = []
            for y in self.db.get_menu(x['id'], is_kitchen=True):
                self.menu[x['id']].append(y['id'])

        self.waiters = self.db.get_employees_by_position('waiter') #взять из базы, к какому деску принадлежит вэйтер
        self.cookers = self.db.get_employees_by_position('cooker') #взять из базы, к какой кухне принадлежит повар
        utils.log(name, 'dbug','кэш пула обновлен. menu='+str(self.menu))
        # TODO: update_data конфликтует с db.update_cache().
        #       я без понятия почему, но надо исправлять.
        #       посмотрим как себя поведет.
        return None



    def new_order(self, waiter_id, orderlist, amount, pay_method, comment, invoice=False):
        '''
        добавляет в пул новый заказ.
        invoice=False описан в db.new_order_extended
        '''
        order_id = self.db.new_order_extended(waiter_id, orderlist, amount, pay_method, comment, invoice=invoice)['order_id']
        if waiter_id not in self.waiters:
            raise ValueError('пользователь не найден')

        if not orderlist:
            raise ValueError('список заказа пустой')

        desk_id = self.waiters[waiter_id]['desk_id']
        template = {
                    'created_id':waiter_id,
                    'create_time':strTimeToInt(nowTime()),
                    'comment':comment,
                    'desk_id':desk_id,
                    'orderlist':orderlist,
                    'kitchens':{}, #потом будем добавлять сюда рассортированые позиции
                    'status':'formed',
                    'gave_id':None,
                    'cooked_time':None
                   }

        for position in orderlist: #проходимся по всему списку позиций в заказе
            for x in self.menu.keys(): # x -- id кухни
                if position in self.menu[x]:
                    if not x in template['kitchens']:
                        template['kitchens'][x]={
                                                 'cooker':None,
                                                 'orderlist':[position]
                                                 }
                    else:
                        template['kitchens'][x]['orderlist'].append(position)

        if not template['kitchens']:
            raise ValueError('ни одна кухня не учавствует в сборе заказа. перепроверьте данные')

        self.pool[order_id] = copy.deepcopy(template)

        for kitchen_id in template['kitchens']:
            self.kitchens[kitchen_id][order_id] = template['kitchens'][kitchen_id]
            self.kitchens[kitchen_id][order_id].update({'created_id':template['created_id'],
                                                        'created_name':self.db.get_employee_info(template['created_id'])['full_name'],
                                                        'create_time':template['create_time'],
                                                        'comment':template['comment'],
                                                        'desk_id':template['desk_id']})

            self.kitchens[kitchen_id][order_id]['orderlist'] = list(map(lambda x: self.db.get_position_info(x)['name'], self.kitchens[kitchen_id][order_id]['orderlist']))
        
        template.pop('desk_id', None)
        template.pop('kitchens', None) #больше это нам не понадобится, убираем сразу с глаз долой
                                       #тем более по факту в desk_id пихается та же самая инфа, только без template['kitchens']  
        self.desks[desk_id][order_id] = template



    def cook(self, order_id, worker_id):
        order_id = int(order_id)
        worker_id = int(worker_id)
        if 'kitchen_id' not in self.cookers[worker_id]:
            raise Exception('worker_id не прикреплен к кухне')

        kitchen_id = self.cookers[worker_id]['kitchen_id']
        try:
            self.pool[order_id]['kitchens'][kitchen_id]['cooker'] = worker_id
        except KeyError:
            raise Exception('заказ с таким id не был выдан кухне повара')
        # стремная еботня, но короче пихаем id повара в его кухню при заказе, а если повар решил скипнуть заказ
        # не из своей кухни, то он оподливился и происходит вывод исключения

        if order_id not in self.kitchens[kitchen_id]:
            raise Exception('заказ уже собран кухней')

        self.kitchens[kitchen_id].pop(order_id, None)
        self.pool[order_id]['kitchens'][kitchen_id]['cooker']=worker_id

        # в цикле мы смотрим, есть ли хоть одна кухня с cooker == None
        # если бы мы поставили is_assembled = False, код бы увеличился
        is_assembled = True
        #kitchen_id нам не потребуется, заюзаем его здесь
        for kitchen_id in self.pool[order_id]['kitchens']:
            if self.pool[order_id]['kitchens'][kitchen_id]['cooker'] == None:
                is_assembled = False
                break

        if is_assembled:
            self.pool[order_id]['status'] = 'cooked'
            self.pool[order_id]['cooked_time'] = strTimeToInt(nowTime())
            desk_id = self.pool[order_id]['desk_id']
            self.desks[desk_id][order_id]['status'] = 'cooked'

        self.db.cook_order(order_id, worker_id, assembled=is_assembled)



    def gave_out(self, order_id, waiter_id):
        order_id = int(order_id)
        waiter_id = int(waiter_id)
        if self.pool[order_id]['status'] != 'cooked':
            raise Exception('заказ еще не приготовлен полностью')

        if 'desk_id' not in self.waiters[waiter_id]:
            raise Exception('waiter_id не прикреплен к деску')

        desk_id = self.waiters[waiter_id]['desk_id']
        self.desks[desk_id].pop(order_id, None)
        self.db.done_order(order_id)
        del self.pool[order_id]
        


    def get_orders(self, kitchen_id=None ,desk_id=None):
        if kitchen_id and desk_id:
            raise Exception('нельзя вернуть заказы одновременно с деска и кухни')
        elif kitchen_id != None:
            return self.kitchens[int(kitchen_id)]
        elif desk_id != None:
            return self.desks[int(desk_id)]


#####################################################
# pool[order_id] = {
#                   'created_id':16,
#                   'create_time':180101214534 #время как в бд
#                   'comment':'sometext',
#                   'desk_id':2,
#                   'orderlist':[1,4,6],
#                   'kitchens':{
#                               'id1':{
#                                      'cooker':None,    # здесь если None то заказ на этой кухне не собран вообще
#                                      'orderlist':[1]   # здесь список из pool[n]['orderlist'] но отфильтрованый по позициям кухни
#                                     }, 
#                               'id2':{
#                                      'cooker':18,    # здесь если число, то заказ с этой кухни УЖЕ собран, 18-м айдишником, из kitchens заказ пропадает 
#                                      'orderlist':[4,6] # здесь список из pool[n]['orderlist'] но отфильтрованый по позициям кухни
#                                     }
#                              },
#                   'status':'cooked', #тут либо formed либо cooked потому что done улетает отсюда сразу в базу.
#                                      #cooked только если во всех (x in kitchens:x['cooker']!=None)
#                                      #он МОЖЕТ быть изменен на done но если в пуле будет замечена такая запись, она будет отпрравлена в базу заказов и удалена из пула
#                   'gave_id':16, #если status != cooked or done, тогда может быть None
#                   'cooked_time':180101214820 #время как в бд.может быть нулевое если status=formed 
#                  }
#
#desk['id1'][order_id] = {
#                         'created_id':16,
#                         'create_time':180101214534 #время как в бд
#                         'comment':'sometext',
#                         'orderlist':[1,4,6] #orderlist здесь полный в отличии от kitchen['someid']['orderlist']
#                         'status':formed, #а может быть и cooked если приготовилось целиком.
#                         'gave_id' 16 #если не cooked и не done, тогда может быть None
#                         'cooked_time':180101214820 #время как в бд.может быть нулевое если status=formed 
#                        }
#
#kitchen['id8'][order_id] = {
#                            'created_id':16,
#                            'create_time':180101214534 #время как в бд
#                            'comment':'sometext',
#                            'desk_id':2,
#                            'orderlist':[1] #здесь только те заказы, что может приготовить эта кухня 
#                                            #берется из pool[order_id]['kitchens']['kitchen_id']['orderlist']
#                           }
#
#waiters['this_id'] = {
#                      'desk_id':1 #если вэйтер добавил заказ, то id деска берется из его массива
#                      # потом может дополню чем-нибудь, пока без надобности
#                     }
#cookers['this_id'] = {
#                      'kitchen_id':2 #если повар сбросил заказ номер Х, то в заказе Х к кухне kitchen_id добавляется id приготовившего this_id
#                      # потом может дополню чем-нибудь, пока без надобности
#                     }
#
#menu['kitchen_id'] = [1,2,3,4,5] #menu -- словарь, menu[n] -- массив позиций, который он может приготовить
#
#
#методы:
#   new_order(data)
#   worker_id_cook_this_part_of_order(order_id, worker_id)
#   waiter_id_gave_out_this_order(order_id, waiter_id)
#   see_undone_by_desk(desk_id)
#   see_uncooked_by_kitchen(kitchen_id)
#   не знаю что еще давай это сделаем пока