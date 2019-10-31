# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2004-2018 Vertel AB (<http://vertel.se>).
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
from datetime import datetime, date, timedelta
from openerp.addons.website_memcached import memcached
import base64
import werkzeug
from openerp.addons.website.models.website import slug 

from openerp import http
from openerp.http import request

from timeit import default_timer as timer
import sys, traceback
import json

import logging
_logger = logging.getLogger(__name__)

from openerp.tools.translate import GettextAlias
from openerp import SUPERUSER_ID
import inspect
import openerp


# ~ class product_template(models.Model):
    # ~ _inherit = 'product.template'

    # ~ @api.model
    # ~ def get_stock_info(self, product_id, location_ids=None):
        # ~ product = self.env['product.product'].sudo().search_read([('id', '=', product_id)], ['virtual_available_days', 'type', 'force_out_of_stock', 'is_offer'])
        # ~ product = self.env['product.product'].sudo().with_context({'location_ids':location_ids }).search_read([('id', '=', product_id)], ['virtual_available_days', 'type', 'inventory_availability', 'is_offer'])

            # ~ locations = self.env.ref('stock.picking_type_out').default_location_dest_id
            # ~ locations |= self.env.ref('point_of_sale.picking_type_posout').default_location_dest_id
            # ~ locations |= self.env.ref('stock.location_production')
            # ~ 1. external id för nytt lager.
            # ~ 2. hitta plats att skapa location_ids.
