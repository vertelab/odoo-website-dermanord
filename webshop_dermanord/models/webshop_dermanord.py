# -*- coding: utf-8 -*-
##############################################################################
#
# odoo, Open Source Management Solution, third party addon
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

from odoo import models, fields, api, _
from odoo import http
from odoo.http import request
from odoo.tools.translate import _
from odoo.tools import html_escape as escape
from odoo.tools import float_compare
from odoo.exceptions import except_orm
from datetime import datetime, date, timedelta
from lxml import html
import odoo.addons.decimal_precision as decpre
import werkzeug
from heapq import nlargest
import math
import time
from multiprocessing import Lock
import sys, traceback
from odoo.api import Environment
from odoo.addons.website_sale.controllers.main import WebsiteSale, QueryURL, TableCompute
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.website.models.ir_http import sitemap_qs2dom

import logging
_logger = logging.getLogger(__name__)

# import xlsxwriter

from odoo import SUPERUSER_ID


import logging
_logger = logging.getLogger(__name__)

PPG = 21 # Products Per Page
PPR = 3  # Products Per Row


class product_template(models.Model):
    _inherit = 'product.template'

    # ~ def _blog_post_ids(self):
        # ~ if type(self.id) is int:
            # ~ blog_posts = self.env['blog.post'].search_read(['&', ('website_published', '=', True),'|', ('product_tmpl_ids', 'in', self.id), ('product_public_categ_ids', 'in', self.public_categ_ids.mapped('id'))],['id'])
            # ~ self.blog_post_ids = [(6, 0, [p['id'] for p in blog_posts])]
            # ~ #~ self.blog_post_ids = [(6, 0, blog_posts.filtered(lambda b: b.website_published == True).mapped('id'))]
    # ~ blog_post_ids = fields.Many2many(comodel_name='blog.post', string='Posts', compute='_blog_post_ids')
    sold_qty = fields.Integer(string='Sold', default=0)
    use_tmpl_name = fields.Boolean(string='Use Template Name', help='When checked. The template name will be used in webshop')
    # ~ campaign_changed = fields.Boolean()

    # ~ def _auto_init(self, cr, context=None):
        # ~ """Install custom sorting functions."""
        # ~ res = super(product_template, self)._auto_init(cr, context)
        # ~ cr.execute("""CREATE OR REPLACE FUNCTION dn_product_template_price_chart_sort(int, int) RETURNS float
# ~ LANGUAGE sql
# ~ AS
# ~ $$

    # ~ SELECT price FROM product_pricelist_chart WHERE pricelist_chart_id = $2 AND product_id IN (SELECT id FROM product_product WHERE product_tmpl_id = $1 AND sale_ok = true and active = true AND website_published = true) ORDER BY price LIMIT 1;
# ~ $$;""")
        # ~ return res

    # ~ def _generate_order_by_inner(self, alias, order_spec, query, reverse_direction=False, seen=None):
        # ~ """Handle sort by functions.
        # ~ dn_price_chart_sort_{pricelist_chart_id} = sort by prices for the given chart.
        # ~ """
        # ~ if seen is None:
            # ~ seen = set()
        # ~ order_by_elements = []
        # ~ special_order = []
        # ~ if 'dn_price_chart_sort_' in order_spec:
            # ~ new_order = []
            # ~ for expr in order_spec.split(','):
                # ~ if 'dn_price_chart_sort_' in expr:
                    # ~ expr = expr.strip().split(' ')
                    # ~ order_direction = expr[1].strip().upper() if len(expr) == 2 else ''
                    # ~ chart_id = expr[0].split('_')[-1]
                    # ~ if not chart_id.isdigit() and order_direction in ('', 'ASC', 'DESC'):
                        # ~ raise except_orm(_('AccessError'), _('Invalid "order" specified for dn_price_chart_sort_'))
                    # ~ special_order.append((chart_id, order_direction))
                # ~ else:
                    # ~ new_order.append(expr.strip())
            # ~ order_spec = ','.join(new_order)
        # ~ if order_spec:
            # ~ order_by_elements = super(product_template, self)._generate_order_by_inner(alias, order_spec, query, reverse_direction=reverse_direction, seen=seen)

        # ~ for order in special_order:
            # ~ order_by_elements.append('dn_product_template_price_chart_sort("%s"."id", %s) %s' % (alias, order[0], order[1]))
        # ~ return order_by_elements

    
    # ~ def get_default_variant(self):
        # ~ self.ensure_one()
        # ~ variants = self.product_variant_ids.filtered(lambda v: self.env.ref('website_sale.image_promo') in v.website_style_ids_variant)
        # ~ if len(variants) > 0:
            # ~ vs = variants.filtered(lambda v: v.check_access_group(self.env.user))
            # ~ return vs[0] if len(vs) > 0 else super(product_template, self).get_default_variant()
        # ~ else:
            # ~ return super(product_template, self).get_default_variant()

    # ~ # get defualt variant ribbon. if there's not one, get the template's ribbon
    
    # ~ def Xget_default_variant_ribbon(self):
        # ~ if self.get_default_variant() and len(self.get_default_variant().website_style_ids_variant) > 0:
            # ~ return ' '.join([s.html_class for s in self.get_default_variant().website_style_ids_variant])
        # ~ else:
            # ~ return ' '.join([s.html_class for s in self.website_style_ids])

    
    # ~ def format_facets(self,facet):
        # ~ self.ensure_one()
        # ~ values = []
        # ~ for value in self.facet_line_ids.mapped('value_ids') & facet.value_ids:
            # ~ values.append(u'<a t-att-href="{href}" class="text-muted"><span>{value_name}</span></a>'.format(
                # ~ href='/dn_shop/?facet_%s_%s=%s%s' %(facet.id, value.id, value.id, (u'&amp;%s' %'&amp;'.join([u'category_%s=%s' %(c.id, c.id) for c in self.public_categ_ids]) if len(self.public_categ_ids) > 0 else '')),
                # ~ value_name=value.name))
        # ~ return ', '.join(values)


    
    # ~ def fts_search_suggestion(self):
        # ~ """
        # ~ Return a search result for search_suggestion.
        # ~ """
        # ~ res = super(product_template, self).fts_search_suggestion()
        # ~ res['event_type_id'] = self.event_type_id and self.event_type_id.id or False
        # ~ return res

class ProductProduct(models.Model):
    _inherit = 'product.product'

    #~ so_line_ids = fields.One2many(comodel_name='sale.order.line', inverse_name='product_id')  # performance hog, do we need it?
    sold_qty = fields.Integer(string='Sold', default=0)
    website_style_ids_variant = fields.Many2many(comodel_name='product.style', string='Styles for Variant')
    has_tester = fields.Boolean(string='Has Tester')
    tester_product_id = fields.Many2one(comodel_name='product.product', string='Tester Product')
    tester_min = fields.Float(string='Minimum Quantity', default=6)
    width = fields.Float('Width (cm)', digits_compute= decpre.get_precision('Product Unit of Measure'), help='Product width in cm')
    height = fields.Float('Height (cm)', digits_compute= decpre.get_precision('Product Unit of Measure'), help='Product height in cm')
    depth = fields.Float('Depth (cm)', digits_compute= decpre.get_precision('Product Unit of Measure'), help='Product depth in cm')

    def _fullname(self):
        self.fullname = '%s %s' % (self.name, ', '.join(self.product_template_attribute_value_ids.mapped('name')))
    fullname = fields.Char(compute='_fullname')

    # ~ def _auto_init(self, cr, context=None):
        # ~ """Install custom sorting functions."""
        # ~ res = super(ProductProduct, self)._auto_init(cr, context)
        # ~ cr.execute("""CREATE OR REPLACE FUNCTION dn_product_product_price_chart_sort(int, int) RETURNS float
# ~ LANGUAGE sql
# ~ AS
# ~ $$
    # ~ SELECT price FROM product_pricelist_chart WHERE pricelist_chart_id = $2 AND product_id = $1 LIMIT 1;
# ~ $$;""")
        # ~ return res

    # ~ def _generate_order_by_inner(self, alias, order_spec, query, reverse_direction=False, seen=None):
        # ~ """Handle sort by functions.
        # ~ dn_price_chart_sort_{pricelist_chart_type_id} = sort by prices for the given chart.
        # ~ """
        # ~ if seen is None:
            # ~ seen = set()
        # ~ order_by_elements = []
        # ~ special_order = []
        # ~ if 'dn_price_chart_sort_' in order_spec:
            # ~ new_order = []
            # ~ for expr in order_spec.split(','):
                # ~ if 'dn_price_chart_sort_' in expr:
                    # ~ expr = expr.strip().split(' ')
                    # ~ order_direction = expr[1].strip().upper() if len(expr) == 2 else ''
                    # ~ chart_id = expr[0].split('_')[-1]
                    # ~ if not chart_id.isdigit() and order_direction in ('', 'ASC', 'DESC'):
                        # ~ raise except_orm(_('AccessError'), _('Invalid "order" specified for dn_price_chart_sort_'))
                    # ~ special_order.append((chart_id, order_direction))
                # ~ else:
                    # ~ new_order.append(expr.strip())
            # ~ order_spec = ','.join(new_order)
        # ~ if order_spec:
            # ~ order_by_elements = super(ProductProduct, self)._generate_order_by_inner(alias, order_spec, query, reverse_direction=reverse_direction, seen=seen)

        # ~ for order in special_order:
            # ~ order_by_elements.append('dn_product_product_price_chart_sort("%s"."id", %s) %s' % (alias, order[0], order[1]))
        # ~ return order_by_elements

    # ~ @api.model
    # ~ def update_sold_qty(self):
        # ~ self._cr.execute('UPDATE product_template SET sold_qty = 0')
        # ~ self._cr.execute('UPDATE product_product SET sold_qty = 0')
        # ~ so_lines = self.env['sale.order'].search([('date_confirm', '>', fields.Date.to_string(date.today() - timedelta(days=30)))]).mapped('order_line').filtered(lambda l : l.state in ['confirmed', 'done'])
        # ~ templates = []
        # ~ products = {}
        # ~ if len(so_lines) > 0:
            # ~ for line in so_lines:
                # ~ if products.get(line.product_id):
                    # ~ products[line.product_id] += sum(line.mapped('product_uom_qty'))
                # ~ else:
                    # ~ products[line.product_id] = sum(line.mapped('product_uom_qty'))
            # ~ for k, v in products.iteritems():
                # ~ k.sold_qty = v
                # ~ if k.product_tmpl_id not in templates:
                    # ~ templates.append(k.product_tmpl_id)
            # ~ for template in templates:
                # ~ template.sold_qty = sum(template.product_variant_ids.mapped('sold_qty'))
        # ~ return None


    
    # ~ def fts_search_suggestion(self):
        # ~ """
        # ~ Return a search result for search_suggestion.
        # ~ """
        # ~ res = super(ProductProduct, self).fts_search_suggestion()
        # ~ res['event_type_id'] = self.event_type_id and self.event_type_id.id or False
        # ~ return res
        
        # ~ '/webshop',
        # ~ '/webshop/category/<model("product.public.category"):category>',
        # ~ '/webshop/preset/<string:preset>',
        
class WebsiteSaleDermanord(WebsiteSale):
    
    # ~ def sitemap_shop(env, rule, qs):
        # ~ if not qs or qs.lower() in '/shop':
            # ~ yield {'loc': '/shop'}

        # ~ Category = env['product.public.category']
        # ~ dom = sitemap_qs2dom(qs, '/shop/category', Category._rec_name)
        # ~ dom += env['website'].get_current_website().website_domain()
        # ~ for cat in Category.search(dom):
            # ~ loc = '/shop/category/%s' % slug(cat)
            # ~ if not qs or qs.lower() in loc:
                # ~ yield {'loc': loc}
                
    @http.route([
        '/dn_shop',
        '/dn_shop/page/<int:page>',
        '/dn_shop/category/<model("product.public.category"):category>',
        '/dn_shop/category/<model("product.public.category"):category>/page/<int:page>',
    ], type='http', auth="public", website=True)
    def dn_shop(self, page=0, category=None, search='', **post):

        url = "/dn_shop"
        request.website.dn_shop_set_session('product.template', post, url)

        if category:
            if not request.session.get('form_values'):
                request.session['form_values'] = {'category_%s' %int(category): int(category)}
            request.session['form_values'] = {'category_%s' %int(category): int(category)}
            request.website.get_form_values()['category_' + str(int(category))] = int(category)
            request.session['current_domain'] = [('public_categ_ids', 'in', [int(category)])]
            request.session['chosen_filter_qty'] = request.website.get_chosen_filter_qty(request.website.get_form_values())

        if not request.context.get('pricelist'):
            request.context['pricelist'] = int(self.get_pricelist())
        if search:
            post["search"] = search

        # ~ category_obj = pool['product.public.category']
        # ~ category_ids = category_obj.search(cr, uid, [('parent_id', '=', False)], context=context)
        # ~ categs = category_obj.browse(cr, uid, category_ids, context=context)

        # ~ attributes_obj = request.registry['product.attribute']
        # ~ attributes_ids = attributes_obj.search(cr, uid, [], context=context)
        # ~ attributes = attributes_obj.browse(cr, uid, attributes_ids, context=context)
        domain = request.session.get('current_domain')
        limit=PPG
        order=request.session.get('current_order')
        offset = 0

        user = request.env['res.users'].browse(request.uid)

        _logger.warn('Anders x domain --------> %s limit %s order %s offset %s' % (domain, limit, order,offset))
        _logger.warn('Anders x search --------> %s  ' % (len(request.env['product.template'].sudo(user).search([],limit=1,order='name'))))
        _logger.warn('Anders x user --------> %s user %s %s %s ' % (request.env.ref('base.public_user'),request.env.user,request.uid,user))

        no_product_message = ''
        products=request.env['product.template'].sudo(user).get_thumbnail_default_variant(request.session.get('current_domain'),request.context['pricelist'],limit=PPG, order=request.session.get('current_order'))

        if len(products) == 0:
            no_product_message = _('Your filtering did not match any results. Please choose something else and try again.')
        # ~ price_data = request.website.get_price_fields(partner_pricelist)

        return request.website.render("webshop_dermanord.products", {
            'search': search,
            'category': category,
            # ~ 'pricelist': pricelist,
            'products':  products,
            'rows': PPR,
            # ~ 'styles': styles,
            # ~ 'categories': categs,
            # ~ 'attributes': attributes,
            'is_reseller': request.env.user.partner_id.property_product_pricelist.for_reseller,
            'url': url,
            'webshop_type': 'dn_shop',
            'current_ingredient': request.env['product.ingredient'].browse(int(post.get('current_ingredient', 0) or 0) or int(request.session.get('current_ingredient', 0) or 0)),
            'shop_footer': True,
            'page_lang': request.env.lang,
            'no_product_message': no_product_message,
            'all_products_loaded': True if len(products) < PPG else False,
        })
        
    @http.route(['/dn_shop_json_grid'], type='json', auth='public', website=True)
    def dn_shop_json_grid(self, page=0, **kw):
        if not request.context.get('pricelist'):
            request.context['pricelist'] = int(self.get_pricelist())
        values = {
            'products': request.env['product.template'].get_thumbnail_default_variant(
                request.session.get('current_domain'),
                request.context['pricelist'],
                order=request.session.get('current_order'),
                limit=6, offset=PPG+int(page)*6),
        }
        return values

    @http.route(['/dn_shop_json_list'], type='json', auth='public', website=True)
    def dn_shop_json_list(self, page=0, **kw):
        if not request.context.get('pricelist'):
            request.context['pricelist'] = int(self.get_pricelist())
        values = {
            'products': request.env['product.product'].get_list_row(request.session.get('current_domain'), request.context['pricelist'], order=request.session.get('current_order'), limit=10, offset=PPG+page*10),
        }
        return values
        
    @http.route(['/dn_shop/product/<model("product.template"):product>'], type='http', auth="public", website=True)
    def dn_product(self, product, category='', search='', **post):
        if len(product.product_variant_ids) == 0:
            user = request.env.user
            if not user:
                user = request.env['res.users'].with_context(active_test=False).browse(request.env.uid).sudo()
            _logger.warn('Product: %s (%s) has no variants for current user: %s' %(product.name, product.id, user.login))
            subject = u'Felaktig konfiguration av %s' % product.name
            body = u'Användaren %s (%s) får ej se några varianter på produkt %s (%s).' % (user.login, user.id, product.name, product.id)
            body += u'Access Groups: %s' % ', '.join(user.commercial_partner_id.access_group_ids.mapped('name'))
            author = request.env.ref('base.partner_root').sudo()
            request.env['mail.message'].sudo().create({
                'subject': subject,
                'body': body,
                'author_id': author.id,
                'res_id': product.id,
                'model': product._name,
                'type': 'notification',
                'partner_ids': [(4, pid) for pid in product.message_follower_ids.mapped('id')],
            })
            request.env['mail.mail'].sudo().create({
                'subject': subject,
                'body_html': body,
                'author_id': author.id,
                'email_from': author.email,
                'type': 'email',
                'auto_delete': True,
                'email_to': 'support@dermanord.se',
            })
            html = request.website._render(
                'website.404',
                {
                    'dn_404_message': _("You are not allowed to see this product."),
                    'status_code': 404,
                    'status_message': werkzeug.http.HTTP_STATUS_CODES[404]
                })
            return werkzeug.wrappers.Response(html, status=404, content_type='text/html;charset=utf-8')
        values = {
            'url': request.session.get('url'),
            'product': product.get_default_variant() or product.product_variant_ids[0],
            'detail': request.env['product.product'].get_product_detail(product, product.get_default_variant().id or product.product_variant_ids[0].id),
            'additional_title': product.name.upper(),
            'shop_footer': True,
        }
        return request.website.render("webshop_dermanord.product_detail_view", values)
        
    @http.route([
        '/dn_shop/variant/<model("product.product"):variant>'
    ], type='http', auth="public", website=True)
    def dn_product_variant(self, variant, category='', search='', **post):
        if not request.env.user:
            return request.redirect(request.httprequest.path)
        product = variant.sudo().product_tmpl_id #5509 variant: 5575
        values = {
            'url': request.session.get('url'), #None
            'product': variant,
            'detail': request.env['product.product'].get_product_detail(product, variant.id),
            'additional_title': variant.name.upper(),
            'shop_footer': True,
        }
        return request.website.render("webshop_dermanord.product_detail_view", values)


    @http.route([
    '''/webshop''',
    '''/webshop/page/<int:page>''',
    '''/webshop/category/<model("product.public.category"):category>''',
    '''/webshop/category/<model("product.public.category"):category>/page/<int:page>''',
    '''/webshop/preset/<string:preset>''',
    ], type='http', auth="public", website=True, sitemap=WebsiteSale.sitemap_shop)
    def webshop(self, page=0, category=None, search='', ppg=False, **post):
        _logger.warning("victor it uses my /shop wooo!"*99)
        _logger.warning(f"victor request: {request}")
        add_qty = int(post.get('add_qty', 1))
        Category = request.env['product.public.category']
        if category:
            category = Category.search([('id', '=', int(category))], limit=1)
            if not category or not category.can_access_from_current_website():
                raise NotFound()
        else:
            category = Category

        if ppg:
            try:
                ppg = int(ppg)
                post['ppg'] = ppg
            except ValueError:
                ppg = False
        if not ppg:
            ppg = request.env['website'].get_current_website().shop_ppg or 20

        ppr = request.env['website'].get_current_website().shop_ppr or 4

        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [[int(x) for x in v.split("-")] for v in attrib_list if v]
        attributes_ids = {v[0] for v in attrib_values}
        attrib_set = {v[1] for v in attrib_values}

        domain = self._get_search_domain(search, category, attrib_values)

        keep = QueryURL('/shop', category=category and int(category), search=search, attrib=attrib_list, order=post.get('order'))

        pricelist_context, pricelist = self._get_pricelist_context()

        request.context = dict(request.context, pricelist=pricelist.id, partner=request.env.user.partner_id)

        url = "/shop"
        if search:
            post["search"] = search
        if attrib_list:
            post['attrib'] = attrib_list

        Product = request.env['product.template'].with_context(bin_size=True)

        search_product = Product.search(domain, order=self._get_search_order(post))
        website_domain = request.website.website_domain()
        categs_domain = [('parent_id', '=', False)] + website_domain
        if search:
            search_categories = Category.search([('product_tmpl_ids', 'in', search_product.ids)] + website_domain).parents_and_self
            categs_domain.append(('id', 'in', search_categories.ids))
        else:
            search_categories = Category
        categs = Category.search(categs_domain)

        if category:
            url = "/shop/category/%s" % slug(category)

        product_count = len(search_product)
        pager = request.website.pager(url=url, total=product_count, page=page, step=ppg, scope=7, url_args=post)
        offset = pager['offset']
        products = search_product[offset: offset + ppg]
        thumbnails = request.env['product.template'].get_thumbnail_default_variant2(request.env.context['pricelist'],products)
        
        _logger.warning(f"victor products: {products}")
        # ~ dv_products = request.env['product.product'].search([['product_tmpl_id', 'in', products.ids], ['default_variant', '=', True]])
        # ~ _logger.warning(f"victor dv_products: {dv_products}")

        

        ProductAttribute = request.env['product.attribute']
        if products:
            # get all products without limit
            attributes = ProductAttribute.search([('product_tmpl_ids', 'in', search_product.ids)])
        else:
            attributes = ProductAttribute.browse(attributes_ids)

        layout_mode = request.session.get('website_sale_shop_layout_mode')
        if not layout_mode:
            if request.website.viewref('website_sale.products_list_view').active:
                layout_mode = 'list'
            else:
                layout_mode = 'grid'

        values = {
            'search': search,
            'category': category,
            'attrib_values': attrib_values,
            'attrib_set': attrib_set,
            'pager': pager,
            'pricelist': pricelist,
            'add_qty': add_qty,
            'products': thumbnails,
            'search_count': product_count,  # common for all searchbox
            'bins': TableCompute().process(products, ppg, ppr),
            'ppg': ppg,
            'ppr': ppr,
            'categories': categs,
            'attributes': attributes,
            'keep': keep,
            'search_categories_ids': search_categories.ids,
            'layout_mode': layout_mode,
        }
        if category:
            values['main_object'] = category
        return request.render("webshop_dermanord.products", values)
        # ~ return request.render("website_sale.products", values)

