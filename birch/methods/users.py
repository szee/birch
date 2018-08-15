#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-
# Part of Birch. See LICENSE file for full copyright and licensing details.

from flask_restful import Resource, reqparse

from . import db


class GetUserInfo(Resource):
    path = '/user_info'
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('user_id')
        args = parser.parse_args()
        try:
            return {'ok':1,'msg':db.get_employee_info(**args)}
        except Exception as e:
            return {'ok':0,'msg':str(e)}, 500


class GetUserId(Resource):
    path = '/user_id'
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('user_login')
        args = parser.parse_args()
        try:
            return {'ok':1,'msg':db.get_employee_id(**args)}
        except Exception as e:
            return {'ok':0,'msg':str(e)}, 500


class UpdateUserPwd(Resource):
    path = '/update_user_password'
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('user_id')
        parser.add_argument('pwd_revoked')
        parser.add_argument('new_salt')
        parser.add_argument('new_hash')
        args = parser.parse_args()
        try:
            return {'ok':1,'msg':db.rst_pwd_employee(**args)}, 204
        except Exception as e:
            return {'ok':0,'msg':str(e)}, 500

class CreateNewUser(Resource):
    path = '/new_user'
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('login')
        parser.add_argument('password')
        parser.add_argument('department')
        parser.add_argument('position')
        parser.add_argument('full_name')
        args = parser.parse_args()
        try:
            return {'ok':1,'msg':db.new_employee(**args)}
        except Exception as e:
            return {'ok':0,'msg':str(e)}, 500