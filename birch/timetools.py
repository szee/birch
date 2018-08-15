#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-
# Part of Birch. See LICENSE file for full copyright and licensing details.

'''
timetools.py -- модуль для работы со временем и преобразованием его для бд
'''

import datetime
import re

OVERDUE_STATUS_MAX_HOURS = 9

def nowTime():
    '''
    возвращает настоящее время "YY-MM-DD hh:mm:ss"
    '''
    return str(datetime.datetime.now().replace(microsecond=0))[2:]


def strTimeToInt(text):
    '''
    'YY-MM-DD hh:mm:ss'(str) -> YYMMDDhhmmss(int)
    '''
    out = 0
    try:   
        out = int(text.replace('-','').replace(' ','').replace(':', ''))
    except:
        pass
    return out


def intTimeToStr(value):
    '''
    YYMMDDhhmmss(int) -> 'YY-MM-DD hh:mm:ss'(str)
    '''
    out = '00-00-00 00:00:00'  
    try:
        s = str(value)
        x = [s[i:i + 2] for i in range(0, len(s), 2)]
        out = x[0]+'-'+x[1]+'-'+x[2]+' '+x[3]+':'+x[4]+':'+x[5]
    except:
        pass

    return out


def getStatus(start_time, end_time):
    '''
    специальная функция, определяет статус деска на основе времени
    статусы и их определения описаны в desks.md
    '''
    try:
        start_time = int(start_time)    
    except:
        raise Exception('время только в INT формате')

    if start_time == 0:
        return 'created'

    if end_time is None:
        # сравнение часов
        # а потом дня
        if (start_time // 1000000 % 100 < strTimeToInt(nowTime()) // 1000000 % 100 - 1):
            return 'overdue'
        else:
            return 'open'
    # str(end_time).isdigit() проверяется, число ли это вообще.
    # через try: int() не получится, потому что end_time может быть None
    elif str(end_time).isdigit():
        if (end_time // 10000 % 100) < OVERDUE_STATUS_MAX_HOURS:
            return 'closed'
        else:
            return 'with_report'
    else:
        raise Exception('время закрытия не None и не число')