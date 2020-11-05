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
from openerp.addons.website.controllers.main import Website as WebsiteOld

from openerp.addons.webshop_dermanord.models.webshop_dermanord import WebsiteSale
from openerp.addons.reseller_dermanord.main import website_sale_home
from openerp.addons.website_reseller_register_dermanord.website import reseller_register
from openerp.addons.website_consumer_register_dermanord.website import consumer_register
from openerp.addons.website_sale.controllers.main import get_pricelist

import logging
_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    memcached_time = fields.Datetime(string='Memcached Timestamp', default=lambda *args, **kwargs: fields.Datetime.now(), help="Last modification relevant to memcached.")

class Website(models.Model):
    _inherit = 'website'

    def get_dn_groups(self):
        groups = [g.id for g in request.env.user.commercial_partner_id.access_group_ids]
        if self.env.ref('webshop_dermanord.group_dn_ht').id in groups: # Webbplatsbehörigheter / Hudterapeut
            return u'hudterapeut'
        elif self.env.ref('webshop_dermanord.group_dn_spa').id in groups: # Webbplatsbehörigheter / SPA-Terapeut
            return u'SPA-terapeut'
        elif self.env.ref('webshop_dermanord.group_dn_af').id in groups: # Webbplatsbehörigheter / Återförsäljare
            return u'Återförsäljare'
        elif self.env.ref('webshop_dermanord.group_dn_sk').id in groups: # Webbplatsbehörigheter / slutkonsument
            return u'Slutkonsument'
        else:
            return u''
        

    def get_webshop_type(self, post):
        if not request.env.user.webshop_type or request.env.user.webshop_type not in ['dn_shop', 'dn_list']: # first time use filter
            if request.env.user.commercial_partner_id.property_product_pricelist.for_reseller: # reseller
                request.env.user.webshop_type = 'dn_list'
            else: # public user / not reseller
                request.env.user.webshop_type = 'dn_shop'
        else:
            if post.get('webshop_type'):
                if post.get('webshop_type') == 'dn_shop': # use imageview in view switcher
                    request.env.user.webshop_type = 'dn_shop'
                elif post.get('webshop_type') == 'dn_list': # use listview in view switcher
                    request.env.user.webshop_type = 'dn_list'
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
        # ~ '/webshop/category/<model("product.public.category"):category>',
    #~ ], type='http', auth="public", website=True)
    @memcached.route(
        key=lambda kw: u'db: {db} base.group_website_publisher: {publisher} base.group_website_designer: {designer} path: {path} logged_in: {logged_in} lang: {lang} country: {country}%s group: %s webshop_type: %s%s' % (request.website.get_search_values(kw), request.website.get_dn_groups(), request.website.get_webshop_type(kw), request.website.dn_handle_webshop_session(kw.get('category'), kw.get('preset'), {}, require_cat_preset=False) or ''),
        flush_type=lambda kw: 'webshop',
        no_cache=True,
        cache_age=86400,  # Memcached    43200 (12 tim)  86400 (24 tim)  31536000 (1 år)
        max_age=31536000, # Webbläsare
        s_maxage=600)
    def webshop(self, category=None, search='', preset=None, **post):
        request.website.dn_shop_set_session('product.template', post, '/webshop')
        return super(WebsiteSale, self).webshop(category, search, preset=preset, **post)

    #~ @http.route(['/dn_shop/product/<model("product.template"):product>'], type='http', auth="public", website=True)
    @memcached.route(
        key=lambda kw: u'db: {db} base.group_website_publisher: {publisher} base.group_website_designer: {designer} path: {path} logged_in: {logged_in} lang: {lang} country: {country} group: %s memcached_time: %s' % 
                                (request.website.get_dn_groups(), (kw.get('product') and (kw['product'].id, kw['product'].memcached_time or ''))),
        flush_type=lambda kw: 'dn_shop',
        no_cache=True,
        cache_age=86400,    # Memcached    43200 (12 tim)  86400 (24 tim)  31536000 (1 år)
        max_age=31536000,   # Webbläsare
        s_maxage=600)
    def dn_product(self, product, category='', search='', **post):
        return super(WebsiteSale, self).dn_product(product, category, search, **post)

    #~ @http.route([
        #~ '/dn_shop/variant/<model("product.product"):variant>'
    #~ ], type='http', auth="public", website=True)
    @memcached.route(
        key=lambda kw: u'db: {db} base.group_website_publisher: {publisher} base.group_website_designer: {designer} path: {path} logged_in: {logged_in} lang: {lang} country: {country} groups: %s memcached_time: %s' % (request.website.get_dn_groups(), (kw.get('variant') and (kw['variant'].id, kw['variant'].memcached_time or ''))),
        flush_type=lambda kw: 'dn_shop',
        no_cache=True,
        cache_age=86400,   # Memcached    43200 (12 tim)  86400 (24 tim)  31536000 (1 år)
        max_age=31536000,  # Webbläsare
        s_maxage=600)
    def dn_product_variant(self, variant, category='', search='', **kwargs):
        return super(WebsiteSale, self).dn_product_variant(variant, category, search, **kwargs)

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
    @http.route(['/my/salon/<model("res.users"):home_user>/info_update'], type='http', auth="user", website=True)
    def info_update(self, home_user=None, **post):
        res = super(WebsiteSaleHome, self).info_update(home_user=home_user, **post)
        if home_user and post:
            home_user.sudo().commercial_partner_id.memcached_time = fields.Datetime.now()
        return res

    # flush memcached contact image
    @http.route(['/my/salon/<model("res.users"):home_user>/contact/new', '/my/salon/<model("res.users"):home_user>/contact/<model("res.partner"):partner>'], type='http', auth='user', website=True)
    def contact_page(self, home_user=None, partner=None, **post):
        res = super(WebsiteSaleHome, self).contact_page(home_user=home_user, partner=partner, **post)
        if partner and post:
            partner.sudo().memcached_time = fields.Datetime.now()
        return res
        


class reseller_register(reseller_register):

    # flush memcached top_image
    @http.route(['/reseller_register/new', '/reseller_register/<int:issue_id>', '/reseller_register/<int:issue_id>/<string:action>'], type='http', auth='public', website=True)
    def reseller_register_new(self, issue_id=None, action=None, **post):
        res = super(reseller_register, self).reseller_register_new(issue_id=issue_id, action=action, **post)
        if issue_id and post:
            issue = self.get_issue(issue_id, post.get('token'))
            if issue:
                issue.sudo().partner_id.memcached_time = fields.Datetime.now()
        return res

    # flush memcached contact image
    @http.route(['/reseller_register/<int:issue_id>/contact/new', '/reseller_register/<int:issue_id>/contact/<int:contact>'], type='http', auth='public', website=True)
    def reseller_contact_new(self, issue_id=None, contact=0, **post):
        res = super(reseller_register, self).reseller_contact_new(issue_id=issue_id, contact=contact, **post)
        if contact and contact != 0 and post:
            contact = request.env['res.partner'].sudo().browse(contact)
            contact.memcached_time = fields.Datetime.now()
        return res
        
class consumer_register(consumer_register):

    # flush memcached top_image
    @http.route(['/consumer_register/new', '/consumer_register/<int:issue_id>', '/consumer_register/<int:issue_id>/<string:action>'], type='http', auth='public', website=True)
    def consumer_register_new(self, issue_id=None, action=None, **post):
        res = super(consumer_register, self).consumer_register_new(issue_id=issue_id, action=action, **post)
        if issue_id and post:
            issue = self.get_issue(issue_id, post.get('token'))
            if issue:
                issue.sudo().partner_id.memcached_time = fields.Datetime.now()
        return res

    # flush memcached contact image
    @http.route(['/consumer_register/<int:issue_id>/contact/new', '/consumer_register/<int:issue_id>/contact/<int:contact>'], type='http', auth='public', website=True)
    def consumer_contact_new(self, issue_id=None, contact=0, **post):
        res = super(consumer_register, self).consumer_contact_new(issue_id=issue_id, contact=contact, **post)
        if contact and contact != 0 and post:
            contact = request.env['res.partner'].sudo().browse(contact)
            contact.memcached_time = fields.Datetime.now()
        return res
