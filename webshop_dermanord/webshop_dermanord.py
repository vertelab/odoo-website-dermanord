# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2004-2015 Vertel AB (<http://vertel.se>).
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
from openerp.http import request
from datetime import datetime, date, timedelta
from lxml import html
from openerp.addons.website_sale.controllers.main import website_sale, QueryURL, table_compute
import werkzeug
from heapq import nlargest

import logging
_logger = logging.getLogger(__name__)

PPG = 20 # Products Per Page
PPR = 4  # Products Per Row

class blog_post(models.Model):
    _inherit = 'blog.post'

    product_public_categ_ids = fields.Many2many(comodel_name='product.public.category', string='Product Public Categories')
    product_tmpl_ids = fields.Many2many(comodel_name='product.template', string='Product Templates')


class product_template(models.Model):
    _inherit = 'product.template'

    @api.one
    def _blog_post_ids(self):
        if type(self.id) is int:
            blog_posts = self.env['blog.post'].search_read(['&', ('website_published', '=', True),'|', ('product_tmpl_ids', 'in', self.id), ('product_public_categ_ids', 'in', self.public_categ_ids.mapped('id'))],['id'])
            self.blog_post_ids = [(6, 0, [p['id'] for p in blog_posts])]
            #~ self.blog_post_ids = [(6, 0, blog_posts.filtered(lambda b: b.website_published == True).mapped('id'))]
    blog_post_ids = fields.Many2many(comodel_name='blog.post', string='Posts', compute='_blog_post_ids')
    list_price_tax = fields.Float(compute='get_product_tax')
    price_tax = fields.Float(compute='get_product_tax')
    recommended_price = fields.Float(compute='get_product_tax')
    sold_qty = fields.Integer(string='Sold', default=0)

    @api.one
    def get_product_tax(self):
        res = 0
        for c in self.sudo().taxes_id.compute_all(
                self.list_price, 1, None,
                self.env.user.partner_id)['taxes']:
            res += c.get('amount', 0.0)
        self.list_price_tax = self.list_price + res

        res = 0
        for c in self.sudo().taxes_id.compute_all(
                self.price, 1, None,
                self.env.user.partner_id)['taxes']:
            res += c.get('amount', 0.0)
        self.price_tax = self.price + res
        self.recommended_price = 0.0


class product_product(models.Model):
    _inherit = 'product.product'

    recommended_price = fields.Float(compute='get_product_tax', compute_sudo=True)
    so_line_ids = fields.One2many(comodel_name='sale.order.line', inverse_name='product_id')
    sold_qty = fields.Integer(string='Sold', default=0)

    @api.one
    def get_product_tax(self):
        res = 0
        price = self.env.ref('product.list0').price_get(self.id, 1)[1]
        for c in self.sudo().taxes_id.compute_all(price, 1, None, self.env.user.partner_id)['taxes']:
            res += c.get('amount', 0.0)
        self.recommended_price = price + res

    @api.model
    def update_sold_qty(self):
        self._cr.execute('UPDATE product_template SET sold_qty = 0')
        self._cr.execute('UPDATE product_product SET sold_qty = 0')
        so_lines = self.env['sale.order'].search([('date_confirm', '>', fields.Date.to_string(date.today() - timedelta(days=30)))]).mapped('order_line').filtered(lambda l : l.state in ['confirmed', 'done'])
        templates = []
        products = {}
        if len(so_lines) > 0:
            for line in so_lines:
                if products.get(line.product_id):
                    products[line.product_id] += sum(line.mapped('product_uom_qty'))
                else:
                    products[line.product_id] = sum(line.mapped('product_uom_qty'))
            for k, v in products.iteritems():
                k.sold_qty = v
                if k.product_tmpl_id not in templates:
                    templates.append(k.product_tmpl_id)
            for template in templates:
                template.sold_qty = sum(template.product_variant_ids.mapped('sold_qty'))
        return None


class product_pricelist(models.Model):
    _inherit = 'product.pricelist'

    for_reseller = fields.Boolean(string='For Reseller')


class website_sale(website_sale):

    def get_attribute_value_ids(self, product):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        currency_obj = pool['res.currency']
        attribute_value_ids = []
        visible_attrs = set(l.attribute_id.id
                                for l in product.attribute_line_ids
                                    if len(l.value_ids) > 1)
        if request.website.pricelist_id.id != context['pricelist']:
            website_currency_id = request.website.currency_id.id
            currency_id = self.get_pricelist().currency_id.id
            for p in product.product_variant_ids:
                price = currency_obj.compute(cr, uid, website_currency_id, currency_id, p.lst_price)
                attribute_value_ids.append([p.id, [v.id for v in p.attribute_value_ids if v.attribute_id.id in visible_attrs], p.price, price, p.recommended_price])
        else:
            attribute_value_ids = [[p.id, [v.id for v in p.attribute_value_ids if v.attribute_id.id in visible_attrs], p.price, p.lst_price, p.recommended_price] for p in product.sudo().product_variant_ids]

        return attribute_value_ids

    @http.route([
        '/dn_shop',
        '/dn_shop/page/<int:page>',
    ], type='http', auth="public", website=True)
    def dn_shop(self, page=0, category=None, search='', **post):
        return self.get_products(page=page, category=category, search=search, **post)

    #~ @http.route(['/dn_ingredient/<model("product.ingredient"):ingredient>'], type='http', auth="public", website=True)
    #~ def dn_ingredient(self, ingredient=None, page=0, category=None, search='', **post):
        #~ return self.get_products(page=page, category=category, search=search, **post)

    def get_domain_append(self, post):
        facet_ids = []
        category_ids = []
        ingredient_ids = []
        for k, v in post.iteritems():
            if k.split('_')[0] == 'facet':
                if v:
                    facet_ids.append(int(v))
            if k.split('_')[0] == 'category':
                if v:
                    category_ids.append(int(v))
            if k == 'ingredient':
                if v:
                    ingredient_ids.append(int(v))

        domain_append = []
        if len(facet_ids) != 0:
            facets = request.env['product.facet.value'].search([('id', 'in', facet_ids)])
            facet = {}
            for f in facets:
                if facet.get(f.name):
                    facet[f.name].append(f.id)
                else:
                    facet[f.name] = [f.id]
            value_ids = []
            for f, r in facet.iteritems():
                value_ids += r
            domain_append.append(('facet_line_ids.value_ids', 'in', value_ids))
        if len(category_ids) != 0:
            categories = request.env['product.public.category'].search([('id', 'in', category_ids)])
            category = {}
            for c in categories:
                if category.get(c.name):
                    category[c.name].append(c.id)
                else:
                    category[c.name] = [c.id]
            value_ids = []
            for c, r in category.iteritems():
                value_ids += r
            domain_append.append(('public_categ_ids', 'in', value_ids))
        if len(ingredient_ids) != 0:
            ingredients = request.env['product.ingredient'].search([('id', 'in', ingredient_ids)])
            ingredient = {}
            for i in ingredients:
                if ingredient.get(i.name):
                    ingredient[i.name].append(i.id)
                else:
                    ingredient[i.name] = [i.id]
            value_ids = []
            for i, r in ingredient.iteritems():
                value_ids += r
            domain_append.append(('ingredient_ids', 'in', value_ids))
        return domain_append

    def get_products(self, page=0, category=None, search='', **post):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry

        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [map(int, v.split("-")) for v in attrib_list if v]
        attrib_set = set([v[1] for v in attrib_values])
        domain = self._get_search_domain(search, category, attrib_values)
        domain += self.get_domain_append(post)

        keep = QueryURL('/dn_shop', category=category and int(category), search=search, attrib=attrib_list)

        if not context.get('pricelist'):
            pricelist = self.get_pricelist()
            context['pricelist'] = int(pricelist)
        else:
            pricelist = pool.get('product.pricelist').browse(cr, uid, context['pricelist'], context)

        product_obj = pool.get('product.template')

        url = "/dn_shop"
        product_count = product_obj.search_count(cr, uid, domain, context=context)
        if search:
            post["search"] = search
        if category:
            category = pool['product.public.category'].browse(cr, uid, int(category), context=context)
            url = "/shop/category/%s" % slug(category)
        if attrib_list:
            post['attrib'] = attrib_list
        pager = request.website.pager(url=url, total=product_count, page=page, step=PPG, scope=7, url_args=post)
        product_ids = product_obj.search(cr, uid, domain, limit=PPG, offset=pager['offset'], order=self._get_search_order(post), context=context)
        products = product_obj.browse(cr, uid, product_ids, context=context)
        #~ popular_products = nlargest(20, products.mapped('sold_qty'))

        style_obj = pool['product.style']
        style_ids = style_obj.search(cr, uid, [], context=context)
        styles = style_obj.browse(cr, uid, style_ids, context=context)

        category_obj = pool['product.public.category']
        category_ids = category_obj.search(cr, uid, [('parent_id', '=', False)], context=context)
        categs = category_obj.browse(cr, uid, category_ids, context=context)

        attributes_obj = request.registry['product.attribute']
        attributes_ids = attributes_obj.search(cr, uid, [], context=context)
        attributes = attributes_obj.browse(cr, uid, attributes_ids, context=context)

        from_currency = pool.get('product.price.type')._get_field_currency(cr, uid, 'list_price', context)
        to_currency = pricelist.currency_id
        compute_currency = lambda price: pool['res.currency']._compute(cr, uid, from_currency, to_currency, price, context=context)

        values = {
            'search': search,
            'category': category,
            'attrib_values': attrib_values,
            'attrib_set': attrib_set,
            'pager': pager,
            'pricelist': pricelist,
            'products': products,
            'bins': table_compute().process(products),
            'rows': PPR,
            'styles': styles,
            'categories': categs,
            'attributes': attributes,
            'compute_currency': compute_currency,
            'keep': keep,
            'style_in_product': lambda style, product: style.id in [s.id for s in product.website_style_ids],
            'attrib_encode': lambda attribs: werkzeug.url_encode([('attrib',i) for i in attribs]),
            'form_values': post,
            'ingredient': request.env['product.ingredient'].browse(int(post.get('ingredient'))) if post.get('ingredient') else None,
        }
        return request.website.render("webshop_dermanord.products", values)

    @http.route([
        '/dn_list',
        '/dn_list/page/<int:page>',
    ], type='http', auth="public", website=True)
    def dn_list(self, page=0, category=None, search='', **post):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry

        domain = self._get_search_domain(search, category, None)
        domain += self.get_domain_append(post)

        keep = QueryURL('/dn_list', category=category and int(category), search=search, attrib=None)

        if not context.get('pricelist'):
            pricelist = self.get_pricelist()
            context['pricelist'] = int(pricelist)
        else:
            pricelist = pool.get('product.pricelist').browse(cr, uid, context['pricelist'], context)

        product_obj = pool.get('product.product')

        url = "/dn_list"
        product_count = product_obj.search_count(cr, uid, domain, context=context)
        if search:
            post["search"] = search
        pager = request.website.pager(url=url, total=product_count, page=page, step=PPG, scope=7, url_args=post)
        product_ids = product_obj.search(cr, uid, domain, limit=PPG, offset=pager['offset'], order=self._get_search_order(post), context=context)
        products = product_obj.browse(cr, uid, product_ids, context=context)

        from_currency = pool.get('product.price.type')._get_field_currency(cr, uid, 'list_price', context)
        to_currency = pricelist.currency_id
        compute_currency = lambda price: pool['res.currency']._compute(cr, uid, from_currency, to_currency, price, context=context)

        values = {
            'search': search,
            'pager': pager,
            'pricelist': pricelist,
            'products': products,
            'rows': PPR,
            'compute_currency': compute_currency,
            'keep': keep,
            'url': url,
            'form_values': post,
        }
        return request.website.render("webshop_dermanord.products_list_reseller_view", values)

    @http.route(['/shop/cart'], type='http', auth="public", website=True)
    def cart(self, **post):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        order = request.website.sale_get_order()
        if order:
            from_currency = pool.get('product.price.type')._get_field_currency(cr, uid, 'list_price', context)
            to_currency = order.pricelist_id.currency_id
            compute_currency = lambda price: pool['res.currency']._compute(cr, uid, from_currency, to_currency, price, context=context)
        else:
            compute_currency = lambda price: price

        values = {
            'order': order,
            'compute_currency': compute_currency,
            'suggested_products': [],
            'dn_list': post.get('dn_list') or None,
        }
        if order:
            _order = order
            if not context.get('pricelist'):
                _order = order.with_context(pricelist=order.pricelist_id.id)
            values['suggested_products'] = _order._cart_accessories()

        return request.website.render("website_sale.cart", values)

    @http.route(['/shop/cart/update'], type='http', auth="public", methods=['POST'], website=True)
    def cart_update(self, product_id, add_qty=1, set_qty=0, **kw):
        cr, uid, context = request.cr, request.uid, request.context
        request.website.sale_get_order(force_create=1)._cart_update(product_id=int(product_id), add_qty=float(add_qty), set_qty=float(set_qty))
        request.context.update({'dn_list': True})
        if kw.get('dn_list'):
            return request.redirect("/dn_list?dn_list=%s" %kw.get('dn_list'))
        return request.redirect("/shop/cart")


class webshop_dermanord(http.Controller):

    @http.route(['/dn_shop/search'], type='json', auth="public", website=True)
    def search(self, **kw):
        raise Warning(kw)
        return value

    @http.route(['/get/product_variant_data'], type='json', auth="public", website=True)
    def product_variant_data(self, product_id=None, **kw):
        value = {}
        if product_id:
            product = request.env['product.product'].browse(int(product_id))
            if product:
                value['image_id'] = product.image_ids[0].id if len(product.image_ids) > 0 else None
                value['ingredients'] = product.ingredients or ''
                value['use_desc'] = product.use_desc or ''
                value['reseller_desc'] = product.reseller_desc or ''
        return value

    @http.route(['/get/product_variant_value'], type='json', auth="public", website=True)
    def product_variant_value(self, product_id=None, value_id=None, **kw):
        if product_id and value_id:
            product = request.env['product.template'].browse(int(product_id))
            if product:
                variants = product.product_variant_ids.filtered(lambda v: int(value_id) in v.attribute_value_ids.mapped("id"))
                return variants[0].ingredients if len(variants) > 0 else ''
