# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductProduct(models.Model):
    _inherit = "product.product"

    ean13 = fields.Char(
            'ean13', copy=False,
            help="International Article Number used for product identification.")
