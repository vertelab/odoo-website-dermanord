
from odoo import models, fields, api, http
from odoo.addons.website_sale_stock.controllers.variant import WebsiteSaleStockVariantController
from odoo.addons.product.models.product_pricelist import Pricelist

class Pricelist(models.Model):
    _inherit = 'product.pricelist'
    
    for_reseller = fields.Boolean(default=True, required=True)
