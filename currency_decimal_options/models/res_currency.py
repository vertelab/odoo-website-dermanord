# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import UserError


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    website_decimal_places = fields.Integer(string="Website Decimal Places",
        help="Technical Field. Controls the decimal precision that the frontend website should provide to the user.")

