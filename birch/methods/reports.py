#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-
# Part of Birch. See LICENSE file for full copyright and licensing details.

from flask_restful import Resource, reqparse

from . import db


class MakeXReport(Resource):
    path = '/make_x_report'
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('desk_id')
        args = parser.parse_args()
        try:
            return {'ok':1,'msg':db.make_x_report(**args)}
        except Exception as e:
            return {'ok':0,'msg':str(e)}, 500

class MakeKitchenReport(Resource):
    path = '/make_kitchen_report'
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('id', dest='kitchen_id')
        parser.add_argument('start', dest='start_time')
        parser.add_argument('end', dest='end_time')
        args = parser.parse_args()

        if args['end'] is None:
            args['end'] = 'now'
        
        try:
            return {'ok':1,'msg':db.make_kitchen_report(**args)}
        except Exception as e:
            return {'ok':0,'msg':str(e)}, 500

class GetReport(Resource):
    path = '/report'
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('id', dest='report_id')
        args = parser.parse_args()
        try:
            return {'ok':1,'msg':db.get_report(**args)}
        except Exception as e:
            return {'ok':0,'msg':str(e)}, 500

class GetLastReports(Resource):
    path = '/last_reports'
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('by_desk')
        parser.add_argument('by_shift')
        parser.add_argument('by_department')
        parser.add_argument('id')# в данном случае при взаимодействии с апи, указывается например ?by_desk&id=blahblah
        parser.add_argument('start_time')# только vegangaDB TIME (необязателен) 
        args = parser.parse_args()


        # TODO: отрефакторить этот пиздец. можно сделать и лучше
        if args['start_time'] is None:
                args['start_time'] = 0
        
        try:   
            if args['by_desk'] is not None:
                res = db.get_desk_reports(args['start_time'],args['id'], str_time=False, full_name=False)
            elif args['by_shift'] is not None:
                return {'ok':0,'msg':'not implemented yet'}, 501
            elif args['by_department'] is not None:
                res = db.get_department_reports(args['start_time'],args['id'], str_time=False)
            else:
                return {'ok':0,'msg':'невалидный тип сортировки (by_desk,by_shift,by_department)'}, 400

            return {'ok':1,'msg':res}
        except Exception as e:
            return {'ok':0,'msg':str(e)}, 500

class CloseShift(Resource):
    path = '/close_shift'
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('desk_id')
        parser.add_argument('closed_id')
        args = parser.parse_args()
        try:
            return {'ok':1,'msg':db.close_shift(**args)}
        except Exception as e:
            return {'ok':0,'msg':str(e)}, 500