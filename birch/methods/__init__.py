#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-
# Part of Birch. See LICENSE file for full copyright and licensing details.

from functools import wraps

from flask_restful import reqparse

from .. import cli
from .. import utils

from ..configurator import configurator
from ..database import VegangaDB

args = cli.args()
cfg = configurator(args.cfg_path)
name = __name__.capitalize()


db = VegangaDB(cfg['MAIN']['db_path'], logging=args.debug)

# когда-нибудь понадобится, хуй с ней.
def api_key_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        parser = reqparse.RequestParser()
        parser.add_argument('key', dest='api_key')
        args = parser.parse_args()
        if not args['api_key']:
            return {'ok':0,'msg':'API key is required'}, 403
        try:
            db.check_api_key(**args)
        except Exception as e:
            return {'ok':0,'msg':str(e)}, 403
        return f(*args, **kwargs)
    return decorated


# now importing....

from . import info
from . import invoices
from . import orders
from . import positions
from . import reports
from . import users
from . import utilities