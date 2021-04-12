# -*- coding: utf-8 -*-
# from odoo import http


# class SaleJournalDermanord(http.Controller):
#     @http.route('/sale_journal_dermanord/sale_journal_dermanord/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/sale_journal_dermanord/sale_journal_dermanord/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('sale_journal_dermanord.listing', {
#             'root': '/sale_journal_dermanord/sale_journal_dermanord',
#             'objects': http.request.env['sale_journal_dermanord.sale_journal_dermanord'].search([]),
#         })

#     @http.route('/sale_journal_dermanord/sale_journal_dermanord/objects/<model("sale_journal_dermanord.sale_journal_dermanord"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('sale_journal_dermanord.object', {
#             'object': obj
#         })
