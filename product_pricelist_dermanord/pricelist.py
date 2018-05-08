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
    date = fields.Date(string='Date', required=True)
    fiscal_position_id = fields.Many2one(comodel_name='account.fiscal.position', string='Fiscal Position', required=True)
    def compute_lang(self):
        return self.env['res.lang'].search([('code', '=', 'sv_SE')])
    lang = fields.Many2one(comodel_name='res.lang', string='Language', default=compute_lang, required=True)

    @api.multi
    def print_report(self):
        data = {
            'date': self.date,
            'pricelist_title_one': self.pricelist_title_one,
            'pricelist_title_two': self.pricelist_title_two,
            'pricelist': (('%s + ' %self.pricelist_id_two.name) if self.pricelist_id_two else '') + self.pricelist_id_one.name,
            'fiscal_position': self.fiscal_position_id.name,
            'currency': self.pricelist_id_one.currency_id.name,
            'categories': [],
            'pricelist_id': self.pricelist_id_one.id,
        }
        domain = [('sale_ok', '=', True)]
        if self._context.get('active_ids'):
            domain.append(('id', 'in', self._context.get('active_ids')))
        all_products = self.env['product.product'].search(domain, order='default_code')
        for c in self.env['product.category'].search([('id', 'in', all_products.mapped('categ_id').mapped('id'))], order='parent_id, name'):
            show_categ = False
            d = {
                'name': self.categ_name_format(c.display_name, c.name_report),
                'products': []
            }
            products = all_products.filtered(lambda p: p.categ_id == c)
            for p in products:
                col1_price = p.get_price_by_pricelist(self.pricelist_id_one, self.date, self.fiscal_position_id)
                col2_price = p.get_price_by_pricelist(self.pricelist_id_two, self.date, self.fiscal_position_id) if self.pricelist_id_two else ''
                if col1_price != '0.0000' and col2_price != '0.0000':
                    d['products'].append({
                        'name': p.display_name,
                        'col1': '%.2f' %float(col1_price),
                        'col2': '%.2f' %float(col2_price),
                    })
                    show_categ = True
            if show_categ:
                data['categories'].append(d)
        ctx = self._context.copy()
        ctx['translatable'] = True
        ctx['report_lang'] = self.lang.code
        ctx['lang'] = self.lang.code # this does not work
        return self.pool['report'].get_action(self._cr, self._uid, [], 'product_pricelist_dermanord.report_pricelist', data=data, context=ctx)

    def categ_name_format(self, display_name, name_report):
        if '/' in display_name:
            return '/'.join(display_name.split('/')[:-1]+[' %s' %name_report]) if name_report else display_name
        else:
            return name_report if name_report else display_name


class product_product(models.Model):
    _inherit = 'product.product'

    @api.multi
    def get_price_by_pricelist(self, pricelist, date, fiscal_position_id):
        price_rule = self.env['product.pricelist'].with_context(date=date)._price_rule_get_multi(pricelist, [(self, 1, self.env.user.partner_id)])
        taxes = 0.0
        for c in fiscal_position_id.map_tax(self.taxes_id).compute_all(self.lst_price, 1, None, self.env.user.partner_id)['taxes']:
            taxes += c.get('amount', 0.0)
        return '%.4f' %(price_rule[self.id][0] + taxes)


class product_category(models.Model):
    _inherit = 'product.category'

    name_report = fields.Char(string='Name for Report', translate=True)


class ReportPricelist(models.AbstractModel):
    _name = 'report.product_pricelist_dermanord.report_pricelist'

    @api.model
    def render_html(self, docids, data=None):
        report_obj = self.env['report']
        report = report_obj._get_report_from_name('product_pricelist_dermanord.report_pricelist')
        docargs = {
            'doc_ids': docids,
            'doc_model': report.model,
            'o': data,
        }
        res = report_obj.with_context(translatable=self._context['translatable'], lang=self._context['report_lang']).render('product_pricelist_dermanord.report_pricelist', docargs)
        return res
