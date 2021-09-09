# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution, third party addon
#    Copyright (C) 2004-2021 Vertel AB (<http://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging

from odoo import fields, http, SUPERUSER_ID, tools, _
from odoo.addons.website_sale.controllers.main import WebsiteSale, TableCompute
from odoo.http import request
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.website.controllers.main import QueryURL
from werkzeug.exceptions import Forbidden, NotFound

_logger = logging.getLogger(__name__)

class WebsiteSale(http.Controller):
    # --------------------------------------------------------------------------
    # Accessory Products
    # --------------------------------------------------------------------------
    @http.route('/shop/products/variant_accessories', type='json', auth='public', website=True)
    def variant_accessories(self, variant_id, **kwargs):
        return self._get_variant_accessories(variant_id)

    def _get_variant_accessories(self, variant_id):
        """
        Returns list of accesories for the specific variant
        """
        _logger.warning("Hello from start of _get_variant_accessories")
        max_number_of_product_for_carousel = 4
        visitor = request.env['website.visitor']._get_visitor_from_request()
        _logger.warning("Hello from end of _get_variant_accessories")
        return {}