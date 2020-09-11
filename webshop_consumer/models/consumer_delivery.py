# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2017- Vertel AB (<http://vertel.se>).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api, _
from openerp.exceptions import Warning
from openerp.tools import safe_eval
import openerp.addons.decimal_precision as dp
import requests
from requests.auth import HTTPBasicAuth
import json
import base64
from urllib import urlencode
import traceback


class delivery_carrier(models.Model):
    _inherit = "delivery.carrier"
    
    is_consumer_delivery = fields.Boolean('Consumer Delivery')

class stock_picking(models.Model):
    _inherit = 'stock.picking'
    
    is_consumer_delivery = fields.Boolean(related='carrier_id.is_consumer_delivery')
    

