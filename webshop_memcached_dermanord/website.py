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
from openerp.addons.reseller_dermanord.main import website_sale_home
from openerp.addons.website_reseller_register_dermanord.website import reseller_register
from openerp.addons.website_sale.controllers.main import get_pricelist

import logging
_logger = logging.getLogger(__name__)


class Website(models.Model):
    _inherit = 'website'

    def get_dn_groups(self):
        return [g.id for g in request.env.user.commercial_partner_id.access_group_ids]

    def get_webshop_type(self):
        return request.env.user.webshop_type

    def get_search_values(self, kw=None):
        def dedictify(value):
            # Order is not guaranteed in a dict. Make it a list of tuples instead
            if type(value) == dict:
                value = [(key, dedictify(value[key])) for key in sorted(value.keys())]
            return value
        attrs = ['chosen_filter_qty', 'form_values', 'sort_order', 'sort_name', 'current_ingredient']
        if kw:
            request.website.dn_shop_set_session('product.template', kw, '/webshop')
        return (' pricelist: %s ' % get_pricelist()) + ' '.join(['%s: %s' % (attr, dedictify(request.session.get(attr))) for attr in attrs]).replace('{', '{{').replace('}', '}}')

class WebsiteSale(WebsiteSale):

    #~ @http.route([
        # ~ '/webshop',
        # ~ '/webshop/page/<int:page>',
        # ~ '/webshop/category/<model("product.public.category"):category>',
        # ~ '/webshop/category/<model("product.public.category"):category>/page/<int:page>',
    #~ ], type='http', auth="public", website=True)
    @memcached.route(key=lambda kw:'db: {db} base.group_website_publisher: {publisher} base.group_website_designer: {designer} path: {path} logged_in: {logged_in} lang: {lang}%s groups: %s webshop_type: %s' % (request.website.get_search_values(kw), request.website.get_dn_groups(), request.website.get_webshop_type()), flush_type=lambda kw: 'webshop', no_cache=True, cache_age=31536000, max_age=31536000, s_maxage=600)
    def webshop(self, page=0, category=None, search='', **post):
        request.website.dn_shop_set_session('product.template', post, '/webshop')
        return super(WebsiteSale, self).webshop(page, category, search, **post)

    #~ @http.route(['/dn_shop/product/<model("product.template"):product>'], type='http', auth="public", website=True)
    @memcached.route(key=lambda kw:'db: {db} path: {path} logged_in: {logged_in} lang: {lang}', flush_type=lambda kw: 'webshop', no_cache=True, cache_age=31536000, max_age=31536000, s_maxage=600)
    def dn_product(self, product, category='', search='', **post):
        return super(WebsiteSale, self).dn_product(product, category, search, **post)

    #~ @http.route([
        #~ '/dn_shop/variant/<model("product.product"):variant>'
    #~ ], type='http', auth="public", website=True)
    @memcached.route(key=lambda kw:'db: {db} path: {path} logged_in: {logged_in} lang: {lang}', flush_type=lambda kw: 'webshop', no_cache=True, cache_age=31536000, max_age=31536000, s_maxage=600)
    def dn_product_variant(self, variant, category='', search='', **post):
        return super(WebsiteSale, self).dn_product_variant(variant, category, search, **post)

    #~ # '/shop/cart'
    #~ @memcached.route()
    #~ def cart(self, **post):
        #~ return super(WebsiteSale, self).cart(**post)

    #~ # '/shop/cart/update'
    #~ @memcached.route()
    #~ def cart_update(self, product_id, add_qty=1, set_qty=0, **kw):
        #~ return super(WebsiteSale, self).cart_update(product_id, add_qty, set_qty, **kw)

class WebsiteSaleHome(website_sale_home):

    # flush memcached top_image
    @http.route(['/home/<model("res.users"):home_user>/info_update'], type='http', auth="user", website=True)
    def info_update(self, home_user=None, **post):
        res = super(WebsiteSaleHome, self).info_update(home_user=home_user, **post)
        if home_user and post:
            for key in memcached.get_keys(path='/imagefield/res.partner/top_image/%s/ref/reseller_dermanord.reseller_top_image' % home_user.partner_id.commercial_partner_id.id):
                memcached.mc_delete(key)
        return res

    # flush memcached contact image
    @http.route(['/home/<model("res.users"):home_user>/contact/new', '/home/<model("res.users"):home_user>/contact/<model("res.partner"):partner>'], type='http', auth='user', website=True)
    def contact_page(self, home_user=None, partner=None, **post):
        res = super(WebsiteSaleHome, self).contact_page(home_user=home_user, partner=partner, **post)
        if partner and post:
            for key in memcached.get_keys(path='/imagefield/res.partner/image/%s/ref/reseller_dermanord.reseller_contact_img' % partner.id):
                memcached.mc_delete(key)
        return res


class reseller_register(reseller_register):

    # flush memcached top_image
    @http.route(['/reseller_register/new', '/reseller_register/<int:issue_id>', '/reseller_register/<int:issue_id>/<string:action>'], type='http', auth='public', website=True)
    def reseller_register_new(self, issue_id=None, action=None, **post):
        res = super(reseller_register, self).reseller_register_new(issue_id=issue_id, action=action, **post)
        if issue_id and post:
            issue = self.get_issue(issue_id, post.get('token'))
            for key in memcached.get_keys(path='/imagefield/res.partner/top_image/%s/ref/reseller_dermanord.reseller_top_image' % issue.partner_id.id):
                memcached.mc_delete(key)
        return res

    # flush memcached contact image
    @http.route(['/reseller_register/<int:issue_id>/contact/new', '/reseller_register/<int:issue_id>/contact/<int:contact>'], type='http', auth='public', website=True)
    def reseller_contact_new(self, issue_id=None, contact=0, **post):
        res = super(reseller_register, self).reseller_contact_new(issue_id=issue_id, contact=contact, **post)
        if contact and contact != 0 and post:
            contact = request.env['res.partner'].sudo().browse(contact)
            for key in memcached.get_keys(path='/imagefield/res.partner/image/%s/ref/reseller_dermanord.reseller_contact_img' % contact.id):
                memcached.mc_delete(key)
        return res
