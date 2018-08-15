#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-
# Part of Birch. See LICENSE file for full copyright and licensing details.

from flask_restful import Resource, reqparse

from . import db


class PayInvoice(Resource):
    path = '/pay_invoice'
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('id', dest='invoice_id')
        args = parser.parse_args()
        try:
            return {'ok':1,'msg':db.pay_invoice(**args)}, 204
        except Exception as e:
            return {'ok':0,'msg':str(e)}, 500


class GetInvoices(Resource):
    path = '/invoices'
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('order_list', dest='full_order_list')
        parser.add_argument('as_name', dest='by_name')
        args = parser.parse_args()

        allowed_values = ['', None]
        if (args['full_order_list'] not in allowed_values or 
            args['by_name'] not in allowed_values):
            return {'ok':0,'msg':'order_list/as_name без значения'}, 400

        if args['full_order_list'] is None:
            args['full_order_list'] = False
        else:       
            args['full_order_list'] = True
        
        if args['by_name'] is None:
            args['by_name'] = False
        else:    
            args['by_name'] = True
        
        try:
            return {'ok':1,'msg':db.get_invoices(**args)}
        except Exception as e:
            return {'ok':0,'msg':str(e)}, 500

class GetInvoiceInfo(Resource):
    path = '/invoice_info'
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('id', dest='invoice_id')
        parser.add_argument('order_list', dest='full_order_list')
        parser.add_argument('as_name', dest='by_name')
        args = parser.parse_args()

        allowed_values = ['', None]
        if (args['full_order_list'] not in allowed_values or 
            args['by_name'] not in allowed_values):
            return {'ok':0,'msg':'order_list/as_name без значения'}, 400

        try:
            args['invoice_id'] = int(args['invoice_id'])
        except:
            return {'ok':0,'msg':'id только число'}, 400
        
        if args['full_order_list'] is None:
            args['full_order_list'] = False
        else:       
            args['full_order_list'] = True
        
        if args['by_name'] is None:
            args['by_name'] = False
        else:    
            args['by_name'] = True

        try:
            return {'ok':1,'msg':db.get_invoice_info(**args)} 
        except Exception as e:
            return {'ok':0,'msg':str(e)}, 500