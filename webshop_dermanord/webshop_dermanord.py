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
from openerp.tools.translate import _
from datetime import datetime, date, timedelta
from lxml import html
from openerp.addons.website_sale.controllers.main import website_sale, QueryURL, table_compute
from openerp.addons.website.models.website import slug
from openerp.addons.website_fts.website_fts import WebsiteFullTextSearch
import werkzeug
from heapq import nlargest
import math

import logging
_logger = logging.getLogger(__name__)

PPG = 21 # Products Per Page
PPR = 3  # Products Per Row

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

    mandatory_billing_fields = ["name", "phone", "email", "street", "city", "country_id"]

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
            for p in product.product_variant_ids.filtered(lambda v: v.sale_ok == True):
                price = currency_obj.compute(cr, uid, website_currency_id, currency_id, p.lst_price)
                attribute_value_ids.append([p.id, [v.id for v in p.attribute_value_ids if v.attribute_id.id in visible_attrs], p.price, price, p.recommended_price])
        else:
            attribute_value_ids = [[p.id, [v.id for v in p.attribute_value_ids if v.attribute_id.id in visible_attrs], p.price, p.lst_price, p.recommended_price] for p in product.sudo().product_variant_ids.filtered(lambda v: v.sale_ok == True)]

        return attribute_value_ids

    def get_domain_append(self, post):
        facet_ids = []
        category_ids = []
        ingredient_ids = []
        not_ingredient_ids = []
        current_ingredient = None
        current_ingredient_key = None

        for k, v in post.iteritems():
            if k.split('_')[0] == 'facet':
                if v:
                    facet_ids.append(int(v))
            if k.split('_')[0] == 'category':
                if v:
                     category_ids.append(int(v))
            if k.split('_')[0] == 'ingredient':
                if v:
                    ingredient_ids.append(int(v))
            if k.split('_')[0] == 'notingredient':
                if v:
                    not_ingredient_ids.append(int(v))
            if k == 'current_ingredient':
                if v:
                    current_ingredient = v
                    current_ingredient_key = 'ingredient_' + v
                    ingredient_ids.append(int(v))

        if current_ingredient:
            post['current_ingredient'] = int(current_ingredient)
            post[current_ingredient_key] = current_ingredient

        domain_append = []
        if category_ids:
            domain_append += [('public_categ_ids', 'in', [id for id in category_ids])]
        if facet_ids:
            product_ids = request.env['product.product'].search_read(
                [('facet_line_ids.value_ids', '=', id) for id in facet_ids], ['id'])
            domain_append.append(('product_variant_ids', 'in', [r['id'] for r in product_ids]))
        if ingredient_ids or not_ingredient_ids:
            product_ids = request.env['product.product'].search_read(
                [('ingredient_ids', '=', id) for id in ingredient_ids] + [('ingredient_ids', '!=', id) for id in not_ingredient_ids], ['id'])
            domain_append.append(('product_variant_ids', 'in', [r['id'] for r in product_ids]))

        return domain_append

    def get_form_values(self):
        if not request.session.get('form_values'):
            request.session['form_values'] = {}
        return request.session.get('form_values')

    def get_chosen_filter_qty(self, post):
        chosen_filter_qty = 0
        for k, v in post.iteritems():
            if k not in ['post_form', 'order']:
                chosen_filter_qty += 1
        return chosen_filter_qty

    def get_chosen_order(self, post):
        sort_name = 'sold_qty'
        sort_order = 'desc'
        for k, v in post.iteritems():
            if k == 'order':
                sort_name = post.get('order').split(' ')[0]
                sort_order = post.get('order').split(' ')[1]
                break
        return [sort_name, sort_order]

    def domain_current(self, model, domain, post):
        domain_current = []
        if 'current_offer' in post:
            campaign_product_ids = request.env[model].get_campaign_products(for_reseller=False).mapped('id')
            domain_current.append(('id', 'in', campaign_product_ids))
        if 'current_offer_reseller' in post:
            if request.env.user.partner_id.property_product_pricelist and request.env.user.partner_id.property_product_pricelist.for_reseller:
                campaign_product_reseller_ids = request.env[model].get_campaign_products(for_reseller=True).mapped('id')
                domain_current.append(('id', 'in', campaign_product_reseller_ids))
        if len(domain_current) > 1:
            for d in domain_current:
                if domain_current.index(d) != (len(domain_current)-1):
                    domain.append('|')
                domain.append(domain_current[domain_current.index(d)])
        if len(domain_current) == 1:
            domain.append(domain_current[0])
        return domain


    @http.route([
        '/dn_shop',
        '/dn_shop/page/<int:page>',
        '/dn_shop/category/<model("product.public.category"):category>',
        '/dn_shop/category/<model("product.public.category"):category>/page/<int:page>',
    ], type='http', auth="public", website=True)
    def dn_shop(self, page=0, category=None, search='', **post):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry

        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [map(int, v.split("-")) for v in attrib_list if v]
        attrib_set = set([v[1] for v in attrib_values])
        domain = self._get_search_domain(search, category, attrib_values)
        domain += self.get_domain_append(post)
        #~ if category:
        domain += self.get_domain_append(self.get_form_values())
        product_obj = pool.get('product.template')

        domain = self.domain_current('product.template', domain, post)

        request.session['current_domain'] = domain

        if category:
            if not request.session.get('form_values'):
                request.session['form_values'] = {'category_%s' %int(category): '%s' %int(category)}
            for k,v in request.session.get('form_values').items():
                if 'category_' in k:
                    del request.session['form_values'][k]
                    request.session['form_values']['category_%s' %int(category)] = '%s' %int(category)

        keep = QueryURL('/dn_shop', category=category and int(category), search=search, attrib=attrib_list)

        if not context.get('pricelist'):
            pricelist = self.get_pricelist()
            context['pricelist'] = int(pricelist)
        else:
            pricelist = pool.get('product.pricelist').browse(cr, uid, context['pricelist'], context)

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
        default_order = self._get_search_order(post)
        request.session['current_order'] = self._get_search_order(post)
        if post.get('order'):
            default_order = post.get('order')
        product_ids = product_obj.search(cr, uid, domain, limit=PPG, offset=pager['offset'], order=default_order, context=context)
        products = product_obj.browse(cr, uid, product_ids, context=context)
        # relist which product templates the current user is allowed to see
        for p in products:
            if len(p.sudo().access_group_ids) > 0 :
                if request.env['res.users'].browse(uid) not in p.sudo().access_group_ids.mapped('users'):
                    products -= p

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

        if post.get('post_form') and post.get('post_form') == 'ok':
            request.session['form_values'] = post
        if category:
            self.get_form_values()['category_' + str(int(category))] = str(int(category))
        request.session['url'] = url
        request.session['chosen_filter_qty'] = self.get_chosen_filter_qty(self.get_form_values())
        request.session['sort_name'] = self.get_chosen_order(self.get_form_values())[0]
        request.session['sort_order'] = self.get_chosen_order(self.get_form_values())[1]

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
            'url': url,
            'style_in_product': lambda style, product: style.id in [s.id for s in product.website_style_ids],
            'attrib_encode': lambda attribs: werkzeug.url_encode([('attrib',i) for i in attribs]),
            'current_ingredient': request.env['product.ingredient'].browse(post.get('current_ingredient')),
            'shop_footer': True,
        }
        #~ re = request.render("webshop_dermanord.products", values)
        #~ _logger.warn(re.render())
        #~ view_obj = request.env["ir.ui.view"]
        #~ res = request.env['ir.qweb'].render("webshop_dermanord.products", values, loader=view_obj.loader("webshop_dermanord.products"))
        #~ _logger.warn(re)
        return request.website.render("webshop_dermanord.products", values)

    @http.route(['/dn_shop_json_grid'], type='json', auth='public', website=True)
    def dn_shop_json_grid(self, page=0, **kw):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry

        if not context.get('pricelist'):
            pricelist = self.get_pricelist()
            context['pricelist'] = int(pricelist)
        else:
            pricelist = pool.get('product.pricelist').browse(cr, uid, context['pricelist'], context)

        product_obj = pool.get('product.template')
        url = "/dn_shop"

        domain = request.session.get('current_domain')
        order = request.session.get('current_order')

        product_count = product_obj.search_count(cr, uid, domain, context=context)
        page_count = int(math.ceil(float(product_count) / float(PPG)))
        pager = request.website.pager(url=url, total=product_count, page=page, step=PPG, scope=7, url_args=None)
        product_ids = product_obj.search(cr, uid, domain, limit=PPG, offset=pager['offset'], order=order, context=context)
        products = product_obj.browse(cr, uid, product_ids, context=context)
        # relist which product templates the current user is allowed to see
        for p in products:
            if len(p.sudo().access_group_ids) > 0 :
                if request.env['res.users'].browse(uid) not in p.sudo().access_group_ids.mapped('users'):
                    products -= p

        from_currency = pool.get('product.price.type')._get_field_currency(cr, uid, 'list_price', context)
        to_currency = pricelist.currency_id
        compute_currency = lambda price: pool['res.currency']._compute(cr, uid, from_currency, to_currency, price, context=context)

        products_list = []
        for product in products:
            image_src = ''
            is_reseller = False
            currency = ''
            if len(product.image_ids) > 0:
                image_src = '/imagefield/base_multi_image.image/file_db_store/%s/ref/%s' %(product.image_ids[0].id, 'snippet_dermanord.img_product')
            elif len(product.image_ids) == 0:
                image_src = request.website.image_url(product, 'image', '300x300')
            partner_pricelist = request.env.user.partner_id.property_product_pricelist
            if partner_pricelist:
                currency = partner_pricelist.currency_id.name
                if partner_pricelist.for_reseller:
                    is_reseller = True
            products_list.append({
                'product_href': '/dn_shop/product/%s' %product.id,
                'product_name': product.name,
                'product_img_src': image_src,
                'price': "%.2f" % product.price,
                'price_tax': "%.2f" % product.price_tax,
                'list_price_tax': "%.2f" % product.list_price_tax,
                'currency': currency,
                'rounding': request.website.pricelist_id.currency_id.rounding,
                'is_reseller': 'yes' if is_reseller else 'no',
                'default_code': product.default_code or '',
                'description_sale': product.description_sale or '',
                'product_variant_ids': True if product.product_variant_ids else False,
            })

        values = {
            'products': products_list,
            'url': url,
            'page_count': page_count,
        }

        return values

    @http.route(['/dn_shop_json_list'], type='json', auth='public', website=True)
    def dn_shop_json_list(self, page=0, **kw):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry

        if not context.get('pricelist'):
            pricelist = self.get_pricelist()
            context['pricelist'] = int(pricelist)
        else:
            pricelist = pool.get('product.pricelist').browse(cr, uid, context['pricelist'], context)

        product_obj = pool.get('product.product')
        url = "/dn_list"

        domain = request.session.get('current_domain')
        order = request.session.get('current_order')

        product_count = product_obj.search_count(cr, uid, domain, context=context)
        page_count = int(math.ceil(float(product_count) / float(PPG)))
        pager = request.website.pager(url=url, total=product_count, page=page, step=PPG, scope=7, url_args=None)
        product_ids = product_obj.search(cr, uid, domain, limit=PPG, offset=pager['offset'], order=order, context=context)
        products = product_obj.browse(cr, uid, product_ids, context=context)
        # relist which product templates the current user is allowed to see
        for p in products:
            if len(p.sudo().access_group_ids) > 0 :
                if request.env['res.users'].browse(uid) not in p.sudo().access_group_ids.mapped('users'):
                    products -= p

        from_currency = pool.get('product.price.type')._get_field_currency(cr, uid, 'list_price', context)
        to_currency = pricelist.currency_id
        compute_currency = lambda price: pool['res.currency']._compute(cr, uid, from_currency, to_currency, price, context=context)

        products_list = []
        for product in products:
            is_reseller = False
            currency = ''
            partner_pricelist = request.env.user.partner_id.property_product_pricelist
            if partner_pricelist:
                currency = partner_pricelist.currency_id.name
                if partner_pricelist.for_reseller:
                    is_reseller = True
            attributes = product.attribute_value_ids.mapped('name')
            products_list.append({
                'variant_id': product.id,
                'product_href': '/dn_shop/variant/%s' %product.id,
                'product_name': product.name,
                'price': "%.2f" % product.price,
                'currency': currency,
                'rounding': request.website.pricelist_id.currency_id.rounding,
                'is_reseller': 'yes' if is_reseller else 'no',
                'default_code': product.default_code or '',
                'attribute_value_ids': (' , ' + ' , '.join(attributes)) if len(attributes) > 0 else '',
            })

        values = {
            'products': products_list,
            'url': url,
            'page_count': page_count,
        }

        return values

    @http.route(['/dn_shop/product/<model("product.template"):product>'], type='http', auth="public", website=True)
    def dn_product(self, product, category='', search='', **kwargs):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        category_obj = pool['product.public.category']
        template_obj = pool['product.template']

        context.update(active_id=product.id)

        if category:
            category = category_obj.browse(cr, uid, int(category), context=context)
            category = category if category.exists() else False

        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [map(int,v.split("-")) for v in attrib_list if v]
        attrib_set = set([v[1] for v in attrib_values])

        keep = QueryURL('/dn_shop', category=category and category.id, search=search, attrib=attrib_list)

        category_ids = category_obj.search(cr, uid, [], context=context)
        category_list = category_obj.name_get(cr, uid, category_ids, context=context)
        category_list = sorted(category_list, key=lambda category: category[1])

        pricelist = self.get_pricelist()

        from_currency = pool.get('product.price.type')._get_field_currency(cr, uid, 'list_price', context)
        to_currency = pricelist.currency_id
        compute_currency = lambda price: pool['res.currency']._compute(cr, uid, from_currency, to_currency, price, context=context)

        if not context.get('pricelist'):
            context['pricelist'] = int(self.get_pricelist())
            product = template_obj.browse(cr, uid, int(product), context=context)

        request.session['chosen_filter_qty'] = self.get_chosen_filter_qty(self.get_form_values())
        request.session['sort_name'] = self.get_chosen_order(self.get_form_values())[0]
        request.session['sort_order'] = self.get_chosen_order(self.get_form_values())[1]

        values = {
            'search': search,
            'category': category,
            'pricelist': pricelist,
            'attrib_values': attrib_values,
            'compute_currency': compute_currency,
            'attrib_set': attrib_set,
            'keep': keep,
            'url': request.session.get('url'),
            'category_list': category_list,
            'main_object': product,
            'product': product,
            'get_attribute_value_ids': self.get_attribute_value_ids,
            'shop_footer': True,
        }
        return request.website.render("website_sale.product", values)

    #controller only for reseller
    @http.route([
        '/dn_list',
        '/dn_list/page/<int:page>',
        '/dn_list/category/<model("product.public.category"):category>',
        '/dn_list/category/<model("product.public.category"):category>/page/<int:page>',
    ], type='http', auth="public", website=True)
    def dn_list(self, page=0, category=None, search='', **post):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        domain = self._get_search_domain(search, category, None)
        domain += self.get_domain_append(post)
        #~ if category:
        domain += self.get_domain_append(self.get_form_values())
        product_obj = pool.get('product.product')

        domain = self.domain_current('product.product', domain, post)

        request.session['current_domain'] = domain

        if category:
            if not request.session.get('form_values'):
                request.session['form_values'] = {'category_%s' %int(category): '%s' %int(category)}
            for k,v in request.session.get('form_values').items():
                if 'category_' in k:
                    del request.session['form_values'][k]
                    request.session['form_values']['category_%s' %int(category)] = '%s' %int(category)

        keep = QueryURL('/dn_list', category=category and int(category), search=search, attrib=None)

        if not context.get('pricelist'):
            pricelist = self.get_pricelist()
            context['pricelist'] = int(pricelist)
        else:
            pricelist = pool.get('product.pricelist').browse(cr, uid, context['pricelist'], context)

        url = "/dn_list"
        product_count = product_obj.search_count(cr, uid, domain, context=context)
        if search:
            post["search"] = search
        pager = request.website.pager(url=url, total=product_count, page=page, step=PPG, scope=7, url_args=post)
        default_order = self._get_search_order(post)
        if post.get('order'):
            default_order = post.get('order')
        product_ids = product_obj.search(cr, uid, domain, limit=PPG, offset=pager['offset'], order=default_order, context=context)
        products = product_obj.browse(cr, uid, product_ids, context=context)
        # relist which product templates the current user is allowed to see
        for p in products:
            if len(p.sudo().access_group_ids) > 0 :
                if request.env['res.users'].browse(uid) not in p.sudo().access_group_ids.mapped('users'):
                    products -= p

        from_currency = pool.get('product.price.type')._get_field_currency(cr, uid, 'list_price', context)
        to_currency = pricelist.currency_id
        compute_currency = lambda price: pool['res.currency']._compute(cr, uid, from_currency, to_currency, price, context=context)

        if post.get('post_form') and post.get('post_form') == 'ok':
            request.session['form_values'] = post
        if category:
            self.get_form_values()['category_' + str(int(category))] = str(int(category))
        request.session['url'] = url
        request.session['chosen_filter_qty'] = self.get_chosen_filter_qty(self.get_form_values())
        request.session['sort_name'] = self.get_chosen_order(self.get_form_values())[0]
        request.session['sort_order'] = self.get_chosen_order(self.get_form_values())[1]

        values = {
            'search': search,
            'pager': pager,
            'pricelist': pricelist,
            'products': products,
            'rows': PPR,
            'compute_currency': compute_currency,
            'keep': keep,
            'url': url,
            'current_ingredient': request.env['product.ingredient'].browse(post.get('current_ingredient')),
            'shop_footer': True,
        }
        return request.website.render("webshop_dermanord.products_list_reseller_view", values)

    @http.route([
        '/dn_shop/variant/<model("product.product"):variant>'
    ], type='http', auth="public", website=True)
    def dn_product_variant(self, variant, category='', search='', **kwargs):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        category_obj = pool['product.public.category']
        template_obj = pool['product.template']

        context.update(active_id=variant.product_tmpl_id.id)

        if category:
            category = category_obj.browse(cr, uid, int(category), context=context)
            category = category if category.exists() else False

        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [map(int,v.split("-")) for v in attrib_list if v]
        attrib_set = set([v[1] for v in attrib_values])

        keep = QueryURL('/dn_shop', category=category and category.id, search=search, attrib=attrib_list)

        category_ids = category_obj.search(cr, uid, [], context=context)
        category_list = category_obj.name_get(cr, uid, category_ids, context=context)
        category_list = sorted(category_list, key=lambda category: category[1])

        pricelist = self.get_pricelist()

        from_currency = pool.get('product.price.type')._get_field_currency(cr, uid, 'list_price', context)
        to_currency = pricelist.currency_id
        compute_currency = lambda price: pool['res.currency']._compute(cr, uid, from_currency, to_currency, price, context=context)

        if not context.get('pricelist'):
            context['pricelist'] = int(self.get_pricelist())
            product = template_obj.browse(cr, uid, variant.product_tmpl_id.id, context=context)

        request.session['chosen_filter_qty'] = self.get_chosen_filter_qty(self.get_form_values())
        request.session['sort_name'] = self.get_chosen_order(self.get_form_values())[0]
        request.session['sort_order'] = self.get_chosen_order(self.get_form_values())[1]

        values = {
            'search': search,
            'category': category,
            'pricelist': pricelist,
            'attrib_values': attrib_values,
            'compute_currency': compute_currency,
            'attrib_set': attrib_set,
            'keep': keep,
            'url': request.session.get('url'),
            'category_list': category_list,
            'main_object': product,
            'product': product,
            'product_product': variant,
            'get_attribute_value_ids': self.get_attribute_value_ids,
            'shop_footer': True,
        }
        return request.website.render("website_sale.product", values)

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
            'url': request.session.get('url'),
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
        request.website.with_context(supress_checks=True).sale_get_order(force_create=1)._cart_update(product_id=int(product_id), add_qty=float(add_qty), set_qty=float(set_qty))
        if kw.get('return_url'):
            return request.redirect(kw.get('return_url'))
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
                value['default_code'] = product.default_code or ''
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


class WebsiteFullTextSearch(WebsiteFullTextSearch):

    @http.route(['/search_suggestion'], type='json', auth="public", website=True)
    def search_suggestion(self, search='', facet=None, res_model=None, limit=0, offset=0, **kw):
        result = request.env['fts.fts'].term_search(search, facet, res_model, limit, offset)
        result_list = result['terms']
        rl = []
        i = 0
        while i < len(result_list) and len(rl) < 5:
            r = result_list[i]
            try:
                if r.model_record._name == 'product.public.category':
                    rl.append({
                        'res_id': r.res_id,
                        'model_record': r.model_record._name,
                        'name': r.model_record.name,
                    })
                elif r.model_record._name == 'product.template':
                    if len(r.model_record.sudo().access_group_ids) == 0 or (len(r.model_record.sudo().access_group_ids) > 0 and request.env.user in r.model_record.sudo().access_group_ids.mapped('users')):
                        rl.append({
                            'res_id': r.res_id,
                            'model_record': r.model_record._name,
                            'name': r.model_record.name,
                        })
                elif r.model_record._name == 'product.product':
                    if len(r.model_record.sudo().access_group_ids) == 0 or (len(r.model_record.sudo().access_group_ids) > 0 and request.env.user in r.model_record.sudo().access_group_ids.mapped('users')):
                        rl.append({
                            'res_id': r.res_id,
                            'model_record': r.model_record._name,
                            'name': r.model_record.name,
                            'product_tmpl_id': r.model_record.product_tmpl_id.id,
                        })
                elif r.model_record._name == 'blog.post':
                    rl.append({
                        'res_id': r.res_id,
                        'model_record': r.model_record._name,
                        'name': r.model_record.name,
                        'blog_id': r.model_record.blog_id.id,
                    })
                elif r.model_record._name == 'product.facet.line':
                    rl.append({
                        'res_id': r.res_id,
                        'model_record': r.model_record._name,
                        'product_tmpl_id': r.model_record.product_tmpl_id.id,
                        'product_name': r.model_record.product_tmpl_id.name,
                    })
            except:
                pass
            i += 1
        return rl
