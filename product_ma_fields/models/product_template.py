# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_combination_info(self, combination=False, product_id=False, add_qty=1, pricelist=False, parent_combination=False, only_template=False):
        res = super(ProductTemplate, self)._get_combination_info(combination=combination, product_id=product_id, add_qty=add_qty, pricelist=pricelist, parent_combination=parent_combination, only_template=only_template)

        product = self.env['product.product'].browse(res['product_id'])

        res['description_webshop'] = product.description_webshop
        res['description_use'] = product.description_use
        res['description_ingredients'] = product.description_ingredients

        _logger.warning(f'RES is: {res}')
        return res
