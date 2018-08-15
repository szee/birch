#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-

import hashlib
import os

import requests

from . import cli
from .configurator import configurator

args = cli.args()
cfg = configurator(args.cfg_path)



def show_logo(name):
    print('\033c')
    print('    _/      _/  _/_/_/_/  _/          _/_/          _/\n'+
          '     _/  _/    _/        _/        _/    _/        _/\n'+
          '      _/      _/_/_/    _/        _/_/_/_/        _/\n'+
          '   _/  _/    _/        _/        _/    _/  _/    _/\n'+
          '_/      _/  _/_/_/_/  _/_/_/_/  _/    _/    _/_/\n'+
          name)



def log(author, ltype, text):
    try:
        requests.get(cfg['LOGGER']['host']+'/?a='+author+'&t='+ltype+'&l='+text)
    except Exception as e:
        if cfg['LOGGER'].getboolean('lazy'):
            pass
        else:
            print('\033[91;7mtryed send log message. Exception: '+str(e)+'\033[0m')

def sha3(text):
    s = hashlib.sha3_512()
    s.update(text.decode('utf-8'))
    return s.hexdigest()

def backupDB(master_key):
    '''
    !!!IMPORTANT!!!
    такой способ не является особо безопасным
    '''