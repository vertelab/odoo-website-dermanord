# -*- coding: utf-8 -*-
# from odoo import http


# class Odoo-stock-picking(http.Controller):
#     @http.route('/odoo-stock-picking/odoo-stock-picking/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/odoo-stock-picking/odoo-stock-picking/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('odoo-stock-picking.listing', {
#             'root': '/odoo-stock-picking/odoo-stock-picking',
#             'objects': http.request.env['odoo-stock-picking.odoo-stock-picking'].search([]),
#         })

#     @http.route('/odoo-stock-picking/odoo-stock-picking/objects/<model("odoo-stock-picking.odoo-stock-picking"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('odoo-stock-picking.object', {
#             'object': obj
#         })
