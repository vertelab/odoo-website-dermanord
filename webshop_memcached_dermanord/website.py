# -*- coding: utf-8 -*-
##############################################################################
#
# Odoo, Open Source Management Solution, third party addon
# Copyright (C) 2018- Vertel AB (<http://vertel.se>).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp import models, fields, api, _
from openerp import http
from openerp.addons.web.http import request
from openerp.addons.website_memcached import memcached

from openerp.addons.webshop_dermanord.webshop_dermanord import WebsiteSale
from openerp.addons.website_sale.controllers.main import get_pricelist

import logging
_logger = logging.getLogger(__name__)

class Website(models.Model):
    _inherit = 'website'

    def get_search_values(self, kw):
        _logger.warn('\nkw: %s\n' % kw)
        _logger.warn('\nsession: %s\n\n' % request.session)
        attrs = ['chosen_filter_qty', 'form_values', 'sort_order', 'sort_name']
        if kw:
            request.website.dn_shop_set_session(kw, '/dn_shop')
        _logger.warn('\nsession: %s\n\n' % request.session)
        return (' pricelist: %s ' % get_pricelist()) + ' '.join(['%s: %s' % (attr, request.session.get(attr)) for attr in attrs]).replace('{', '{{').replace('}', '}}')

class WebsiteSale(WebsiteSale):

    #~ @http.route([
        #~ '/dn_shop',
        #~ '/dn_shop/page/<int:page>',
        #~ '/dn_shop/category/<model("product.public.category"):category>',
        #~ '/dn_shop/category/<model("product.public.category"):category>/page/<int:page>',
    #~ ], type='http', auth="public", website=True)
    @memcached.route(key=lambda kw:'db: {db} base.group_website_publisher: {publisher} base.group_website_designer: {designer} path: {path} logged_in: {logged_in} lang: {lang}%s' % request.website.get_search_values(kw), flush_type='dn_shop')
    def dn_shop(self, page=0, category=None, search='', **post):
        return super(WebsiteSale, self).dn_shop(page, category, search, **post)

    #~ @http.route([
        #~ '/dn_list',
        #~ '/dn_list/page/<int:page>',
        #~ '/dn_list/category/<model("product.public.category"):category>',
        #~ '/dn_list/category/<model("product.public.category"):category>/page/<int:page>',
    #~ ], type='http', auth="public", website=True)
    @memcached.route(key=lambda kw:'db: {db} path: {path} logged_in: {logged_in} lang: {lang}%s' % request.website.get_search_values(kw), flush_type='dn_shop')
    def dn_list(self, page=0, category=None, search='', **post):
        return super(WebsiteSale, self).dn_list(page, category, search, **post)

    #~ # '/dn_list'
    #~ @memcached.route()
    #~ def dn_list(self, page=0, category=None, search='', **post):
        #~ return super(WebsiteSale, self).dn_list(page, category, search, **post)
  
    # '/shop/product/<model("product.template"):product>'
    @memcached.route(key=lambda kw:'db: {db} path: {path} logged_in: {logged_in} lang: {lang}%s' % request.website.get_search_values(kw), flush_type='dn_shop')
    def product(self, product, category='', search='', **kwargs):
        return super(WebsiteSale, self).product(product, category, search, **post)

    #~ @http.route([
        #~ '/dn_shop/variant/<model("product.product"):variant>'
    #~ ], type='http', auth="public", website=True)
    @memcached.route(key=lambda kw:'db: {db} path: {path} logged_in: {logged_in} lang: {lang}%s' % request.website.get_search_values(kw), flush_type='dn_shop')
    def dn_product_variant(self, variant, category='', search='', **kwargs):
        return super(WebsiteSale, self).dn_product_variant(variant, category, search, **kwargs)



    #~ # '/shop/product/comment/<int:product_template_id>'
    #~ @memcached.route()
    #~ def product_comment(self, product_template_id, **post):
        #~ return super(WebsiteSale, self).product_comment(product_template_id, **post)

    #~ # '/dn_shop/variant/<model("product.product"):variant>'
    #~ @memcached.route()
    #~ def dn_product_variant(self, variant, category='', search='', **kwargs):
        #~ return super(WebsiteSale, self).dn_product_variant(variant, category, search, **kwargs)

    #~ # '/shop/cart'
    #~ @memcached.route()
    #~ def cart(self, **post):
        #~ return super(WebsiteSale, self).cart(**post)

    #~ # '/shop/cart/update'
    #~ @memcached.route()
    #~ def cart_update(self, product_id, add_qty=1, set_qty=0, **kw):
        #~ return super(WebsiteSale, self).cart_update(product_id, add_qty, set_qty, **kw)
