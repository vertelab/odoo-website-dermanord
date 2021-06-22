# -*- coding: utf-8 -*-

from openerp import models, fields, api

class stock_picking(models.Model):
    _inherit = 'stock.picking'

    for_reseller = fields.Boolean(string="For Reseller",help="Displays if the end customer is a reseller or not", default=True)