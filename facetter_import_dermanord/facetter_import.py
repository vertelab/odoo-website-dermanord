#!/usr/bin/python
# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from xlrd import open_workbook
from xlrd.book import Book
from xlrd.sheet import Sheet

import os
import logging
_logger = logging.getLogger(__name__)

class product_product(models.Model):
    _inherit = 'product.product'

    @api.model
    def facetter_import(self):
        wb = open_workbook(os.path.join(os.path.dirname(os.path.abspath(__file__)), u'facetter.xlsx'))
        ws = wb.sheet_by_index(0)

        products = {}
        product_id = ''
        products_unknow = []
        products_debug = {}

        for r in range(ws.nrows):
            if r > 0:
                if ws.cell_value(r, 0) == '' or ws.cell_value(r, 0).startswith('__export__.product_product_'):
                    if ws.cell_value(r, 0) != '':
                        product_id = ws.cell_value(r, 0).split('_')[-1]
                        product_id = int(product_id)
                        products[product_id] = []
                    if ws.cell_value(r, 4) == 'product.product.facet.line':
                        if ws.cell_value(r, 6) != '':
                            products[product_id].append((ws.cell_value(r, 6), ws.cell_value(r, 7)))
                    elif ws.cell_value(r, 4) == '':
                        if ws.cell_value(r, 5) != '':
                            products[product_id].append((ws.cell_value(r, 5), ws.cell_value(r, 6)))
                    elif ws.cell_value(r, 5) == 'product.product.facet.line':
                        if ws.cell_value(r, 7) != '':
                            products[product_id].append((ws.cell_value(r, 7), ws.cell_value(r, 8)))
                else:
                    products_unknow.append(ws.cell_value(r, 0))

        #~ return products
        _logger.warn('Product Unkown: %s' %products_unknow)
        #~ return products_debug

        self.env['product.product.facet.line'].search([]).unlink()

        for product,facets in products.items():
            facet_ids = []
            for facet in facets:
                facet_value = self.env['product.facet.value'].search([('facet_id', '=', facet[1]), ('name', '=', facet[0])])
                facet_id = self.env['product.facet'].search([('name', '=', facet[1])])
                if facet_value and facet_id:
                    facet_ids.append((facet_value, facet_id))
            product_product = self.env['product.product'].browse(product)
            read_ok = False
            try:
                product_product.name
                read_ok = True
            except:
                _logger.error('>>> Product: %s can not read' %product_product)
            if product_product and read_ok:
                try:
                    fs = self.env['product.facet'].browse()
                    facet_line_ids = {}
                    for f in facet_ids:
                        fs |= f[1]
                    for f in fs:
                        facet_line_ids[f.id] = []
                        for v in facet_ids:
                            if v[1] == f:
                                facet_line_ids[f.id].append(v[0].id)
                    for k,v in facet_line_ids.items():
                        self.env['product.product.facet.line'].create({
                            'facet_id': k,
                            'value_ids': [(6, 0, v)],
                            'product_id': product_product.id,
                        })
                    _logger.warn('Product: %s Facet updated' %product_product)
                except:
                    _logger.error('>>> Product: %s got error' %product_product)
