    #!/usr/bin/env python3.6
# -*- coding: utf-8 -*-
# Part of Birch. See LICENSE file for full copyright and licensing details.

from flask_restful import Resource, reqparse

from . import db

class GetApiVersion(Resource):
    path = '/api_version'
    def get(self):
        return {'ok':1,'msg':'v2.0'}
        

class Ping(Resource):
    path = '/ping'
    def get(self):
        return {'ok':1,'msg':'pong'}, 418