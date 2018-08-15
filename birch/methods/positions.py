#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-
# Part of Birch. See LICENSE file for full copyright and licensing details.

from flask_restful import Resource, reqparse

from . import db


class AddPosition(Resource):
    path = '/new_position' 
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('kitchen_id')
        parser.add_argument('name')
        parser.add_argument('amount')
        parser.add_argument('group', dest='menu_group')
        parser.add_argument('priority')
        args = parser.parse_args()
        try:
            return {'ok':1,'msg':db.new_position(**args)}
        except Exception as e:
            return {'ok':0,'msg':str(e)}, 500


class DelPosition(Resource):
    path = '/del_position' 
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('id', dest='pos_id')
        args = parser.parse_args()
        try:
            return {'ok':1,'msg':db.del_position(**args)}, 204
        except Exception as e:
            return {'ok':0,'msg':str(e)}, 500


class UpdateStock(Resource): 
    path = '/update_stock'
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('id', dest='menu_id')
        parser.add_argument('value')
        args = parser.parse_args()
        try:
            return {'ok':1,'msg':db.update_stock(**args)}, 202
        except Exception as e:
            return {'ok':0,'msg':str(e)}, 500