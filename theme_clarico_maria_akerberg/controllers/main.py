# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution, third party addon
#    Copyright (C) 2004-2021 Vertel AB (<http://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging

from odoo import fields, http, SUPERUSER_ID, tools, _
from odoo.http import request
from odoo.addons.emipro_theme_base.controller.main import WebsiteSale
import json

_logger = logging.getLogger(__name__)


class WebsiteSale(WebsiteSale):
    # --------------------------------------------------------------------------
    # Accessory Products
    # --------------------------------------------------------------------------
    @http.route(
        "/shop/products/variant_accessories", type="json", auth="public", website=True
    )
    def variant_accessories(self, **kwargs):
        data = json.loads(request.httprequest.data)
        return self._get_variant_accessories(int(data.get('params', {}).get('variant_id')))

    def _get_variant_accessories(self, variant_id):
        """
        Returns list of accessories for the specific variant
        """
        variant = (
            request.env["product.product"]
            .with_context(display_default_code=False)
            .browse(variant_id)
        )

        if variant.exists():
            FieldMonetary = request.env["ir.qweb.field.monetary"]
            monetary_options = {
                "display_currency": request.website.get_current_pricelist().currency_id,
            }
            rating = request.website.viewref("website_sale.product_comment").active
            res = {"products": []}
            for product in variant.variant_accessory_product_ids:
                combination_info = product._get_combination_info_variant()
                res_product = product.read(["id", "name", "website_url"])[0]
                res_product.update(combination_info)
                res_product["price"] = FieldMonetary.value_to_html(
                    res_product["price"], monetary_options
                )
                if rating:
                    res_product["rating"] = request.env["ir.ui.view"]._render_template(
                        "portal_rating.rating_widget_stars_static",
                        values={
                            "rating_avg": product.rating_avg,
                            "rating_count": product.rating_count,
                        },
                    )
                res["products"].append(res_product)
            return res
        return {}
