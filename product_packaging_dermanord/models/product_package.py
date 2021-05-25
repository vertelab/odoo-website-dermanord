# -*- coding: utf-8 -*-
from odoo import models, fields, api

class RequestPackageType(models.Model):
    _name = 'res.package.type'
    name = fields.Char(string='Name', required=True)
    package_type = fields.Selection([('unit','Unit'),('pack','Pack'),('box', 'Box'), ('pallet', 'Pallet')], 'Type', required=True, default = "unit")
    height = fields.Float('Height', help='The height of the package')
    width = fields.Float('Width', help='The width of the package')
    length = fields.Float('Length', help='The length of the package')
    weight = fields.Float('Empty Package Weight')


class ProductPackaging(models.Model):
    _inherit = "product.packaging"

    @api.model
    def _reference_models(self):
        obj = self.env['res.package.type']
        res = obj.search_read(fields=['name_technical','name'])
        return [(r['name_technical'], r['name']) for r in res]

    name = fields.Many2one("res.package.type", "Package types")

    ul_container = fields.Many2one("res.package.type", "Pallet Logistic Unit")

    ul_qty = fields.Integer(
        string = "Packages By Layer"
    ) 

    rows = fields.Integer(
        string = "Number Of Layers"
    ) 

    weight = fields.Float(
        string = "Total Package Weight"
    ) 
