#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-
# Part of Birch. See LICENSE file for full copyright and licensing details.

import argparse
import os
import sys

# if pytest
if sys.argv[0] == '/usr/local/bin/pytest':
    sys.argv = ['birch', '-c', './config.ini']

parser = argparse.ArgumentParser(
                  description='Birch is a simple ERP system for tiny buisness')

parser.add_argument('-c', '--config', type=str,
                    dest='cfg_path',
                    metavar='PATH', default='/etc/Birch/config.ini',
                    help='path to config file')

parser.add_argument('--no-logo', action='store_true',
                    dest='hide_logo',
                    help='hiding XELAJ logo')
                    
parser.add_argument('-d', '--debug', action='store_true',
                    dest='debug',
                    help='print debug messages')


a = parser.parse_args()

a.cfg_path = os.path.realpath(a.cfg_path)
if not os.path.exists(a.cfg_path):
    print(a.cfg_path+' is not exist. Aborting.')
    sys.exit(1)

def args():
    return a