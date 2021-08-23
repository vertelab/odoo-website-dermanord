# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    description_webshop = fields.Text(string="Webshop Description")
    description_use = fields.Text(string="Use description")
    description_ingredients = fields.Text(string="Ingredients")
