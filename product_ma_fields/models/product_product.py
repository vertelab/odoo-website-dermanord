# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ProductProduct(models.Model):
    _inherit = 'product.product'

    description_webshop = fields.Text(string="Webshop Description")
    description_use = fields.Text(string="Use description")
    description_ingredients = fields.Text(string="Ingredients")
