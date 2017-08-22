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
from openerp import http
from openerp.http import request

import logging
_logger = logging.getLogger(__name__)

class Main(http.Controller):

    @http.route(['/resellers'], type='http', auth="public", website=True)
    def reseller(self, **post):
        word = post.get('search', False)
        partners = None
        if not word:
            partners = request.env['res.partner'].sudo().search([('category_id', 'in', request.env.ref('reseller_dermanord.reseller_tag').id)])
        if word and word != '':
            partners = request.env['res.partner'].sudo().search([('name', 'ilike', word), ('category_id', 'in', self.env.ref('reseller_dermanord.reseller_tag').id)])
        return request.website.render('reseller_dermanord.resellers', {'resellers': partners})

    @http.route(['/reseller/<model("res.partner"):partner>'], type='http', auth="public", website=True)
    def reseller_partner(self, partner):
        return request.website.render('reseller_dermanord.reseller', {'reseller': partner})
