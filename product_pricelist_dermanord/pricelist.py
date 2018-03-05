# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2018- Vertel AB (<http://vertel.se>).
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
import logging
_logger = logging.getLogger(__name__)


class product_pricelist_dermanord(models.TransientModel):
    _name = 'product.pricelist.dermanord'
    _description = 'Product Pricelist Dermanord'

    pricelist_title_one = fields.Char(string='Column Title 1', required=True)
    pricelist_title_two = fields.Char(string='Column Title 2')
    pricelist_id_one = fields.Many2one(comodel_name='product.pricelist', string='Pricelist 1', required=True)
    pricelist_id_two = fields.Many2one(comodel_name='product.pricelist', string='Pricelist 2')
    version_id_one = fields.Many2one(comodel_name='product.pricelist.version', string='Pricelist Version 1', domain="[('pricelist_id', '=', pricelist_id_one)]", required=True)
    version_id_two = fields.Many2one(comodel_name='product.pricelist.version', string='Pricelist Version 2', domain="[('pricelist_id', '=', pricelist_id_two)]")

    @api.multi
    def print_report(self):
        data = []
        for c in self.env['product.category'].search([]):
            products = self.env['product.product'].search([('categ_id', '=', c.id), ('sale_ok', '=', True), ('website_published', '=', True)])
            data.append({
                'name': c.name,
                'products': [{
                    'name': p.name,
                    'col1': p.get_price_by_version(self.env['product.pricelist.version'].browse(self.version_id_two.id)) if self.version_id_two else '',
                    'col2': p.get_price_by_version(self.env['product.pricelist.version'].browse(self.pricelist_id_one.id)),
                } for p in products]
            })
        return self.pool['report'].get_action(self._cr, self._uid, [], 'product_pricelist_dermanord.report_pricelist', data=data, context=self._context)


class product_product(models.Model):
    _inherit = 'product.product'

    @api.multi
    def get_price_by_version(self, version):
        return 10.0


class ReportPricelist(models.AbstractModel):
    _name = 'report.product_pricelist_dermanord.report_pricelist'

    @api.model
    def render_html(self, docids, data=None):
        report_obj = self.env['report']
        report = report_obj._get_report_from_name('product_pricelist_dermanord.report_pricelist')
        docargs = {
            'docs': self,
            'data': data,
        }
        return report_obj.render('product_pricelist_dermanord.report_pricelist', docargs)
