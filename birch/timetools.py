#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-
# Part of Birch. See LICENSE file for full copyright and licensing details.

'''
timetools.py -- модуль для работы со временем и преобразованием его для бд
'''

import datetime
import time
import re

OVERDUE_STATUS_MAX_HOURS = 9

def nowTime():
    '''
    возвращает unix time (str)
    '''
    return str(int(time.time()))


def strTimeToInt(text):
    '''
    делает из строки int
    '''
    out = 0
    try:
        out = int(text)
    except:
        pass
    return out


def intTimeToStr(value):
    '''
    делает из int строку
    '''
    out = '0'
    try:
        out = str(value)
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
        # проверяем день
        if (int(time.strftime('%d', time.localtime(start_time))) <
                int(time.strftime('%d', time.localtime())) - 1):
            return 'overdue'
        else:
            return 'open'
    # str(end_time).isdigit() проверяется, число ли это вообще.
    # через try: int() не получится, потому что end_time может быть None
    elif str(end_time).isdigit():
        # Надо сравнивать время дня (типа часы работы)
        if (int(time.strftime('%H', time.localtime(end_time))) < OVERDUE_STATUS_MAX_HOURS):
            return 'closed'
        else:
            return 'with_report'
    else:
        raise Exception('время закрытия не None и не число')
