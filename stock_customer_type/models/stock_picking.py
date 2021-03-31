# ~ # -*- coding: utf-8 -*-

from odoo import models, fields, api, http
from odoo.addons.website_sale_stock.controllers.variant import WebsiteSaleStockVariantController
from odoo.addons.stock.models.stock_picking import Picking

import logging
_logger = logging.getLogger(__name__)


class Picking(models.Model):
    _inherit = 'stock.picking'
    is_reseller = fields.Boolean(related = "partner_id.property_product_pricelist.for_reseller")
    
