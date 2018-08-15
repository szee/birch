#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Part of Birch. See LICENSE file for full copyright and licensing details.

from flask import Flask
from flask_restful import Api

from . import cli
from . import utils
from . import methods

from .configurator import configurator

args = cli.args()
cfg = configurator(args.cfg_path)
name = __name__.capitalize()

app = Flask(cfg['MAIN']['name'])
api = Api(app)

@app.after_request
def apply_caching(response):
    response.headers['server'] = cfg['MAIN']['name']
    return response


def new_resource(method):
    api.add_resource(method,method.path)


# TODO: сделать цикл с импортом. в будущем все методы можно будет импортировать как плагины
new_resource(methods.info.GetDepartments)
new_resource(methods.info.GetDesks)
new_resource(methods.info.GetDesksInfoExtended)
new_resource(methods.info.GetKitchenInfo)
new_resource(methods.info.GetMenu)
new_resource(methods.info.GetPayMethods)
new_resource(methods.info.GetPositionInfo)
new_resource(methods.info.GetStockInfo)

new_resource(methods.invoices.GetInvoiceInfo)
new_resource(methods.invoices.GetInvoices)
new_resource(methods.invoices.PayInvoice)

new_resource(methods.orders.CreateOrder)
new_resource(methods.orders.GetDeskOrders)
new_resource(methods.orders.GetKitchenOrders)
new_resource(methods.orders.UpdateOrderStatus)

new_resource(methods.positions.AddPosition)
new_resource(methods.positions.DelPosition)
new_resource(methods.positions.UpdateStock)

new_resource(methods.reports.CloseShift)
new_resource(methods.reports.GetLastReports)
new_resource(methods.reports.GetReport)
new_resource(methods.reports.MakeKitchenReport)
new_resource(methods.reports.MakeXReport)

new_resource(methods.users.CreateNewUser)
new_resource(methods.users.GetUserId)
new_resource(methods.users.GetUserInfo)
new_resource(methods.users.UpdateUserPwd)

new_resource(methods.utilities.GetApiVersion)
new_resource(methods.utilities.Ping)