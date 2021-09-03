# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models, _
from odoo.addons.base.models.res_partner import WARNING_MESSAGE, WARNING_HELP

_logger = logging.getLogger(__name__)


class ProductAttribute(models.Model):
    _inherit = "product.attribute"

    use_from_price = fields.Boolean(
        string="Use From Price",
        help="Determines that a product should use from price when rendered in shop",
    )


class ProductTemplate(models.Model):
    _inherit = "product.template"

    from_price = fields.Float(string="From Price", compute="_from_price")

    def _from_price(self):
        self.from_price = 50.0  # Search for variant with lowest price
        # below code is not good enough. It should call compute_price on product.template
        # res = self.list_price or self.lst_price
        # if self.product_variant_ids:
        #     variants = self.product_variant_ids.mapped(id)
        #     res = call compute_price somehow..
        # self.from_price = res

    def _get_combination_info(
        self,
        combination=False,
        product_id=False,
        add_qty=1,
        pricelist=False,
        parent_combination=False,
        only_template=False,
    ):
        res = super(ProductTemplate, self)._get_combination_info(
            combination=combination,
            product_id=product_id,
            add_qty=add_qty,
            pricelist=pricelist,
            parent_combination=parent_combination,
            only_template=only_template,
        )

        product = self.env["product.template"].browse(res["product_template_id"])

        res["use_from_price"] = False

        for line in product.attribute_line_ids:
            if line.attribute_id.use_from_price:
                res["use_from_price"] = line.attribute_id.use_from_price

        # disabled this for now since it's nonsense
        # res["from_price"] = product.from_price

        return res
