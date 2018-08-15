#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-
# Part of Birch. See LICENSE file for full copyright and licensing details.

from flask_restful import Resource, reqparse

from . import db

from .. import cli
from .. import utils
from ..configurator import configurator

args = cli.args()
cfg = configurator(args.cfg_path)
name = __name__.capitalize()

class CreateOrder(Resource):
    path = '/create_order'
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('waiter_id')
        parser.add_argument('orderlist')
        parser.add_argument('amount')
        parser.add_argument('pay_method')
        parser.add_argument('comment')
        parser.add_argument('invoice')
        args = parser.parse_args()

        #здесь фиксим ошибки заполнения формы
        if not args['comment'] or args['comment'] == 'undefined':
            args['comment'] = 'нет комментария'

        if not args['pay_method'] or args['pay_method'] == 'undefined':
            args['pay_method'] = cfg['MAIN']['default_pay_method']

        if not args['invoice']:
            args['invoice'] = False

        if ';;' in args['orderlist']:
            args['orderlist'].replace(';;',';')

        if args['orderlist'][-1] == ';':
            args['orderlist'] =  args['orderlist'][:-1]

        args['orderlist'] = args['orderlist'].split(';')

        try:
            return {'ok':1,'msg':db.pool.new_order(**args)}, 204
        except Exception as e:
            return {'ok':0,'msg':str(e)}, 500


class GetDeskOrders(Resource):
    path = '/desk_orders'
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('id', dest='desk_id')
        args = parser.parse_args()
        try:
            return {'ok':1,'msg':db.pool.get_orders(**args)}
        except Exception as e:
            return {'ok':0,'msg':str(e)}, 500


class GetKitchenOrders(Resource):
    path = '/kitchen_orders'
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('id', dest='kitchen_id')
        args = parser.parse_args()
        try:
            return {'ok':1,'msg':db.pool.get_orders(**args)}
        except Exception as e:
            return {'ok':0,'msg':str(e)}, 500


class UpdateOrderStatus(Resource):
    path = '/update_order_status'
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('status')
        parser.add_argument('order_id')
        parser.add_argument('worker_id')
        args = parser.parse_args()
        try:
            if args['status'] == 'cooked':
                return {'ok':1,'msg':db.pool.cook(**args)}, 204

            elif args['status'] == 'gaved':
                return {'ok':1,'msg':db.pool.gave_out(**args)}, 204

            else:
                return {'ok':0,'msg':'аргумент status может быть только cooked или gaved'}, 400

        except Exception as e:
            return {'ok':0,'msg':str(e)}, 500