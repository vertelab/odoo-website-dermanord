# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2004-2017 Vertel AB (<http://vertel.se>).
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

from openerp import models, fields, api, http, _
from openerp import http
from openerp.http import request
import logging
_logger = logging.getLogger(__name__)

class SalePromotions(models.Model):
    _name = 'sale.promotion'
    _order = 'sequence, name, id'
    
    @api.model
    def _default_sequence(self):
        last = self.search([], order='sequence desc', limit=1)
        if not last:
            return 1
        return last.sequence + 1
    
    name = fields.Char(string="Name", required=True)
    description = fields.Text(string="Description")
    image = fields.Binary(string='Image', required=True)
    url = fields.Char(string='URL', required=True)
    sequence = fields.Integer(string='Sequence', required=True, default=_default_sequence)
    website_published = fields.Boolean(string='Published')


class SalePromotions(http.Controller):
    @http.route(['/get_sale_promotion'], type='json', auth='public', website=True)
    def get_sale_promotion(self, sp_id=None, **kw):
        sp = request.env['sale.promotion'].browse(int(sp_id))
        sale_promotion = {}
        sale_promotion['name'] = sp.name
        sale_promotion['description'] = sp.description
        sale_promotion['image'] = '/imagefield/sale.promotion/image/%s/ref/' %sp.id
        sale_promotion['url'] = sp.url
        return sale_promotion
