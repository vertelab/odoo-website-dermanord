# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = "product.product"

    description_webshop = fields.Text(
        string="Webshop Description", help="Webshop Description"
    )
    description_use = fields.Text(string="Use description", help="Use description")
    description_ingredients = fields.Text(string="Ingredients", help="Ingredients")
    ean13 = fields.Char(string="EAN13 Barcode")
    variant_name = fields.Char(
        string="Name", help="Friendly product name", compute="_compute_variant_name"
    )  # TODO: make stored to increase preformance.
    variant_accessory_product_ids = fields.Many2many(
        "product.product",
        "prod_prod_accessory_rel",
        "src_id",
        "dest_id",
        string="Accessory Products",
        check_company=True,
        help="Accessories show up when the customer reviews the cart before payment (cross-sell strategy).",
    )

    def _compute_variant_name(self):
        for rec in self:
            # Consider changing this to using
            # rec.with_context(display_default_code=False).display_name
            # for products with only 1 variant this will exclude the
            # attribute values though. Does this solution too?
            res = (
                rec.display_name.split("] ")[1]
                if "] " in rec.display_name
                else rec.display_name
            )
            rec.variant_name = res
