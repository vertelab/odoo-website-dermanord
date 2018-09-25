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
from openerp.tools import html_escape as escape
from openerp.tools import float_compare
from datetime import datetime, date, timedelta
from lxml import html
from openerp.addons.website_sale.controllers.main import website_sale, QueryURL, table_compute
from openerp.addons.website.models.website import slug
from openerp.addons.website_fts.website_fts import WebsiteFullTextSearch
from openerp.addons.base.ir.ir_qweb import HTMLSafe
import werkzeug
from heapq import nlargest
import math
import time
from multiprocessing import Lock
import sys, traceback

from openerp import SUPERUSER_ID

from timeit import default_timer as timer

import logging
_logger = logging.getLogger(__name__)

PPG = 21 # Products Per Page
PPR = 3  # Products Per Row

class blog_post(models.Model):
    _inherit = 'blog.post'

    product_public_categ_ids = fields.Many2many(comodel_name='product.public.category', string='Product Public Categories')
    product_tmpl_ids = fields.Many2many(comodel_name='product.template', string='Product Templates')


class crm_tracking_campaign(models.Model):
    _inherit = 'crm.tracking.campaign'

    @api.multi
    def write(self, vals):
        for r in self:
            for o in r.object_ids:
                if o.object_id._name == 'product.template':
                    o.object_id.write({'campaign_changed': False if o.object_id.campaign_changed else True})
                elif o.object_id._name == 'product.product':
                    o.object_id.product_tmpl_id.write({'campaign_changed': False if o.object_id.product_tmpl_id.campaign_changed else True})
        return super(crm_tracking_campaign, self).write(vals)

    @api.model
    def create(self, vals):
        res = super(crm_tracking_campaign, self).create(vals)
        for o in res.object_ids:
            if o.object_id._name == 'product.template':
                o.object_id.write({'campaign_changed': True})
            elif o.object_id._name == 'product.product':
                o.object_id.product_tmpl_id.write({'campaign_changed': True})
        return res


class crm_campaign_object(models.Model):
    _inherit = 'crm.campaign.object'

    @api.one
    def _product_price(self):
        if self.object_id._name == 'product.template':
            variant = self.object_id.get_default_variant()
            self.product_price = self.env.ref('product.list0').price_get(variant.id, 1)[1] + sum([c.get('amount', 0.0) for c in variant.sudo().taxes_id.compute_all(self.env.ref('product.list0').price_get(variant.id, 1)[1], 1, None, self.env.user.partner_id)['taxes']])
        if self.object_id._name == 'product.product':
            self.product_price = self.env.ref('product.list0').price_get(self.object_id.id, 1)[1] + sum([c.get('amount', 0.0) for c in self.object_id.sudo().taxes_id.compute_all(self.env.ref('product.list0').price_get(self.object_id.id, 1)[1], 1, None, self.env.user.partner_id)['taxes']])
    product_price = fields.Float(string='Price for public', compute='_product_price')

    @api.model
    def create(self, vals):
        if vals.get('object_id') and vals['object_id'][0] == 'product.template':
            self.env['product.template'].browse(vals['object_id'][1]).write({'campaign_changed': True})
        elif vals.get('object_id') and vals['object_id'][0] == 'product.product':
            self.env['product.product'].browse(vals['object_id'][1]).product_tmpl_id.write({'campaign_changed': True})
        return super(crm_campaign_object, self).create(vals)

    @api.multi
    def write(self, vals):
        for r in self:
            if r.object_id and r.object_id._name == 'product.template':
                r.object_id.write({'campaign_changed': False if r.object_id.campaign_changed else True})
            elif r.object_id and r.object_id._name == 'product.product':
                r.object_id.product_tmpl_id.write({'campaign_changed': False if r.object_id.product_tmpl_id.campaign_changed else True})
        return super(crm_campaign_object, self).write(vals)


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
    use_tmpl_name = fields.Boolean(string='Use Template Name', help='When checked. The template name will be used in webshop')
    campaign_changed = fields.Boolean()

    @api.multi
    def get_default_variant(self):
        self.ensure_one()
        variants = self.product_variant_ids.filtered(lambda v: self.env.ref('website_sale.image_promo') in v.website_style_ids_variant)
        if len(variants) > 0:
            vs = variants.filtered(lambda v: v.check_access_group(self.env.user))
            return vs[0] if len(vs) > 0 else super(product_template, self).get_default_variant()
        else:
            return super(product_template, self).get_default_variant()

    # get defualt variant ribbon. if there's not one, get the template's ribbon
    @api.multi
    def Xget_default_variant_ribbon(self):
        if self.get_default_variant() and len(self.get_default_variant().website_style_ids_variant) > 0:
            return ' '.join([s.html_class for s in self.get_default_variant().website_style_ids_variant])
        else:
            return ' '.join([s.html_class for s in self.website_style_ids])

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

    @api.multi
    def format_facets(self,facet):
        self.ensure_one()
        values = []
        for value in self.facet_line_ids.mapped('value_ids') & facet.value_ids:
            values.append(u'<a t-att-href="{href}" class="text-muted"><span>{value_name}</span></a>'.format(
                href='/dn_shop/?facet_%s_%s=%s%s' %(facet.id, value.id, value.id, (u'&amp;%s' %'&amp;'.join([u'category_%s=%s' %(c.id, c.id) for c in self.public_categ_ids]) if len(self.public_categ_ids) > 0 else '')),
                value_name=value.name))
        return ', '.join(values)


    @api.multi
    def write(self, vals):
        res = super(product_template, self).write(vals)
        if 'list_price' in vals:
            self.product_variant_ids.get_product_tax()
        return res

    @api.multi
    def fts_search_suggestion(self):
        """
        Return a search result for search_suggestion.
        """
        res = super(product_template, self).fts_search_suggestion()
        res['event_type_id'] = self.event_type_id and self.event_type_id.id or False
        return res

class product_product(models.Model):
    _inherit = 'product.product'


    #~ so_line_ids = fields.One2many(comodel_name='sale.order.line', inverse_name='product_id')  # performance hog, do we need it?
    sold_qty = fields.Integer(string='Sold', default=0)
    website_style_ids_variant = fields.Many2many(comodel_name='product.style', string='Styles for Variant')

    @api.one
    def _fullname(self):
        self.fullname = '%s %s' % (self.name, ', '.join(self.attribute_value_ids.mapped('name')))
    fullname = fields.Char(compute='_fullname')

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


    @api.multi
    def fts_search_suggestion(self):
        """
        Return a search result for search_suggestion.
        """
        res = super(product_product, self).fts_search_suggestion()
        res['event_type_id'] = self.event_type_id and self.event_type_id.id or False
        return res

class product_facet(models.Model):
    _inherit = 'product.facet'

    @api.multi
    def get_filtered_facets(self, form_values):
        categories = []
        if len(form_values) > 0:
            for k, v in form_values.iteritems():
                if k.split('_')[0] == 'category':
                    if v:
                        categories.append(int(v))
        facets = self.browse([])
        if len(categories) > 0:
            for facet in facets.search([], order='sequence'):
                if len(facet.category_ids) == 0:
                    facets |= facet
                else:
                    for category in facet.category_ids:
                        if category.id in categories:
                            facets |= facet
        elif len(categories) == 0:
            facets = self.search([]).filtered(lambda f: len(f.category_ids) == 0)
        return facets


class product_pricelist(models.Model):
    _inherit = 'product.pricelist'

    rec_pricelist_id = fields.Many2one(comodel_name='product.pricelist', string='Recommended Pricelist')
    for_reseller = fields.Boolean(string='For Reseller')

    @api.multi
    def price_get(self, prod_id, qty, partner=None):
        return super(product_pricelist, self).price_get(prod_id, qty, partner)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def address_to_html(self, options=None):
        """Corresponds to the contact t-field widget."""
        if options is None:
            options = {}
        opf = options.get('fields') or ["name", "address", "phone", "mobile", "fax", "email"]

        value_rec = self.sudo().with_context(show_address=True)
        value = value_rec.name_get()[0][1]

        val = {
            'name': value.split("\n")[0],
            'address': escape("\n".join(value.split("\n")[1:])),
            'phone': value_rec.phone,
            'mobile': value_rec.mobile,
            'fax': value_rec.fax,
            'city': value_rec.city,
            'country_id': value_rec.country_id.display_name,
            'website': value_rec.website,
            'email': value_rec.email,
            'fields': opf,
            'object': value_rec,
            'options': options
        }

        html = self.env.ref("base.contact").render(val, engine='ir.qweb').decode('utf8')

        return HTMLSafe(html)


class sale_order(models.Model):
    _inherit='sale.order'

    @api.multi
    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        """ Add or set product quantity, add_qty can be negative """
        self.ensure_one()

        quantity = 0
        if self.state != 'draft':
            request.session['sale_order_id'] = None
            raise Warning(_('It is forbidden to modify a sale order which is not in draft status'))

        ticket_id = request.context.get("event_ticket_id")
        line = self.order_line.filtered(lambda l: ((line_id == l.id) if line_id else (l.product_id.id == product_id)) and (not ticket_id or l.event_ticket_id.id == ticket_id))
        line = line and line[0]

        # Create line if no line with product_id can be located
        if not line:
            if ticket_id:
                ticket = self.env['event.event.ticket'].with_context(pricelist=self.pricelist_id.id).browse(ticket_id)
                product = ticket.product_id
            else:
                product = self.env['product.product'].browse(product_id)
            values = self.env['sale.order.line'].sudo().product_id_change(
                        pricelist=self.pricelist_id.id,
                        product=product.id,
                        partner_id=self.partner_id.id,
                        fiscal_position=self.fiscal_position.id,
                        qty=set_qty or add_qty,
                    )['value']
            values['name'] = product.description_sale and "%s\n%s" % (product.display_name, product.description_sale) or product.display_name
            values['product_id'] = product.id
            values['order_id'] = self.id
            values['product_uom_qty'] = set_qty or add_qty
            if ticket_id:
                values['event_id'] = ticket.event_id.id
                values['event_ticket_id'] = ticket.id
                values['price_unit'] = ticket.price_reduce or ticket.price
                values['name'] = "%s\n%s" % (ticket.event_id.display_name, ticket.name)
            if values.get('tax_id') != None:
                values['tax_id'] = [(6, 0, values['tax_id'])]
            line = self.env['sale.order.line'].create(values)
            if add_qty:
                add_qty = 0

        # compute new quantity
        if set_qty:
            quantity = set_qty
        elif add_qty != None:
            quantity = line.product_uom_qty + (add_qty or 0)

        # Remove zero of negative lines
        if quantity <= 0:
            line.unlink()

        elif quantity != line.product_uom_qty:
            line.product_uom_qty = quantity

        return {
                'name': self.name,
                'line_id': line.id,
                'quantity': quantity,
                'cart_quantity': self.cart_quantity,
                'amount_total':self.amount_total,
                'amount_untaxed': self.amount_untaxed,
            }

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.multi
    def sale_home_confirm_copy(self):
        if self.is_delivery or self.is_min_order_fee:
            return False
        return super(SaleOrderLine, self).sale_home_confirm_copy()

dn_cart_update = {}

class Website(models.Model):
    _inherit = 'website'

    def handle_error_403(self, path):
        """Emergency actions to perform if we run into an unexpected access error."""
        if path == '/dn_shop':
            # Reset domain so customer is hopefully not endlessly stuck.
            self.dn_shop_set_session('product.template', {'post_form': 'ok'}, '/dn_shop')
        elif path == '/dn_list':
            # Reset domain so customer is hopefully not endlessly stuck.
            self.dn_shop_set_session('product.product', {'post_form': 'ok'}, '/dn_list')

    # TODO: Move these functions from WebsiteSale
    def get_form_values(self):
        if not request.session.get('form_values'):
            request.session['form_values'] = {}
        return request.session.get('form_values')

    def get_chosen_filter_qty(self, post):
        chosen_filter_qty = 0
        for k, v in post.iteritems():
            if k not in ['post_form', 'order', 'current_ingredient']:
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

    def get_domain_append(self, model, dic):
        facet_ids = {}
        category_ids = []
        ingredient_ids = []
        not_ingredient_ids = []
        current_ingredient = None
        current_ingredient_key = None
        current_news = None
        current_offer = None

        for k, v in dic.iteritems():
            if k.split('_')[0] == 'facet':
                if v:
                    group, id = k.split('_')[1:]
                    if not group in facet_ids:
                        facet_ids[group] = []
                    facet_ids[group].append(int(v))
                    request.session.get('form_values')['facet_%s_%s' %(group, id)] = id
            if k.split('_')[0] == 'category':
                if v:
                     category_ids.append(int(v))
                     request.session.get('form_values')['category_%s' % int(v)] = int(v)
            if k.split('_')[0] == 'ingredient':
                if v:
                    ingredient_ids.append(int(v))
                    request.session.get('form_values')['ingredient_%s' %int(v)] = int(v)
            if k == 'current_news':
                if v:
                    current_news = 'current_news'
                    request.session.get('form_values')['current_news'] = 'current_news'
            if k == 'current_offer':
                if v:
                    current_offer = 'current_offer'
                    request.session.get('form_values')['current_offer'] = 'current_offer'
            if k.split('_')[0] == 'notingredient':
                if v:
                    not_ingredient_ids.append(int(v))
                    request.session.get('form_values')['notingredient_%s' % int(v)] = int(v)
            if k == 'current_ingredient':
                if v:
                    current_ingredient = int(v)
                    current_ingredient_key = 'ingredient_%s' % int(v)
                    ingredient_ids.append(int(v))

        if current_ingredient:
            dic['current_ingredient'] = int(current_ingredient)
            dic[current_ingredient_key] = current_ingredient

        domain_append = [('sale_ok', '=', True),('event_ok', '=', False)]
        if category_ids:
            domain_append += [('public_categ_ids', 'in', [id for id in category_ids])]
        if facet_ids:
            for group in facet_ids:
                ids = facet_ids[group]
                if model == 'product.product':
                    domain_append += ['|' for i in range(len(ids) - 1)] + [('facet_line_ids.value_ids', '=', id) for id in ids]
                if model == 'product.template':
                    domain_append += ['|' for i in range(len(ids) - 1)] + [('product_variant_ids.facet_line_ids.value_ids', '=', id) for id in ids]
        if ingredient_ids or not_ingredient_ids:
            product_ids = request.env['product.product'].sudo().search_read(
                ['|' for i in range(len(ingredient_ids) - 1)] + [('ingredient_ids', '=', id) for id in ingredient_ids] + [('ingredient_ids', '!=', id) for id in not_ingredient_ids], ['id'])
            domain_append.append(('product_variant_ids', 'in', [r['id'] for r in product_ids]))
        if request.session.get('form_values'):
            if request.session.get('form_values').get('current_news') or request.session.get('form_values').get('current_offer'):
                offer_domain = self.domain_current(model, dic)
                if len(offer_domain) > 0:
                    for d in offer_domain:
                        domain_append.append(d)

        return domain_append

    def domain_current(self, model, dic):
        domain_current = []
        def append_domain(domain1, domain2):
            if domain1:
                domain1.insert(0, '|')
            domain1 += domain2
        if 'current_news' in dic:
            promo_id = request.env.ref('website_sale.image_promo').id
            if model == 'product.template':
                append_domain(domain_current, ['|', ('website_style_ids', '=', promo_id), ('product_variant_ids.website_style_ids_variant', '=', promo_id)])
            if model == 'product.product':
                append_domain(domain_current, ['|', ('product_tmpl_id.website_style_ids', '=', promo_id), ('website_style_ids_variant', '=', promo_id)])
        for offer_type in ['current_offer']:
            if offer_type in dic:
                reseller = request.env.user.partner_id.property_product_pricelist and request.env.user.partner_id.property_product_pricelist.for_reseller
                # TODO: This looks like a lot of browses. Should be possible to shorten it considerably.
                if model == 'product.template':
                    #get product.template that have variants are in current offer
                    campaign_product_ids = list(set(
                        request.env[model].get_campaign_tmpl(for_reseller=reseller).mapped('id') +
                        request.env['product.product'].get_campaign_variants(for_reseller=reseller).mapped('product_tmpl_id').mapped('id')))
                if model == 'product.product':
                    campaign_product_ids = list(set(
                        request.env[model].get_campaign_variants(for_reseller=reseller).mapped('id') +
                        request.env['product.product'].search([('product_tmpl_id.id', 'in', request.env['product.template'].get_campaign_tmpl(for_reseller=reseller).mapped('id'))]).mapped('id')))
                if campaign_product_ids:
                    append_domain(domain_current, [('id', 'in', campaign_product_ids)])
                else:
                    append_domain(domain_current, [('id', '=', 0)])
        return [('sale_ok', '=', True), ('dv_name', '!=', 'Error')] + domain_current

    def dn_shop_set_session(self, model, post, url):
        """Update session for /dn_shop"""
        default_order = 'sold_qty desc'
        if post.get('order'):
            default_order = post.get('order')
            if request.session.get('form_values'):
                request.session['form_values']['order'] = default_order
        request.session['current_order'] = default_order

        if post.get('post_form') == 'ok':
            request.session['form_values'] = post

        request.session['url'] = url
        request.session['chosen_filter_qty'] = self.get_chosen_filter_qty(self.get_form_values())
        request.session['sort_name'], request.session['sort_order'] = self.get_chosen_order(self.get_form_values())

        if post:
            request.session['form_values']['current_ingredient'] = post.get('current_ingredient')
            request.session['current_ingredient'] = post.get('current_ingredient')
            domain = self.get_domain_append(model, post)
        else:
            domain = self.get_domain_append(model, request.session.get('form_values', {}))
        # ~ _logger.warn('\n\ndomain: %s\n' % domain)
        request.session['current_domain'] = domain

    # API handling broken for unknown reasons. Decorators not working properly with this method.
    def sale_get_order(self, cr, uid, ids, force_create=False, code=None, update_pricelist=None, check_draft=True, context=None):
        env = api.Environment(cr, uid, context)
        sale_order_obj = env['sale.order']
        sale_order_id = request.session.get('sale_order_id')

        #~ if sale_order_id: # Check if order has been tampered on backoffice
            #~ sale_order = sale_order_obj.sudo().browse(sale_order_id)
            #~ if sale_order and sale_order.order_line.filtered(lambda l: l.state not in ['draft']):
                #~ sale_order_id = None

        # Test validity of the sale_order_id. Match user and check state.
        sale_order = sale_order_id and env['sale.order'].sudo().search([('id', '=', sale_order_id), ('partner_id.user_ids', '=', uid)] + ([('state', '=', 'draft')] if check_draft else []))

        # Find old sale order that is a webshop cart.
        if not sale_order and env.user != env.ref('base.public_user'):
            # Check for staff purchases
            employee = request.env['hr.employee'].sudo().search([('user_id', '=', request.env.user.id)])
            if employee and employee.address_home_id:
                partner = employee.address_home_id
            else:
                partner = env.user.partner_id
            sale_order = env['sale.order'].sudo().search([
                ('partner_id', '=', partner.id),
                ('section_id', '=', env.ref('website.salesteam_website_sales').id),
                ('state', '=', 'draft'),
            ], limit=1)
            if sale_order:
                request.session['sale_order_id'] = sale_order.id

        # create so if needed
        if not sale_order and (force_create or code) and env.user != env.ref('base.public_user'):
            values = {
                'user_id': env.ref('base.user_admin').id,
                'partner_id': env.user.partner_id.id,
                'pricelist_id': env.user.partner_id.property_product_pricelist.id,
                'section_id': env.ref('website.salesteam_website_sales').id,
            }
            values.update(env['sale.order'].sudo().onchange_partner_id(env.user.partner_id.commercial_partner_id.id)['value'])
            sale_order = env['sale.order'].sudo().create(values)
            request.session['sale_order_id'] = sale_order.id

        #~ sale_order = super(Website, self).sale_get_order(cr, uid, ids, force_create, code, update_pricelist, context)

        # TODO: Fix code and and update_pricelist

        #~ if code and code != sale_order.pricelist_id.code:
                #~ pricelist_ids = self.pool['product.pricelist'].search(cr, SUPERUSER_ID, [('code', '=', code)], context=context)
                #~ if pricelist_ids:
                    #~ pricelist_id = pricelist_ids[0]
                    #~ request.session['sale_order_code_pricelist_id'] = pricelist_id
                    #~ update_pricelist = True

            #~ pricelist_id = request.session.get('sale_order_code_pricelist_id') or partner.property_product_pricelist.id

            #~ # check for change of partner_id ie after signup
            #~ if sale_order.partner_id.id != partner.id and request.website.partner_id.id != partner.id:
                #~ flag_pricelist = False
                #~ if pricelist_id != sale_order.pricelist_id.id:
                    #~ flag_pricelist = True
                #~ fiscal_position = sale_order.fiscal_position and sale_order.fiscal_position.id or False

                #~ values = sale_order_obj.onchange_partner_id(cr, SUPERUSER_ID, [sale_order_id], partner.id, context=context)['value']
                #~ if values.get('fiscal_position'):
                    #~ order_lines = map(int,sale_order.order_line)
                    #~ values.update(sale_order_obj.onchange_fiscal_position(cr, SUPERUSER_ID, [],
                        #~ values['fiscal_position'], [[6, 0, order_lines]], context=context)['value'])

                #~ values['partner_id'] = partner.id
                #~ sale_order_obj.write(cr, SUPERUSER_ID, [sale_order_id], values, context=context)

                #~ if flag_pricelist or values.get('fiscal_position', False) != fiscal_position:
                    #~ update_pricelist = True

            #~ # update the pricelist
            #~ if update_pricelist:
                #~ values = {'pricelist_id': pricelist_id}
                #~ values.update(sale_order.onchange_pricelist_id(pricelist_id, None)['value'])
                #~ sale_order.write(values)
                #~ for line in sale_order.order_line:
                    #~ if line.exists():
                        #~ sale_order._cart_update(product_id=line.product_id.id, line_id=line.id, add_qty=0)

            #~ # update browse record
            #~ if (code and code != sale_order.pricelist_id.code) or sale_order.partner_id.id !=  partner.id:
                #~ sale_order = sale_order_obj.browse(cr, SUPERUSER_ID, sale_order.id, context=context)

        return sale_order

    def price_format(self, price, dp=None):
        if not dp:
            dp = request.env['res.lang'].search_read([('code', '=', request.env.lang)], ['decimal_point'])
            dp = dp and dp[0]['decimal_point'] or '.'
        return ('%.2f' %price).replace('.', dp)


class WebsiteSale(website_sale):

    FACETS = {}  # Static variable
    dn_cart_lock = Lock()

    @http.route('/shop/payment/validate', type='http', auth="public", website=True)
    def payment_validate(self, transaction_id=None, sale_order_id=None, **post):
        if sale_order_id is None:
            order = request.website.sale_get_order(check_draft=False, context=request.context)
            return super(WebsiteSale, self).payment_validate(transaction_id, order.id, **post)
        return super(WebsiteSale, self).payment_validate(transaction_id, sale_order_id, **post)

    @http.route([
        '/shop',
        '/shop/page/<int:page>',
        '/shop/category/<model("product.public.category"):category>',
        '/shop/category/<model("product.public.category"):category>/page/<int:page>'
    ], type='http', auth="public", website=True)
    def shop(self, page=0, category=None, search='', **post):
        return request.redirect(request.session.get('url') or '/dn_shp')

    @http.route(['/shop/confirm_order'], type='http', auth="public", website=True)
    def confirm_order(self, **post):
        order = request.website.sale_get_order()
        if not order:
            return request.redirect("/shop")
        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        values = self.checkout_values(post)
        values["error"] = self.checkout_form_validate(values["checkout"])
        if values["error"]:
            return request.website.render("website_sale.checkout", values)
        self.checkout_form_save(values["checkout"])
        request.session['sale_last_order_id'] = order.id
        request.website.sale_get_order(update_pricelist=True)
        _logger.warn('Partner_id (confirm) %s shipping %s invoice %s' % (order.partner_id,order.partner_shipping_id,order.partner_invoice_id))
        return request.redirect("/shop/payment")

    @http.route(['/shop/payment'], type='http', auth="public", website=True)
    def payment(self, **post):
        """ Payment step. This page proposes several payment means based on available
        payment.acquirer. State at this point :

         - a draft sale order with lines; otherwise, clean context / session and
           back to the shop
         - no transaction in context / session, or only a draft one, if the customer
           did go to a payment.acquirer website but closed the tab without
           paying / canceling
        """
        payment_obj = request.env['payment.acquirer']
        sale_order_obj = request.env['sale.order']

        order = request.website.sale_get_order()
        _logger.warn('Partner_id (before payment) %s shipping %s invoice %s' % (order.partner_id,order.partner_shipping_id,order.partner_invoice_id))
        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        shipping_partner_id = False
        if order:
            if order.partner_shipping_id.id:
                shipping_partner_id = order.partner_shipping_id.id
            else:
                shipping_partner_id = order.partner_invoice_id.id
        values = {
            'order': order.sudo()
        }
        values['errors'] = sale_order_obj._get_errors(order)
        values.update(sale_order_obj._get_website_data(order))
        if not values['errors']:
            acquirer_ids = payment_obj.sudo().search([('website_published', '=', True), ('company_id', '=', order.company_id.id)])
            values['acquirers'] = list(acquirer_ids)
            render_ctx = dict(request.env.context, submit_class='btn btn-primary', submit_txt=_('Place Order'))
            for acquirer in values['acquirers']:
                acquirer.button = acquirer.with_context(render_ctx).render(
                    '/',
                    order.amount_total,
                    order.pricelist_id.currency_id.id,
                    partner_id=shipping_partner_id,
                    tx_values={
                        'return_url': '/shop/payment/validate',
                    })[0]
        _logger.warn('Partner_id (payment) %s shipping %s invoice %s res %s' % (order.partner_id,order.partner_shipping_id,order.partner_invoice_id,values))
        return request.website.render("website_sale.payment", values)

    mandatory_billing_fields = ["name", "phone", "email", "street", "city", "country_id"]

    def show_purchase_button(self, product):
        sale_ok = False
        if product and product.sudo().sale_ok and product.sudo().instock_percent >= 50.0 and request.env.user.partner_id.commercial_partner_id.property_product_pricelist.for_reseller:
            sale_ok = True
        return sale_ok

    def checkout_form_validate(self, data):
        error = dict()
        if not data.get("shipping_id") and data.get('shipping_id') != 0:
            error['shipping_id'] = 'missing'

        if not data.get("invoicing_id") and data.get('invoicing_id') != 0:
            error['invoicing_id'] = 'missing'

        return error

    def checkout_values(self, data=None):
        start = timer()
        #TODO: Completely replace this function to cut down on load times.
        if not data:
            data = {}
        res = super(WebsiteSale, self).checkout_values(data)
        if request.env.user != request.website.user_id:
            # Check for staff purchase
            employee_id = request.env['hr.employee'].sudo().search([('user_id', '=', request.env.user.id)])
            if employee_id and employee_id.address_home_id:
                partner = employee_id.address_home_id
            else:
                partner = request.env.user.partner_id

            order = request.website.sale_get_order(force_create=1)
            invoicings = request.env['res.partner'].sudo().with_context(show_address=True).search([
                ("parent_id", "=", partner.commercial_partner_id.id),
                '|',
                    ('type', "=", 'invoice'),
                    ('type', "=", 'default')
            ]) | partner.commercial_partner_id
            shippings = request.env['res.partner'].sudo().with_context(show_address=True).search([
                ("parent_id", "=", partner.commercial_partner_id.id),
                '|',
                    ('type', "=", 'delivery'),
                    ('type', "=", 'default')
            ]) | partner.commercial_partner_id

            # Update to selected addresses, if they are valid
            invoicing_id = shipping_id = None
            try:
                invoicing_id = int(data.get("invoicing_id", '0'))
                if invoicing_id not in invoicings._ids:
                    invoicing_id = order.partner_invoice_id.id
            except ValueError:
                pass
            try:
                shipping_id = int(data.get("shipping_id", '0'))
                if shipping_id not in shippings._ids:
                    shipping_id = order.partner_shipping_id.id
            except ValueError:
                pass
            invoicing_id = invoicing_id or order.partner_invoice_id.id
            shipping_id = shipping_id or order.partner_shipping_id.id

            res['shippings'] = shippings
            res['invoicings'] = invoicings.sudo()
            res['invoicing_id'] = invoicing_id
            res['shipping_id'] = shipping_id
            # the checkout dict updates the addresses on the order
            res['checkout']['invoicing_id'] = invoicing_id
            res['checkout']['shipping_id'] = shipping_id
        # ~ _logger.warn('checkout_values: %s' % (timer() - start))
        return res

    def checkout_form_save(self, checkout):
        start = timer()

        order = request.website.sale_get_order(force_create=1)

        orm_partner = request.env['res.partner']
        orm_user = request.env['res.users']
        order_obj = request.env['sale.order'].sudo()

        partner_lang = request.lang if request.lang in [lang.code for lang in request.website.language_ids] else None

        # set partner_id
        partner_id = order.partner_id
        # ~ partner_id = None
        # ~ if request.env.user != request.website.user_id: # Check if we are not public user
            # ~ partner_id = request.env.user.partner_id
        # ~ elif order.partner_id:
            # ~ user_ids = request.env['res.users'].sudo().search(
                # ~ [("partner_id", "=", order.partner_id.id)], active_test=False)
            # ~ if not user_ids or request.website.user_id not in user_ids:
                # ~ partner_id = order.partner_id

        order_info = {
            'partner_id': partner_id.id,
            'message_follower_ids': [(4, partner_id.id), (3, request.website.partner_id.id)],
            'date_order': fields.Datetime.now(),
        }
        if order_info['partner_id'] != order.partner_id.id:
            order_info.update(order.onchange_partner_id(partner_id.id)['value'])
        # Reset to the specified shipping and invoice adresses
        order_info.update({
            'partner_invoice_id': checkout.get('invoicing_id') or partner_id.id,
            'partner_shipping_id': checkout.get('shipping_id') or partner_id.id,
        })
        _logger.warn('Partner_id (order_info) %s shipping %s' % (order_info['partner_invoice_id'],order_info['partner_shipping_id']))
        if order_info['partner_id'] != order.partner_id or order_info['shipping_id'] != order.partner_shipping_id.id:
            address_change = order.onchange_delivery_id(
                order.company_id.id, partner_id.id, checkout.get('shipping_id'), None)['value']
            order_info.update(address_change)
            if address_change.get('fiscal_position') and address_change.get('fiscal_position') != order.fiscal_position.id:
                fiscal_update = order.onchange_fiscal_position(
                    address_change['fiscal_position'],
                    [(4, l.id) for l in order.order_line])['value']
                order_info.update(fiscal_update)
        if 'user_id' in order_info:
            order_info.pop('user_id')
        order.sudo().write(order_info)

        #super(WebsiteSale, self).checkout_form_save(checkout)
        # ~ _logger.warn('checkout_form_save super:%s' % (timer() - start))
        #~ order = request.website.sale_get_order(force_create=1)
        #~ order.date_order = fields.Datetime.now()
        #~ partner_invoice_id = checkout.get('invoicing_id') or request.env.user.partner_id.id
        #~ if order.partner_invoice_id.id != partner_invoice_id:
            #~ order.write({'partner_invoice_id': partner_invoice_id})

        # ~ _logger.warn('checkout_form_save:%s' % (timer() - start))

    @http.route([
        '/dn_shop',
        '/dn_shop/page/<int:page>',
        '/dn_shop/category/<model("product.public.category"):category>',
        '/dn_shop/category/<model("product.public.category"):category>/page/<int:page>',
    ], type='http', auth="public", website=True)
    def dn_shop(self, page=0, category=None, search='', **post):
        _logger.warn('----------------_> %s '  % 'Start')


        url = "/dn_shop"
        request.website.dn_shop_set_session('product.template', post, url)

        if category:
            if not request.session.get('form_values'):
                request.session['form_values'] = {'category_%s' %int(category): int(category)}
            request.session['form_values'] = {'category_%s' %int(category): int(category)}
            request.website.get_form_values()['category_' + str(int(category))] = int(category)
            request.session['current_domain'] = [('public_categ_ids', 'in', [int(category)])]
            request.session['chosen_filter_qty'] = request.website.get_chosen_filter_qty(request.website.get_form_values())

        _logger.warn('----------------_> %s '  % 'before pricelist')
        if not request.context.get('pricelist'):
            request.context['pricelist'] = int(self.get_pricelist())
        if search:
            post["search"] = search
        _logger.warn('----------------_> %s '  % 'before pricelist')

        # ~ category_obj = pool['product.public.category']
        # ~ category_ids = category_obj.search(cr, uid, [('parent_id', '=', False)], context=context)
        # ~ categs = category_obj.browse(cr, uid, category_ids, context=context)

        # ~ attributes_obj = request.registry['product.attribute']
        # ~ attributes_ids = attributes_obj.search(cr, uid, [], context=context)
        # ~ attributes = attributes_obj.browse(cr, uid, attributes_ids, context=context)

        no_product_message = ''
        products=request.env['product.template'].get_thumbnail_default_variant(request.session.get('current_domain'),request.context['pricelist'],limit=PPG, order=request.session.get('current_order'))
        _logger.warn('----------------_> %s '  % products)

        if len(products) == 0:
            no_product_message = _('Your filtering did not match any results. Please choose something else and try again.')
        # ~ price_data = request.website.get_price_fields(partner_pricelist)

        # ~ _logger.warn('----------------_> %s '  % request.env['product.template'].get_thumbnail_default_variant(domain, PPG, current_order,pricelist))

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
            'current_ingredient': request.env['product.ingredient'].browse(post.get('current_ingredient') or request.session.get('current_ingredient')),
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
            'products': request.env['product.template'].get_thumbnail_default_variant(session.get('current_domain'),request.context['pricelist'],order=request.session.get('current_order'),limit=6,offset=21+int(page)*6),
        }
        return values

    @http.route(['/dn_shop_json_list'], type='json', auth='public', website=True)
    def dn_shop_json_list(self, page=0, **kw):
        if not request.context.get('pricelist'):
            request.context['pricelist'] = int(self.get_pricelist())
        values = {
            'products': request.env['product.product'].get_list_row(request.session.get('current_domain'),request.context['pricelist'],order=request.session.get('current_order'),limit=10, offset=PPG+page*10),
        }
        return values


    @http.route(['/dn_shop/product/<model("product.template"):product>'], type='http', auth="public", website=True)
    def dn_product(self, product, category='', search='', **kwargs):
        # ~ cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        # ~ category_obj = pool['product.public.category']
        # ~ template_obj = pool['product.template']

        # ~ context.update(active_id=product.id)

        # ~ if category:
            # ~ category = category_obj.browse(cr, uid, int(category), context=context)
            # ~ category = category if category.exists() else False

        # ~ attrib_list = request.httprequest.args.getlist('attrib')
        # ~ attrib_values = [map(int,v.split("-")) for v in attrib_list if v]
        # ~ attrib_set = set([v[1] for v in attrib_values])

        # ~ keep = QueryURL('/dn_shop', category=category and category.id, search=search, attrib=attrib_list)

        # ~ category_ids = category_obj.search(cr, uid, [], context=context)
        # ~ category_list = category_obj.name_get(cr, uid, category_ids, context=context)
        # ~ category_list = sorted(category_list, key=lambda category: category[1])

        # ~ pricelist = self.get_pricelist()

        # ~ from_currency = pool.get('product.price.type')._get_field_currency(cr, uid, 'list_price', context)
        # ~ to_currency = pricelist.currency_id
        # ~ compute_currency = lambda price: pool['res.currency']._compute(cr, uid, from_currency, to_currency, price, context=context)

        # ~ if not request.context.get('pricelist'):
            # ~ request.context['pricelist'] = int(self.get_pricelist())
            # ~ product = template_obj.browse(cr, uid, int(product), context=context)

        # ~ request.session['chosen_filter_qty'] = request.website.get_chosen_filter_qty(request.website.get_form_values())
        # ~ request.session['sort_name'], request.session['sort_order'] = request.website.get_chosen_order(request.website.get_form_values())

        # ~ values = {
            # ~ 'search': search,
            # ~ 'category': category,
            # ~ 'pricelist': pricelist,
            # ~ 'attrib_values': attrib_values,
            # ~ 'compute_currency': compute_currency,
            # ~ 'attrib_set': attrib_set,
            # ~ 'keep': keep,
            # ~ 'url': request.session.get('url'),
            # ~ 'category_list': category_list,
            # ~ 'main_object': product,
            # ~ 'product': product,
            # ~ 'show_purchase_button': self.show_purchase_button(product.get_default_variant()),
            # ~ 'is_reseller': request.env.user.partner_id.property_product_pricelist.for_reseller,
            # ~ 'shop_footer': True,
        # ~ }
        # ~ return request.website.render("website_sale.product", values)

        product = request.env['product.template'].browse(int(product))
        values = {
            'url': request.session.get('url'),
            'detail': request.env['product.product'].get_product_detail(product, product.get_default_variant().id or product.product_variant_ids[0].id),
            'shop_footer': True,
        }
        return request.website.render("webshop_dermanord.product_detail_view", values)

    #controller only for reseller
    @http.route([
        '/dn_list',
        '/dn_list/page/<int:page>',
        '/dn_list/category/<model("product.public.category"):category>',
        '/dn_list/category/<model("product.public.category"):category>/page/<int:page>',
    ], type='http', auth="public", website=True)
    def dn_list(self, page=0, category=None, search='', **post):
        url = '/dn_list'
        request.website.dn_shop_set_session('product.product', post, url)
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

        no_product_message = ''
        products=request.env['product.product'].get_list_row(request.session.get('current_domain'),request.context['pricelist'],limit=PPG, order=request.session.get('current_order'))
        if len(products) == 0:
            no_product_message = _('Your filtering did not match any results. Please choose something else and try again.')

        return request.website.render("webshop_dermanord.products_list_reseller_view", {
            'title': _('Shop'),
            'search': search,
            'products': products,
            'rows': PPR,
            # ~ 'compute_currency': compute_currency,
            'url': url,
            'current_ingredient': request.env['product.ingredient'].browse(post.get('current_ingredient') or request.session.get('current_ingredient')),
            'shop_footer': True,
            'no_product_message': no_product_message,
            'all_products_loaded': True if len(products) < PPG else False,
        })

    @http.route([
        '/dn_shop/variant/<model("product.product"):variant>'
    ], type='http', auth="public", website=True)
    def dn_product_variant(self, variant, category='', search='', **kwargs):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        category_obj = pool['product.public.category']
        template_obj = pool['product.template']

        context.update(active_id=variant.sudo().product_tmpl_id.id)

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
            product = template_obj.browse(cr, uid, variant.sudo().product_tmpl_id.id, context=context)

        request.session['chosen_filter_qty'] = request.website.get_chosen_filter_qty(request.website.get_form_values())
        request.session['sort_name'], request.session['sort_order'] = request.website.get_chosen_order(request.website.get_form_values())

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
            'show_purchase_button': self.show_purchase_button(variant),
            'is_reseller': request.env.user.partner_id.property_product_pricelist.for_reseller,
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

    #~ @http.route(['/shop/cart/update'], type='http', auth="public", methods=['POST'], website=True)
    #~ def cart_update(self, product_id, add_qty=1, set_qty=0, **kw):
        #~ cr, uid, context = request.cr, request.uid, request.context
        #~ request.website.with_context(supress_checks=True).sale_get_order(force_create=1)._cart_update(product_id=int(product_id), add_qty=float(add_qty), set_qty=float(set_qty))
        #~ if kw.get('return_url'):
            #~ return request.redirect(kw.get('return_url'))
        #~ return request.redirect("/shop/cart")

    @http.route(['/shop/cart/update'], type='json', auth="public", website=True)
    def cart_update(self, product_id, add_qty=1, set_qty=0, **kw):

        start = timer()
        locked = True
        while not self.dn_cart_lock.acquire(False):
            if timer() - start > 2:
                locked = False
                break
        res = request.website.sale_get_order(force_create=1)._cart_update(product_id=int(product_id), add_qty=float(add_qty), set_qty=float(set_qty))
        if locked:
            self.dn_cart_lock.release()
        return [request.website.price_format(res['amount_untaxed']), res['cart_quantity'], res['amount_untaxed']]

    @http.route(['/website_sale_update_cart'], type='json', auth="public", website=True)
    def website_sale_update_cart(self):
        order = request.website.sale_get_order()
        dp = request.env['res.lang'].search_read([('code', '=', request.env.lang)], ['decimal_point', 'thousands_sep'])
        ts = dp and dp[0]['thousands_sep'] or ' '
        dp = dp and dp[0]['decimal_point'] or '.'
        res = {'amount_untaxed': '0.00', 'cart_quantity': '0', 'currency': 'SEK', 'decimal_point': dp, 'thousands_sep': ts}
        if order:
            res['amount_untaxed'] = request.website.price_format(order.amount_untaxed)
            res['cart_quantity'] = order.cart_quantity
            res['currency'] = order.pricelist_id.currency_id.name
            res['amount_float'] = order.amount_untaxed
        else:
            res['currency'] = request.env.user.partner_id.property_product_pricelist.currency_id.name
            res['amount_float'] = 0.0
        return res

    @http.route(['/dn_shop/search'], type='json', auth="public", website=True)
    def search(self, **kw):
        raise Warning(kw)
        return value



    @http.route(['/get/product_variant_data'], type='json', auth="public", website=True)
    def product_variant_data(self, product_id=None, **kw):
        is_reseller = False
        if request.env.user.partner_id.property_product_pricelist and request.env.user.partner_id.property_product_pricelist.for_reseller:
            is_reseller = True
        value = {}
        if product_id:
            product = request.env['product.product'].sudo().browse(int(product_id))
            if product:
                if not self.FACETS.get(product.id,False):
                    self.FACETS[product.id] = {}
                    if len(product.facet_line_ids) > 0:
                        for line in product.sudo().facet_line_ids:
                            self.FACETS[product.id][line.facet_id.name] = []
                            for v in line.value_ids:
                                self.FACETS[product.id].get(line.facet_id.name,[]).append([line.facet_id.id, v.name, v.id])
                ingredients_description = product.ingredients or ''
                ingredients = []
                product_ingredients = request.env['product.ingredient'].search([('product_ids', 'in', product_id)], order='sequence')
                if len(product_ingredients) > 0:
                    for i in product_ingredients:
                        ingredients.append([i.id if i.image else 0, i.name])

                offer = False
                if product in product.get_campaign_variants(for_reseller=request.env.user.partner_id.commercial_partner_id.property_product_pricelist.for_reseller):
                    offer = True
                elif product.product_tmpl_id in product.product_tmpl_id.get_campaign_tmpl(for_reseller=request.env.user.partner_id.commercial_partner_id.property_product_pricelist.for_reseller):
                    offer = True

                sale_ribbon = request.env.ref('website_sale.image_promo')

                if len(product.product_tmpl_id.public_categ_ids) > 0: # remove all previously category, facet and reset it according to the current product
                    for_values = request.session.get('form_values')
                    for k,v in for_values.items():
                        if k.split('_')[0] == 'facet' or 'category':
                            del for_values[k]
                    request.session['form_values'] = for_values
                    value['category'] = '&'.join(['category_%s=%s' %(c.id, c.id) for c in product.product_tmpl_id.public_categ_ids])

                value['id'] = product.id
                # ~ value['instock'] = self.in_stock(product.id)[0]
                # ~ value['stock_status'] = self.in_stock(product.id)[1]
                # ~ value['public_user'] = True if (not self.in_stock(product.id)[0] and self.in_stock(product.id)[1] == '') else False
                value['images'] = product.get_image_attachment_ids()
                value['facets'] = self.FACETS[product.id]
                value['ingredients_description'] = ingredients_description
                value['ingredients'] = ingredients
                value['default_code'] = product.default_code or ''
                value['public_desc'] = product.public_desc or ''
                value['use_desc'] = product.use_desc or ''
                value['reseller_desc'] = (product.reseller_desc or '') if is_reseller else ''
                value['offer'] = offer
                value['offer_text'] = _('Offer')
                value['news_text'] = _('News')
                value['ribbon'] = sale_ribbon in product.website_style_ids_variant if product.website_style_ids_variant else (sale_ribbon in product.product_tmpl_id.website_style_ids)
                # ~ value['sale_ok'] = True if (product.sale_ok and self.in_stock(product.id)[0] and request.env.user.partner_id.commercial_partner_id.property_product_pricelist.for_reseller) else False
        return value

    @http.route(['/get/product_variant_value'], type='json', auth="public", website=True)
    def product_variant_value(self, product_id=None, value_id=None, **kw):
        if product_id and value_id:
            product = request.env['product.template'].browse(int(product_id))
            if product:
                variants = product.product_variant_ids.filtered(lambda v: int(value_id) in v.attribute_value_ids.mapped("id"))
                return variants[0].ingredients if len(variants) > 0 else ''

    @http.route(['/event/type/<model("event.type"):event_type>'], type='http', auth="public", website=True)
    def event_type_info(self, event_type=None, **kw):
        values = {
            'event_type': event_type,
            'events': request.env['event.event'].search([
                ('state', "in", ['draft','confirm','done']),
                ('type', '=', event_type.id),
                ('date_begin', '>', fields.Datetime.now()),
            ]),
        }
        return request.website.render("webshop_dermanord.event_type_info", values)


#~ class WebsiteFullTextSearch(WebsiteFullTextSearch):

    #~ @http.route(['/search_suggestion'], type='json', auth="public", website=True)
    #~ def search_suggestion(self, search='', facet=None, res_model=None, limit=0, offset=0, **kw):
        #~ result = request.env['fts.fts'].term_search(search.lower(), facet, res_model, limit, offset)
        #~ result_list = result['terms']
        #~ rl = []
        #~ i = 0
        #~ while i < len(result_list) and len(rl) < 5:
            #~ r = result_list[i]
            #~ try:
                #~ if r.model_record._name == 'product.public.category':
                    #~ rl.append({
                        #~ 'res_id': r.res_id,
                        #~ 'model_record': r.model_record._name,
                        #~ 'name': r.model_record.name,
                    #~ })
                #~ elif r.model_record._name == 'product.template':
                    #~ if len(r.model_record.sudo().access_group_ids) == 0 or (len(r.model_record.sudo().access_group_ids) > 0 and request.env.user in r.model_record.sudo().access_group_ids.mapped('users')):
                        #~ rl.append({
                            #~ 'res_id': r.res_id,
                            #~ 'model_record': r.model_record._name,
                            #~ 'name': r.model_record.name,
                        #~ })
                #~ elif r.model_record._name == 'product.product':
                    #~ if len(r.model_record.sudo().access_group_ids) == 0 or (len(r.model_record.sudo().access_group_ids) > 0 and request.env.user in r.model_record.sudo().access_group_ids.mapped('users')):
                        #~ rl.append({
                            #~ 'res_id': r.res_id,
                            #~ 'model_record': r.model_record._name,
                            #~ 'name': r.model_record.name,
                            #~ 'product_tmpl_id': r.model_record.product_tmpl_id.id,
                        #~ })
                #~ elif r.model_record._name == 'blog.post':
                    #~ rl.append({
                        #~ 'res_id': r.res_id,
                        #~ 'model_record': r.model_record._name,
                        #~ 'name': r.model_record.name,
                        #~ 'blog_id': r.model_record.blog_id.id,
                    #~ })
                #~ elif r.model_record._name == 'product.facet.line':
                    #~ rl.append({
                        #~ 'res_id': r.res_id,
                        #~ 'model_record': r.model_record._name,
                        #~ 'product_tmpl_id': r.model_record.product_tmpl_id.id,
                        #~ 'product_name': r.model_record.product_tmpl_id.name,
                    #~ })
            #~ except:
                #~ pass
            #~ i += 1
        #~ return rl
