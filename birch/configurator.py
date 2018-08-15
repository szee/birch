#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-
# Part of Birch. See LICENSE file for full copyright and licensing details.

'''
configurator.py предназначен для снятия кодовой нагрузки на сервисы XELAJ.

'''

from configparser import ConfigParser as cp
import os
import sys

class configurator:
    def __init__(self,path):
        self.d = cp()
        self.d.read(path)
        if not self.d.sections():
            raise Exception('path is not cfg file')

    def keys(self):
        return self.d.keys()
    
    def __getitem__(self, item):
        return self.d[item]