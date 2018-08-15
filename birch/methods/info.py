#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-
# Part of Birch. See LICENSE file for full copyright and licensing details.

from flask_restful import Resource, reqparse

from . import db


class GetDepartments(Resource):
    path = '/departments'
    def get(self):
        try:
            return {'ok':1,'msg':db.get_departments_extended()}
        except Exception as e:
            return {'ok':0,'msg':str(e)}, 500


class GetDesks(Resource):
    path = '/desks'
    def get(self):
        try:
            return {'ok':1,'msg':db.get_desks()}
        except Exception as e:
            return {'ok':0,'msg':str(e)}, 500


class GetMenu(Resource):
    path = '/menu'
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('department_id')
        args = parser.parse_args()
        try:
            return {'ok':1,'msg':db.get_menu(**args)}
        except Exception as e:
            return {'ok':0,'msg':str(e)}, 500


class GetDesksInfoExtended(Resource):
    path = '/desks_info_x'
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('department_id')
        args = parser.parse_args()
        try:
            return {'ok':1,'msg':db.get_desks_extended(**args)}
        except Exception as e:
            return {'ok':0,'msg':str(e)}, 500


class GetPositionInfo(Resource):
    path = '/position_info'
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('id', dest='position_id')
        args = parser.parse_args()
        try:
            return {'ok':1,'msg':db.get_position_info(**args)}
        except Exception as e:
            return {'ok':0,'msg':str(e)}, 500


class GetPayMethods(Resource):
    path = '/pay_methods'
    def get(self):
        try:
            return {'ok':1,'msg':db.get_pay_methods()}
        except Exception as e:
            return {'ok':0,'msg':str(e)}, 500


class GetStockInfo(Resource):
    path = '/stock_info' 
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('department_id')
        args = parser.parse_args()
        try:
            return {'ok':1,'msg':db.get_stock(**args)}
        except Exception as e:
            return {'ok':0,'msg':str(e)}, 500

class GetKitchenInfo(Resource):
    path = '/kitchen_info'
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('id', dest='kitchen_id')
        args = parser.parse_args()
        try:
            return {'ok':1,'msg':db.get_kitchen_info(**args)}
        except Exception as e:
            return {'ok':0,'msg':str(e)}, 500