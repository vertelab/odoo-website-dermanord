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
from datetime import datetime, date, timedelta
from lxml import html
from openerp.addons.website_sale.controllers.main import website_sale, QueryURL, table_compute
from openerp.addons.website.models.website import slug
from openerp.addons.website_fts.website_fts import WebsiteFullTextSearch
from openerp.addons.base.ir.ir_qweb import HTMLSafe
import werkzeug
from heapq import nlargest
import math

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
        for o in self.env['crm.campaign.object'].browse(vals.get('object_ids')):
            if o.object_id._name == 'product.template':
                o.object_id.write({'campaign_changed': True})
            elif o.object_id._name == 'product.product':
                o.object_id.product_tmpl_id.write({'campaign_changed': True})
        return super(crm_tracking_campaign, self).create(vals)


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

    product_variant_count = fields.Integer(string='# of Product Variants', compute='_compute_product_variant_count', store=True)

    @api.one
    @api.depends('product_variant_ids.active')
    def _compute_product_variant_count(self):
        self.product_variant_count = len(self.product_variant_ids.filtered('active'))

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
        variants = self.product_variant_ids.filtered(lambda v: request.env.ref('website_sale.image_promo') in v.website_style_ids_variant)
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

    @api.model
    def Xget_all_variant_data(self, products):
        pricelist = self.env.ref('product.list0')
        res = {}
        placeholder = '/web/static/src/img/placeholder.png'
        for p in products:
            variant = p.get_default_variant()
            if variant:
                res[p.id]= {}
                try:
                    res[p.id]['recommended_price'] = pricelist.price_get(variant.id, 1)[1] + sum([c.get('amount', 0.0) for c in p.sudo().taxes_id.compute_all(pricelist.price_get(variant.id, 1)[1], 1, None, self.env.user.partner_id)['taxes']])
                    res[p.id]['price'] = variant.price
                    res[p.id]['price_tax'] = res[p.id]['price'] + sum(c.get('amount', 0.0) for c in p.sudo().taxes_id.compute_all(res[p.id]['price'], 1, None, self.env.user.partner_id)['taxes'])
                    res[p.id]['default_code'] = variant.default_code or ''
                    res[p.id]['description_sale'] = variant.description_sale or ''
                    res[p.id]['image_src'] = '/imagefield/ir.attachment/datas/%s/ref/%s' %(variant.image_ids[0].image_attachment_id.id, 'snippet_dermanord.img_product') if (variant.image_ids and variant.image_ids[0].image_attachment_id) else placeholder
                except Exception as e:
                    res[p.id] = {'recommended_price': 0.0, 'price': 0.0, 'price_tax': 0.0, 'default_code': 'error', 'description_sale': '%s' %e, 'image_src': placeholder}
        return res

    @api.multi
    @api.depends('name', 'price', 'list_price', 'taxes_id', 'default_code', 'description_sale', 'image', 'image_ids', 'website_style_ids', 'attribute_line_ids.value_ids')
    def _get_all_variant_data(self):
        pricelist = self.env.ref('product.list0')
        pricelist_45 = self.env['product.pricelist'].search([('name', '=', u'Återförsäljare 45')])
        pricelist_20 = self.env['product.pricelist'].search([('name', '=', 'Special 20')])
        placeholder = '/web/static/src/img/placeholder.png'
        environ = request.httprequest.headers.environ
        _logger.warn(environ.get("REMOTE_ADDR"))
        for p in self:
            variant = p.get_default_variant().read(['name', 'price', 'recommended_price', 'price_45', 'price_20', 'default_code', 'description_sale', 'attribute_value_ids', 'image_ids', 'website_style_ids_variant'])
            try:
                variant = p.get_default_variant().read(['name', 'price', 'recommended_price', 'price_45', 'price_20', 'default_code', 'description_sale', 'attribute_value_ids', 'image_ids', 'website_style_ids_variant'])
                attribute_value_ids = self.env['product.attribute.value'].browse(variant[0]['attribute_value_ids'])
                image_ids = self.env['base_multi_image.image'].browse(variant[0]['image_ids']).read(['image_attachment_id'])
                website_style_ids_variant = self.env['product.style'].browse(variant[0]['website_style_ids_variant']).read(['html_class'])
                if variant:
                    p.dv_recommended_price = variant[0]['recommended_price']
                    p.dv_price_45 = variant[0]['price_45']
                    p.dv_price_20 = variant[0]['price_20']
                    p.dv_price = variant[0]['price']
                    p.dv_price_tax = p.dv_price + sum(c.get('amount', 0.0) for c in p.sudo().taxes_id.compute_all(p.dv_price, 1, None, self.env.user.partner_id)['taxes'])
                    p.dv_default_code = variant[0]['default_code'] or ''
                    p.dv_description_sale = variant[0]['description_sale'] or ''
                    p.dv_name = p.name if p.use_tmpl_name else ', '.join([p.name] + attribute_value_ids.mapped('name'))
                    p.dv_image_src = '/imagefield/ir.attachment/datas/%s/ref/%s' %(image_ids[0]['image_attachment_id'][0], 'snippet_dermanord.img_product') if (image_ids and image_ids[0]) else placeholder
                    #~ p.dv_ribbon = ' '.join([s.html_class for s in website_style_ids_variant]) if len(website_style_ids_variant) > 0 else ' '.join([s.html_class for s in p.website_style_ids])
                    p.dv_ribbon = website_style_ids_variant[0]['html_class'] if len(website_style_ids_variant) > 0 else ' '.join([s.html_class for s in p.website_style_ids])
            except Exception as e:
                _logger.error(e)
                p.dv_recommended_price = 0.0
                p.dv_price_45 = 0.0
                p.dv_price_20 = 0.0
                p.dv_price = 0.0
                p.dv_price_tax = 0.0
                p.dv_default_code = 'except'
                p.dv_description_sale = '%s' %e
                p.dv_name = 'Error'
                p.dv_image_src = placeholder
                p.dv_ribbon = ''
    dv_recommended_price = fields.Float(compute='_get_all_variant_data', store=True)
    dv_price_45 = fields.Float(compute='_get_all_variant_data', store=True)
    dv_price_20 = fields.Float(compute='_get_all_variant_data', store=True)
    dv_price = fields.Float(compute='_get_all_variant_data', store=True)
    dv_price_tax = fields.Float(compute='_get_all_variant_data', store=True)
    dv_default_code = fields.Char(compute='_get_all_variant_data', store=True)
    dv_description_sale = fields.Text(compute='_get_all_variant_data', store=True)
    dv_image_src = fields.Char(compute='_get_all_variant_data', store=True)
    dv_name = fields.Char(compute='_get_all_variant_data', store=True)
    dv_ribbon = fields.Char(compute='_get_all_variant_data', store=True)

    @api.one
    @api.depends('campaign_changed')
    def _is_offer_product(self):
        self.is_offer_product_reseller = self in self.get_campaign_tmpl(for_reseller=True)
        if not self.is_offer_product_reseller:
            self.is_offer_product_reseller = self.product_variant_ids & self.get_campaign_variants(for_reseller=True)
        self.is_offer_product_consumer = self in self.get_campaign_tmpl(for_reseller=False)
        if not self.is_offer_product_consumer:
            self.is_offer_product_consumer = self.product_variant_ids & self.get_campaign_variants(for_reseller=False)
    is_offer_product_consumer = fields.Boolean(compute='_is_offer_product', store=True)
    is_offer_product_reseller = fields.Boolean(compute='_is_offer_product', store=True)


class product_product(models.Model):
    _inherit = 'product.product'

    recommended_price = fields.Float(compute='get_product_tax', compute_sudo=True, store=True)
    price_45 = fields.Float(compute='get_product_tax', compute_sudo=True, store=True)
    price_20 = fields.Float(compute='get_product_tax', compute_sudo=True, store=True)
    #~ tax_45 = fields.Float(compute='get_product_tax', compute_sudo=True, store=True)
    #~ tax_20 = fields.Float(compute='get_product_tax', compute_sudo=True, store=True)
    so_line_ids = fields.One2many(comodel_name='sale.order.line', inverse_name='product_id')
    sold_qty = fields.Integer(string='Sold', default=0)
    website_style_ids_variant = fields.Many2many(comodel_name='product.style', string='Styles for Variant')

    @api.one
    @api.depends('lst_price', 'product_tmpl_id.list_price')
    def get_product_tax(self):
        price = self.env.ref('product.list0').price_get(self.id, 1)[self.env.ref('product.list0').id]
        pricelist_45 = self.env['product.pricelist'].search([('name', '=', u'Återförsäljare 45')])
        pricelist_20 = self.env['product.pricelist'].search([('name', '=', 'Special 20')])
        self.price_45 = pricelist_45.price_get(self.id, 1)[pricelist_45.id]
        self.price_20 = pricelist_20.price_get(self.id, 1)[pricelist_20.id]
        #~ self.tax_45 = sum(map(lambda x: x.get('amount', 0.0), self.taxes_id.compute_all(self.price_45, 1, None, self.env.user.partner_id)['taxes']))
        #~ self.tax_20 = sum(map(lambda x: x.get('amount', 0.0), self.taxes_id.compute_all(self.price_20, 1, None, self.env.user.partner_id)['taxes']))
        self.recommended_price = price + sum(map(lambda x: x.get('amount', 0.0), self.taxes_id.compute_all(price, 1, None, self.env.user.partner_id)['taxes']))

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

    # get this variant ribbon. if there's not one, get the template's ribbon
    @api.multi
    def get_this_variant_ribbon(self):
        if len(self.website_style_ids_variant) > 0:
            return ' '.join([s.html_class for s in self.website_style_ids_variant])
        else:
            return ' '.join([s.html_class for s in self.product_tmpl_id.website_style_ids])

    @api.one
    @api.depends('product_tmpl_id.campaign_changed')
    def _is_offer_product(self):
        self.is_offer_product_reseller = self in self.get_campaign_variants(for_reseller=True)
        if not self.is_offer_product_reseller:
            self.is_offer_product_reseller = self.product_tmpl_id in self.product_tmpl_id.get_campaign_tmpl(for_reseller=True)
        self.is_offer_product_consumer = self in self.get_campaign_variants(for_reseller=False)
        if not self.is_offer_product_consumer:
            self.is_offer_product_consumer = self.product_tmpl_id in self.product_tmpl_id.get_campaign_tmpl(for_reseller=False)
    is_offer_product_consumer = fields.Boolean(compute='_is_offer_product', store=True)
    is_offer_product_reseller = fields.Boolean(compute='_is_offer_product', store=True)

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
    def _cart_update(self,product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        """ Add or set product quantity, add_qty can be negative """
        self.ensure_one()

        quantity = 0
        if self.state != 'draft':
            request.session['sale_order_id'] = None
            raise Warning(_('It is forbidden to modify a sale order which is not in draft status'))

        line = self.order_line.filtered(lambda l: True if not line_id and l.product_id.id == product_id else line_id == l.id)
        if len(line) > 1:
            line = line_id[0]

        # Create line if no line with product_id can be located
        if not line:
            product = self.env['product.product'].browse(product_id)
            values = self.env['sale.order.line'].sudo().product_id_change(
                        pricelist=self.pricelist_id.id,
                        product=product.id,
                        partner_id=self.partner_id.id,
                        fiscal_position=self.fiscal_position.id,
                        qty=set_qty or add_qty,
                        #~ company_id=self.company_id.id
                    )['value']
            values['name'] = product.description_sale and "%s\n%s" % (product.display_name, product.description_sale) or product.display_name
            values['product_id'] = product.id
            values['order_id'] = self.id
            values['product_uom_qty'] = set_qty or add_qty
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


class Website(models.Model):
    _inherit = 'website'

    # TODO: Move these functions from WebsiteSale
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

    def get_domain_append(self, model, dic):
        facet_ids = []
        category_ids = []
        ingredient_ids = []
        not_ingredient_ids = []
        current_ingredient = None
        current_ingredient_key = None
        current_news = None
        current_offer = None
        current_offer_reseller = None

        for k, v in dic.iteritems():
            if k.split('_')[0] == 'facet':
                if v:
                    facet_ids.append(int(v))
                    request.session.get('form_values')['facet_%s_%s' %(k.split('_')[1], k.split('_')[2])] = k.split('_')[2]
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
            if k == 'current_offer_reseller':
                if v:
                    current_offer_reseller = 'current_offer_reseller'
                    request.session.get('form_values')['current_offer_reseller'] = 'current_offer_reseller'
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

        domain_append = []
        if category_ids:
            domain_append += [('public_categ_ids', 'in', [id for id in category_ids])]
        if facet_ids:
            if model == 'product.product':
                domain_append += [('facet_line_ids.value_ids', '=', id) for id in facet_ids]
            if model == 'product.template':
                domain_append += [('product_variant_ids.facet_line_ids.value_ids', '=', id) for id in facet_ids]
        if ingredient_ids or not_ingredient_ids:
            product_ids = request.env['product.product'].sudo().search_read(
                [('ingredient_ids', '=', id) for id in ingredient_ids] + [('ingredient_ids', '!=', id) for id in not_ingredient_ids], ['id'])
            domain_append.append(('product_variant_ids', 'in', [r['id'] for r in product_ids]))
        if request.session.get('form_values'):
            if request.session.get('form_values').get('current_news') or request.session.get('form_values').get('current_offer') or request.session.get('form_values').get('current_offer_reseller'):
                offer_domain = self.domain_current(model, dic)
                if len(offer_domain) > 0:
                    for d in offer_domain:
                        domain_append.append(d)

        return domain_append

    def domain_current(self, model, dic):
        domain_current = []
        domain_append = []
        if 'current_news' in dic:
            if model == 'product.template':
                product_ids = request.env[model].search([('website_style_ids', 'in', request.env.ref('website_sale.image_promo').id)]).mapped('id')
                product_variants = request.env['product.product'].search([('website_style_ids_variant', 'in', request.env.ref('website_sale.image_promo').id)]).mapped('product_tmpl_id')
                if len(product_variants) > 0:
                    product_ids += product_variants.mapped('id')
            if model == 'product.product':
                product_ids = request.env[model].search([('website_style_ids_variant', 'in', request.env.ref('website_sale.image_promo').id)]).mapped('id')
                product_tmpls = request.env['product.template'].search([('website_style_ids', 'in', request.env.ref('website_sale.image_promo').id)]).mapped('product_variant_ids')
                if len(product_tmpls) > 0:
                    product_ids += product_tmpls.mapped('id')
            if len(product_ids) == 0:
                domain_current.append(('id', '=', 9999999999))
            else:
                domain_current.append(('id', 'in', product_ids))
        if 'current_offer' in dic:
            if model == 'product.template':
                campaign_product_ids = request.env[model].get_campaign_tmpl(for_reseller=False).mapped('id')
                #get product.template that have variants are in current offer
                tmpl = request.env['product.product'].get_campaign_variants(for_reseller=False).mapped('product_tmpl_id')
                if len(tmpl) > 0:
                    for t in tmpl:
                        if t.id not in campaign_product_ids:
                            campaign_product_ids.append(t.id)
            if model == 'product.product':
                campaign_product_ids = request.env[model].get_campaign_variants(for_reseller=False).mapped('id')
                tmpl = request.env['product.template'].get_campaign_tmpl(for_reseller=False)
                if len(tmpl) > 0:
                    for t in tmpl:
                        campaign_product_ids += t.mapped('product_variant_ids').mapped('id')
            if len(campaign_product_ids) == 0 and ('id', '=', 9999999999) not in domain_current:
                domain_current.append(('id', '=', 9999999999))
            else:
                domain_current.append(('id', 'in', campaign_product_ids))
        if 'current_offer_reseller' in dic:
            if request.env.user.partner_id.property_product_pricelist and request.env.user.partner_id.property_product_pricelist.for_reseller:
                if model == 'product.template':
                    campaign_product_reseller_ids = request.env[model].get_campaign_tmpl(for_reseller=True).mapped('id')
                    tmpl = request.env['product.product'].get_campaign_variants(for_reseller=True).mapped('product_tmpl_id')
                    if len(tmpl) > 0:
                        for t in tmpl:
                            if t.id not in campaign_product_reseller_ids:
                                campaign_product_reseller_ids.append(t.id)
                if model == 'product.product':
                    campaign_product_reseller_ids = request.env[model].get_campaign_variants(for_reseller=True).mapped('id')
                    tmpl = request.env['product.template'].get_campaign_tmpl(for_reseller=True)
                    if len(tmpl) > 0:
                        for t in tmpl:
                            campaign_product_reseller_ids += t.product_variant_ids.mapped('id')
                if len(campaign_product_reseller_ids) == 0 and ('id', '=', 9999999999) not in domain_current:
                    domain_current.append(('id', '=', 9999999999))
                else:
                    domain_current.append(('id', 'in', campaign_product_reseller_ids))
        for i in domain_current:
            if domain_current.count(i) > 1:
                domain_current.remove(i)
        if len(domain_current) > 1:
            for d in domain_current:
                if domain_current.index(d) == 0 or (len(domain_current) == 3 and domain_current.index(d) == 1):
                    domain_append.append('|')
                domain_append.append(domain_current[domain_current.index(d)])
        if len(domain_current) == 1:
            domain_append.append(domain_current[0])
        return domain_append

    def dn_shop_set_session(self, model, post, url):
        """Update session for /dn_shop"""
        default_order = 'sold_qty desc'
        if post.get('order'):
            default_order = post.get('order')
            if request.session.get('form_values'):
                request.session['form_values']['order'] = default_order
            request.session['current_order'] = default_order



        if post.get('post_form') and post.get('post_form') == 'ok':
            request.session['form_values'] = post

        request.session['url'] = url
        request.session['chosen_filter_qty'] = self.get_chosen_filter_qty(self.get_form_values())
        request.session['sort_name'] = self.get_chosen_order(self.get_form_values())[0]
        request.session['sort_order'] = self.get_chosen_order(self.get_form_values())[1]



        if post:
            domain = self.get_domain_append(model, post)
        else:
            domain = self.get_domain_append(model, request.session.get('form_values', {}))
        _logger.warn('\n\ndomain: %s\n' % domain)
        request.session['current_domain'] = domain

    # API handling broken for unknown reasons. Decorators not working properly with this method.
    def sale_get_order(self, cr, uid, ids, force_create=False, code=None, update_pricelist=None, context=None):
        env = api.Environment(cr, uid, context)
        sale_order_obj = env['sale.order']
        sale_order_id = request.session.get('sale_order_id')

        #~ if sale_order_id: # Check if order has been tampered on backoffice
            #~ sale_order = sale_order_obj.sudo().browse(sale_order_id)
            #~ if sale_order and sale_order.order_line.filtered(lambda l: l.state not in ['draft']):
                #~ sale_order_id = None

        # Test validity of the sale_order_id
        sale_order = env['sale.order'].sudo().search([('id', '=', sale_order_id)])

        # Find old sale order that is a webshop cart.
        if env.user != env.ref('base.public_user') and not sale_order:
            sale_order = env['sale.order'].sudo().search([
                ('partner_id', '=', env.user.partner_id.id),
                ('section_id', '=', env.ref('website.salesteam_website_sales').id),
                ('state', '=', 'draft'),
            ], limit=1)
            if sale_order:
                request.session['sale_order_id'] = sale_order.id

        # create so if needed
        if not sale_order and (force_create or code):
            values = {
                'user_id': env.user.id,
                'partner_id': env.user.partner_id.id,
                'pricelist_id': env.user.partner_id.property_product_pricelist.id,
                'section_id': env.ref('website.salesteam_website_sales').id,
            }
            sale_order = env['sale.order'].sudo().create(values)
            sale_order.write(env['sale.order'].onchange_partner_id(env.user.partner_id.id)['value'])
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

    def price_formate(self, price):
        if request.env.lang == 'sv_SE':
            return ('%.2f' %price).replace('.', ',')
        else:
            return '%.2f' %price


class WebsiteSale(website_sale):

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
            render_ctx = dict(request.env.context, submit_class='btn btn-primary', submit_txt=_('Pay Now'))
            for acquirer in values['acquirers']:
                acquirer.button = acquirer.with_context(render_ctx).render(
                    '/',
                    order.amount_total,
                    order.pricelist_id.currency_id.id,
                    partner_id=shipping_partner_id,
                    tx_values={
                        'return_url': '/shop/payment/validate',
                    })
        return request.website.render("website_sale.payment", values)

    mandatory_billing_fields = ["name", "phone", "email", "street", "city", "country_id"]

    def show_purchase_button(self, product):
        sale_ok = False
        if product.sudo().sale_ok and product.sudo().instock_percent >= 50.0 and request.env.user.partner_id.commercial_partner_id.property_product_pricelist.for_reseller:
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
        _logger.warn('checkout_values super: %s' % (timer() - start))
        if request.env.user != request.website.user_id:
            partner = request.env.user.partner_id
            invoicing_id = int(data.get("invoicing_id", '-2'))
            if invoicing_id == -2:
                order = request.website.sale_get_order(force_create=1)
                invoicing_id = order.partner_invoice_id.id
                if invoicing_id == partner.id:
                    invoicing_id = 0
            invoicings = request.env['res.partner'].sudo().with_context(show_address=1).search([("parent_id", "=", partner.commercial_partner_id.id), '|', ('type', "=", 'invoice'), ('type', "=", 'default')])
            if partner != partner.commercial_partner_id:
                shippings = set(res.get('shippings', []))
                shippings |= set([r for r in request.env['res.partner'].with_context(show_address=True).search([("parent_id", "=", partner.commercial_partner_id.id), '|', ('type', "=", 'delivery'), ('type', "=", 'standard')])])
                shippings |= set([partner.with_context(show_address=True).commercial_partner_id])
                invoicings |= partner.sudo().commercial_partner_id
                res['shippings'] = shippings
            res['invoicings'] = invoicings.sudo()
            res['invoicing_id'] = invoicing_id
            res['checkout']['invoicing_id'] = invoicing_id
        _logger.warn('checkout_values: %s' % (timer() - start))
        return res

    #_logger.warn(':%s' % (timer() - start))
    def checkout_form_save(self, checkout):
        start = timer()


        order = request.website.sale_get_order(force_create=1)

        orm_partner = request.env['res.partner']
        orm_user = request.env['res.users']
        order_obj = request.env['sale.order'].sudo()

        partner_lang = request.lang if request.lang in [lang.code for lang in request.website.language_ids] else None

        _logger.warn('1:%s' % (timer() - start))
        # set partner_id
        partner_id = None
        if request.env.user != request.website.user_id:
            partner_id = request.env.user.partner_id
        elif order.partner_id:
            user_ids = request.env['res.users'].sudo().search(
                [("partner_id", "=", order.partner_id.id)], active_test=False)
            if not user_ids or request.website.user_id not in user_ids:
                partner_id = order.partner_id
        _logger.warn('2:%s' % (timer() - start))

        order_info = {
            'partner_id': partner_id.id,
            'message_follower_ids': [(4, partner_id.id), (3, request.website.partner_id.id)],
            'partner_invoice_id': checkout.get('invoicing_id') or partner_id.id,
            'date_order': fields.Datetime.now(),
        }
        order_info.update(order.onchange_partner_id(partner_id.id)['value'])
        address_change = order.onchange_delivery_id(order.company_id.id, partner_id.id,
                                                        checkout.get('shipping_id'), None)['value']
        order_info.update(address_change)
        _logger.warn('5:%s' % (timer() - start))
        if address_change.get('fiscal_position'):
            fiscal_update = order.onchange_fiscal_position(address_change['fiscal_position'],
                                                               [(4, l.id) for l in order.order_line])['value']
            order_info.update(fiscal_update)
        _logger.warn('6:%s' % (timer() - start))
        order_info.pop('user_id')
        order_info.update(partner_shipping_id=checkout.get('shipping_id') or partner_id.id)
        _logger.warn('7:%s' % (timer() - start))
        order.sudo().write(order_info)
        _logger.warn('8:%s' % (timer() - start))









        #super(WebsiteSale, self).checkout_form_save(checkout)
        _logger.warn('checkout_form_save super:%s' % (timer() - start))
        #~ order = request.website.sale_get_order(force_create=1)
        #~ order.date_order = fields.Datetime.now()
        #~ partner_invoice_id = checkout.get('invoicing_id') or request.env.user.partner_id.id
        #~ if order.partner_invoice_id.id != partner_invoice_id:
            #~ order.write({'partner_invoice_id': partner_invoice_id})

        _logger.warn('checkout_form_save:%s' % (timer() - start))

    def get_attribute_value_ids(self, product):
        def get_sale_start(product):
            if product.sale_ok:
                if product.sale_start and not product.sale_end and product.sale_start > fields.Date.today():
                    return int(product.sale_start.replace('-', ''))
            else:
                if product.sale_start and product.sale_start > fields.Date.today():
                    return int(product.sale_start.replace('-', ''))
            return 0
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
                attribute_value_ids.append([p.id, [v.id for v in p.attribute_value_ids if v.attribute_id.id in visible_attrs], p.price, price, p.recommended_price, 1 if (p.sale_ok and request.env.user != request.env.ref('base.public_user')) else 0, get_sale_start(p)])
        else:
            attribute_value_ids = [[p.id, [v.id for v in p.attribute_value_ids if v.attribute_id.id in visible_attrs], p.price, p.lst_price, p.recommended_price, 1 if (p.sale_ok and request.env.user != request.env.ref('base.public_user')) else 0, get_sale_start(p)] for p in product.sudo().product_variant_ids]

        return attribute_value_ids

    def get_domain_append(self, model, dic):
        facet_ids = []
        category_ids = []
        ingredient_ids = []
        not_ingredient_ids = []
        current_ingredient = None
        current_ingredient_key = None
        current_news = None
        current_offer = None
        current_offer_reseller = None

        for k, v in dic.iteritems():
            if k.split('_')[0] == 'facet':
                if v:
                    facet_ids.append(int(v))
                    request.session.get('form_values')['facet_%s_%s' %(k.split('_')[1], k.split('_')[2])] = k.split('_')[2]
            if k.split('_')[0] == 'category':
                if v:
                     category_ids.append(int(v))
                     request.session.get('form_values')['category_%s' %k.split('_')[1]] = k.split('_')[1]
            if k.split('_')[0] == 'ingredient':
                if v:
                    ingredient_ids.append(int(v))
                    request.session.get('form_values')['ingredient_%s' %k.split('_')[1]] = k.split('_')[1]
            if k == 'current_news':
                if v:
                    current_news = 'current_news'
                    request.session.get('form_values')['current_news'] = 'current_news'
            if k == 'current_offer':
                if v:
                    current_offer = 'current_offer'
                    request.session.get('form_values')['current_offer'] = 'current_offer'
            if k == 'current_offer_reseller':
                if v:
                    current_offer_reseller = 'current_offer_reseller'
                    request.session.get('form_values')['current_offer_reseller'] = 'current_offer_reseller'
            if k.split('_')[0] == 'notingredient':
                if v:
                    not_ingredient_ids.append(int(v))
                    request.session.get('form_values')['notingredient_%s' %k.split('_')[1]] = k.split('_')[1]
            if k == 'current_ingredient':
                if v:
                    current_ingredient = v
                    current_ingredient_key = 'ingredient_' + v
                    ingredient_ids.append(int(v))

        if current_ingredient:
            dic['current_ingredient'] = int(current_ingredient)
            dic[current_ingredient_key] = current_ingredient

        domain_append = []
        if category_ids:
            domain_append += [('public_categ_ids', 'in', [id for id in category_ids])]
        if facet_ids:
            if model == 'product.product':
                domain_append += [('facet_line_ids.value_ids', '=', id) for id in facet_ids]
            if model == 'product.template':
                domain_append += [('product_variant_ids.facet_line_ids.value_ids', '=', id) for id in facet_ids]
        if ingredient_ids or not_ingredient_ids:
            product_ids = request.env['product.product'].sudo().search_read(
                [('ingredient_ids', '=', id) for id in ingredient_ids] + [('ingredient_ids', '!=', id) for id in not_ingredient_ids], ['id'])
            domain_append.append(('product_variant_ids', 'in', [r['id'] for r in product_ids]))
        if request.session.get('form_values'):
            if request.session.get('form_values').get('current_news') or request.session.get('form_values').get('current_offer') or request.session.get('form_values').get('current_offer_reseller'):
                offer_domain = self.domain_current(model, dic)
                if len(offer_domain) > 0:
                    for d in offer_domain:
                        domain_append.append(d)

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

    def domain_current(self, model, dic):
        domain_current = []
        domain_append = []
        if 'current_news' in dic:
            if model == 'product.template':
                product_ids = request.env[model].search([('website_style_ids', 'in', request.env.ref('website_sale.image_promo').id)]).mapped('id')
                product_variants = request.env['product.product'].search([('website_style_ids_variant', 'in', request.env.ref('website_sale.image_promo').id)]).mapped('product_tmpl_id')
                if len(product_variants) > 0:
                    product_ids += product_variants.mapped('id')
            if model == 'product.product':
                product_ids = request.env[model].search([('website_style_ids_variant', 'in', request.env.ref('website_sale.image_promo').id)]).mapped('id')
                product_tmpls = request.env['product.template'].search([('website_style_ids', 'in', request.env.ref('website_sale.image_promo').id)]).mapped('product_variant_ids')
                if len(product_tmpls) > 0:
                    product_ids += product_tmpls.mapped('id')
            if len(product_ids) == 0:
                domain_current.append(('id', '=', 9999999999))
            else:
                domain_current.append(('id', 'in', product_ids))
        if 'current_offer' in dic:
            if model == 'product.template':
                campaign_product_ids = request.env[model].get_campaign_tmpl(for_reseller=False).mapped('id')
                #get product.template that have variants are in current offer
                tmpl = request.env['product.product'].get_campaign_variants(for_reseller=False).mapped('product_tmpl_id')
                if len(tmpl) > 0:
                    for t in tmpl:
                        if t.id not in campaign_product_ids:
                            campaign_product_ids.append(t.id)
            if model == 'product.product':
                campaign_product_ids = request.env[model].get_campaign_variants(for_reseller=False).mapped('id')
                tmpl = request.env['product.template'].get_campaign_tmpl(for_reseller=False)
                if len(tmpl) > 0:
                    for t in tmpl:
                        campaign_product_ids += t.mapped('product_variant_ids').mapped('id')
            if len(campaign_product_ids) == 0 and ('id', '=', 9999999999) not in domain_current:
                domain_current.append(('id', '=', 9999999999))
            else:
                domain_current.append(('id', 'in', campaign_product_ids))
        if 'current_offer_reseller' in dic:
            if request.env.user.partner_id.property_product_pricelist and request.env.user.partner_id.property_product_pricelist.for_reseller:
                if model == 'product.template':
                    campaign_product_reseller_ids = request.env[model].get_campaign_tmpl(for_reseller=True).mapped('id')
                    tmpl = request.env['product.product'].get_campaign_variants(for_reseller=False).mapped('product_tmpl_id')
                    if len(tmpl) > 0:
                        for t in tmpl:
                            if t.id not in campaign_product_reseller_ids:
                                campaign_product_reseller_ids.append(t.id)
                if model == 'product.product':
                    campaign_product_reseller_ids = request.env[model].get_campaign_variants(for_reseller=True).mapped('id')
                    tmpl = request.env['product.template'].get_campaign_tmpl(for_reseller=True)
                    if len(tmpl) > 0:
                        for t in tmpl:
                            campaign_product_reseller_ids += t.product_variant_ids.mapped('id')
                if len(campaign_product_reseller_ids) == 0 and ('id', '=', 9999999999) not in domain_current:
                    domain_current.append(('id', '=', 9999999999))
                else:
                    domain_current.append(('id', 'in', campaign_product_reseller_ids))
        for i in domain_current:
            if domain_current.count(i) > 1:
                domain_current.remove(i)
        if len(domain_current) > 1:
            for d in domain_current:
                if domain_current.index(d) == 0 or (len(domain_current) == 3 and domain_current.index(d) == 1):
                    domain_append.append('|')
                domain_append.append(domain_current[domain_current.index(d)])
        if len(domain_current) == 1:
            domain_append.append(domain_current[0])
        return domain_append




    @http.route([
        '/dn_shop',
        '/dn_shop/page/<int:page>',
        '/dn_shop/category/<model("product.public.category"):category>',
        '/dn_shop/category/<model("product.public.category"):category>/page/<int:page>',
    ], type='http', auth="public", website=True)
    def dn_shop(self, page=0, category=None, search='', **post):
        start_all = timer()
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry

        url = "/dn_shop"
        request.website.dn_shop_set_session('product.template', post, url)

        # This looks like trash left over from /shop

        #~ attrib_list = request.httprequest.args.getlist('attrib')
        #~ _logger.warn('\n\nattrib_list: %s\npost: %s\n' % (attrib_list, post))
        #~ attrib_values = [map(int, v.split("-")) for v in attrib_list if v]
        #~ attrib_set = set([v[1] for v in attrib_values])
        #~ domain = self._get_search_domain(search, category, attrib_values)

        domain_finished = timer()

        if category:
            if not request.session.get('form_values'):
                request.session['form_values'] = {'category_%s' %int(category): '%s' %int(category)}
            request.session['form_values'] = {'category_%s' %int(category): '%s' %int(category)}
            self.get_form_values()['category_' + str(int(category))] = str(int(category))

        if not context.get('pricelist'):
            pricelist = self.get_pricelist()
            context['pricelist'] = int(pricelist)
        else:
            pricelist = pool.get('product.pricelist').browse(cr, uid, context['pricelist'], context)


        if search:
            post["search"] = search
        #~ if attrib_list:
            #~ post['attrib'] = attrib_list

        search_start = timer()
        domain = request.session.get('current_domain')
        default_order = request.session.get('default_order')
        products = request.env['product.template'].with_context(pricelist=pricelist.id).search_read(domain, fields=['id', 'name', 'use_tmpl_name', 'default_code', 'access_group_ids', 'dv_ribbon', 'is_offer_product_reseller', 'is_offer_product_consumer', 'dv_image_src', 'dv_name', 'dv_default_code', 'dv_recommended_price', 'dv_price_45', 'dv_price_20', 'dv_price_tax', 'website_style_ids', 'dv_description_sale'], limit=PPG, order=default_order)

        #~ _logger.error('timer %s' % (timer() - start))  0.05 sek
        search_end = timer()
        #~ request.env['product.template'].get_all_variant_data(products)   2 sek
        #~ _logger.error('timer get_all_datra %s' % (timer() - start))

        style_obj = pool['product.style']
        style_ids = style_obj.search(cr, uid, [], context=context)
        styles = style_obj.browse(cr, uid, style_ids, context=context)

        category_obj = pool['product.public.category']
        category_ids = category_obj.search(cr, uid, [('parent_id', '=', False)], context=context)
        categs = category_obj.browse(cr, uid, category_ids, context=context)

        attributes_obj = request.registry['product.attribute']
        attributes_ids = attributes_obj.search(cr, uid, [], context=context)
        attributes = attributes_obj.browse(cr, uid, attributes_ids, context=context)

        #~ from_currency = pool.get('product.price.type')._get_field_currency(cr, uid, 'list_price', context)
        #~ to_currency = pricelist.currency_id
        #~ compute_currency = lambda price: pool['res.currency']._compute(cr, uid, from_currency, to_currency, price, context=context)

        values = {
            'search': search,
            'category': category,
            #~ 'attrib_values': attrib_values,
            #~ 'attrib_set': attrib_set,
            'pricelist': pricelist,
            'products': products,
            #~ 'bins': table_compute().process(products),
            'rows': PPR,
            'styles': styles,
            'categories': categs,
            'attributes': attributes,
            #~ 'compute_currency': compute_currency,
            'is_reseller': request.env.user.partner_id.property_product_pricelist.for_reseller,
            #~ 'keep': keep,
            'url': url,
            #~ 'style_in_product': lambda style, product: style.id in [s.id for s in product.website_style_ids],
            #~ 'attrib_encode': lambda attribs: werkzeug.url_encode([('attrib',i) for i in attribs]),
            'current_ingredient': request.env['product.ingredient'].browse(post.get('current_ingredient')),
            'shop_footer': True,
            'page_lang': request.env.lang,
        }
        _logger.error('to continue to qweb timer %s\ndomain: %s\npricelist: %s\nsearch: %s\nvalues: %s' % (timer() - start_all, domain_finished - start_all, search_start - domain_finished, search_end - search_start, timer() - search_end))
        render_start = timer()
        #~ re = request.website.render("webshop_dermanord.products", values)
        #~ _logger.warn(re.render())
        #~ view_obj = request.env["ir.ui.view"]
        #~ res = request.env['ir.qweb'].render("webshop_dermanord.products", values, loader=view_obj.loader("webshop_dermanord.products"))
        #~ _logger.warn(re)
        #~ start = timer()
        _logger.error('rendered finished %s' % (timer() - render_start))

        return request.website.render("webshop_dermanord.products", values)

    @http.route(['/dn_shop_json_grid'], type='json', auth='public', website=True)
    def dn_shop_json_grid(self, page=0, **kw):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        start_time = timer()
        if not context.get('pricelist'):
            pricelist = self.get_pricelist()
            context['pricelist'] = int(pricelist)
        else:
            pricelist = pool.get('product.pricelist').browse(cr, uid, context['pricelist'], context)

        domain = request.session.get('current_domain')
        order = request.session.get('current_order')
        search_start = timer()
        # relist which product templates the current user is allowed to see
        # TODO: always get same product in the last?? why?

        products = request.env['product.template'].with_context(pricelist=pricelist.id).search_read(domain, limit=6, offset=21+int(page)*6, fields=['id', 'name', 'use_tmpl_name', 'default_code', 'access_group_ids', 'dv_ribbon', 'is_offer_product_reseller', 'is_offer_product_consumer', 'dv_image_src', 'dv_name', 'dv_default_code', 'dv_recommended_price', 'dv_price_45', 'dv_price_20', 'dv_price_tax', 'website_style_ids', 'dv_description_sale', 'product_variant_ids'], order=order)

        search_end = timer()
        _logger.warn('search end: %s' %(timer() - start_time))

        products_list = []
        is_reseller = False
        currency = ''

        partner_pricelist = request.env.user.partner_id.property_product_pricelist
        if partner_pricelist:
            currency = partner_pricelist.currency_id.name
            if partner_pricelist.for_reseller:
                is_reseller = True

        for product in products:
            #~ image_src = ''

            #those style options only can be set on product.template
            style_options = ''
            for style in request.env['product.style'].search([]):
                style_options += '<li class="%s"><a href="#" data-id="%s" data-class="%s">%s</a></li>' %('active' if style.id in product['website_style_ids'] else '', style.id, style.html_class, style.name)

            products_list.append({
                'product_href': '/dn_shop/product/%s' %product['id'],
                'product_id': product['id'],
                'product_name': product['dv_name'],
                'is_offer_product': product['is_offer_product_reseller'] if request.env.user.partner_id.property_product_pricelist.for_reseller else product['is_offer_product_consumer'],
                'style_options': style_options,
                'grid_ribbon_style': 'dn_product_div %s' %product['dv_ribbon'],
                'product_img_src': product['dv_image_src'],
                'price': "%.2f" %  product['dv_price'],
                'price_tax': "%.2f" % product['dv_price_tax'],
                'list_price_tax': "%.2f" % product['dv_recommended_price'],
                'currency': currency,
                'rounding': request.website.pricelist_id.currency_id.rounding,
                'is_reseller': 'yes' if is_reseller else 'no',
                'default_code': product['dv_default_code'],
                'description_sale': product['dv_description_sale'],
                'product_variant_ids': True if product['product_variant_ids'] else False,
            })

        values = {
            'products': products_list,
            #~ 'page_count': int(math.ceil(float(request.session.get('product_count')) / float(PPG))),
        }
        _logger.warn('end time: %s' %(timer() - search_end))
        return values

    @http.route(['/dn_shop_json_list'], type='json', auth='public', website=True)
    def dn_shop_json_list(self, page=0, **kw):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        sale_ribbon = request.env.ref('website_sale.image_promo')
        if not context.get('pricelist'):
            pricelist = self.get_pricelist()
            context['pricelist'] = int(pricelist)
        else:
            pricelist = pool.get('product.pricelist').browse(cr, uid, context['pricelist'], context)

        url = "/dn_list"

        domain = request.session.get('current_domain')
        default_order = request.session.get('default_order')

        # relist which product templates the current user is allowed to see
        #~ products = request.env['product.product'].with_context(pricelist=pricelist.id).search(domain, limit=PPG, offset=(int(page)+1)*PPG, order=order) #order gives strange result
        products = request.env['product.product'].with_context(pricelist=pricelist.id).search_read(domain, fields=['id', 'name', 'campaign_ids', 'attribute_value_ids', 'default_code', 'price_45', 'price_20', 'recommended_price', 'is_offer_product_reseller', 'is_offer_product_consumer', 'website_style_ids_variant', 'sale_ok', 'sale_start', 'product_tmpl_id'], limit=10, offset=(PPG+1) if page == 1 else (int(page)+1)*10, order=default_order)

        products_list = []
        partner_pricelist = request.env.user.partner_id.property_product_pricelist
        currency = ''
        is_reseller = False
        if partner_pricelist:
            currency = partner_pricelist.currency_id.name
            if partner_pricelist.for_reseller:
                is_reseller = True

        #~ for product in products:
            #~ is_reseller = False
            #~ currency = ''
            #~ if partner_pricelist:
                #~ currency = partner_pricelist.currency_id.name
                #~ if partner_pricelist.for_reseller:
                    #~ is_reseller = True
            #~ attributes = product.attribute_value_ids.mapped('name')
            #~ purchase_phase = None
            #~ if len(product.campaign_ids) > 0:
                #~ if len(product.campaign_ids[0].mapped('phase_ids').filtered(lambda p: p.reseller_pricelist and fields.Date.today() >= p.start_date  and fields.Date.today() <= p.end_date)) > 0:
                    #~ purchase_phase = product.campaign_ids[0].mapped('phase_ids').filtered(lambda p: p.reseller_pricelist and fields.Date.today() >= p.start_date  and fields.Date.today() <= p.end_date)[0]
            #~ else:
                #~ if len(product.product_tmpl_id.campaign_ids) > 0:
                    #~ if len(product.product_tmpl_id.campaign_ids[0].mapped('phase_ids').filtered(lambda p: p.reseller_pricelist and fields.Date.today() >= p.start_date  and fields.Date.today() <= p.end_date)) > 0:
                        #~ purchase_phase = product.product_tmpl_id.campaign_ids[0].mapped('phase_ids').filtered(lambda p: p.reseller_pricelist and fields.Date.today() >= p.start_date  and fields.Date.today() <= p.end_date)[0]
            #~ _logger.warn('%s :: %s' %(sale_ribbon, product.website_style_ids))

        for p in products:
            p_start = timer()
            if len(p['campaign_ids']) > 0:
                phases = request.env['crm.tracking.campaign'].browse(p['campaign_ids'][0]).mapped('phase_ids').filtered(lambda p: p.reseller_pricelist and fields.Date.today() >= p.start_date  and fields.Date.today() <= p.end_date)
                if len(phases) > 0:
                    p['purchase_phase'] = {
                        'start_date': phases[0].start_date,
                        'end_date': phases[0].end_date,
                        'phase': len(phases) > 0,
                    }
                else:
                    p['purchase_phase'] = {'phase': False}
            else:
                tmpl = request.env['product.template'].search_read([('id', '=', p.get('product_tmpl_id', [0])[0])], ['campaign_ids'])
                if len(tmpl[0]['campaign_ids']) > 0:
                    phases = request.env['crm.tracking.campaign'].browse(tmpl[0]['campaign_ids'][0][0]).mapped('phase_ids').filtered(lambda p: p.reseller_pricelist and fields.Date.today() >= p.start_date  and fields.Date.today() <= p.end_date)
                    if len(phases) > 0:
                        p['purchase_phase'] = {
                            'date_start': phases[0].campaign_id.date_start,
                            'end_date': phases[0].campaign_id.end_date,
                            'phase': len(phases) > 0,
                        }
                else:
                    p['purchase_phase'] = {'phase': False}

            p['attribute_value_ids'] = [name['name'] for name in request.env['product.attribute.value'].search_read([('id', 'in', p['attribute_value_ids'])], ['name'])]
            product_ribbon = ' '.join([pro['html_class'] for pro in request.env['product.style'].search_read([('id', 'in', p.get('website_style_ids_variant', []))], ['html_class'])])
            if product_ribbon == '':
                tmpl = request.env['product.template'].search_read([('id', 'in', [t[0] for t in [p.get('product_tmpl_id', [])]])], ['website_style_ids'])
                if tmpl:
                    product_ribbon = ' '.join([pro['html_class'] for pro in request.env['product.style'].search_read([('id', 'in', tmpl[0].get('website_style_ids', []))], ['html_class'])])
            p['get_this_variant_ribbon'] = product_ribbon

            if request.env.user.partner_id.property_product_pricelist.name == u'Återförsäljare 45':
                price = p['price_45']
                #~ tax = p['tax_45']
            elif request.env.user.partner_id.property_product_pricelist.name == 'Special 20':
                price = p['price_20']
                #~ tax = p['tax_20']
            else:
                price = request.env['product.product'].browse(p['id']).price
                #tax = sum(map(lambda x: x.get('amount', 0.0), request.env['product.product'].browse(p['id']).taxes_id.compute_all(price, 1, None, self.env.user.partner_id)['taxes']))

            products_list.append({
                'lst_ribbon_style': 'tr_lst %s' %p['get_this_variant_ribbon'],
                'variant_id': p['id'],
                'product_href': '/dn_shop/variant/%s' %p['id'],
                'product_name': p['name'],
                'is_news_product': True if sale_ribbon in p['website_style_ids_variant'] else False,
                'is_offer_product': p['is_offer_product_reseller'] if request.env.user.partner_id.property_product_pricelist.for_reseller else p['is_offer_product_consumer'],
                'purchase_phase': True if p['purchase_phase']['phase'] else False,
                #~ 'product_name_col': 'product_price col-md-6 col-sm-6 col-xs-12' if p['purchase_phase']['phase'] else 'product_price col-md-8 col-sm-8 col-xs-12',
                'product_name_col': 'product_name' if p['purchase_phase']['phase'] else 'product_name',
                'purchase_phase_start_date': p['purchase_phase']['start_date'] if p['purchase_phase']['phase'] else '',
                'purchase_phase_end_date': p['purchase_phase']['end_date'] if p['purchase_phase']['phase'] else '',
                'recommended_price': "%.2f" % p['recommended_price'],
                'price': request.website.price_formate(price),
                #~ 'tax': "%.2f" %request.website.price_formate(tax),
                'currency': currency,
                'rounding': request.website.pricelist_id.currency_id.rounding,
                'is_reseller': 'yes' if is_reseller else 'no',
                'default_code': p['default_code'] or '',
                'attribute_value_ids': (' , ' + ' , '.join(p['attribute_value_ids'])) if len(p['attribute_value_ids']) > 0 else '',
                'sale_ok': p['sale_ok'],
                'sale_start': p['sale_start'],
                'load_time': timer() - p_start,
            })

        values = {
            'products': products_list,
            'url': url,
            'page_count': int(math.ceil(float(request.session.get('product_count')) / float(PPG))),
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
            'show_purchase_button': self.show_purchase_button(product.get_default_variant()),
            'get_attribute_value_ids': self.get_attribute_value_ids,
            'is_reseller': request.env.user.partner_id.property_product_pricelist.for_reseller,
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
        url = "/dn_list"
        request.website.dn_shop_set_session('product.product', post, url)

        if category:
            if not request.session.get('form_values'):
                request.session['form_values'] = {'category_%s' %int(category): '%s' %int(category)}
            request.session['form_values'] = {'category_%s' %int(category): '%s' %int(category)}
            self.get_form_values()['category_' + str(int(category))] = str(int(category))

        if not context.get('pricelist'):
            pricelist = self.get_pricelist()
            context['pricelist'] = int(pricelist)
        else:
            pricelist = pool.get('product.pricelist').browse(cr, uid, context['pricelist'], context)

        if search:
            post["search"] = search

        domain = request.session.get('current_domain')
        default_order = request.session.get('default_order')
        products = request.env['product.product'].with_context(pricelist=pricelist.id).search_read(domain, fields=['id', 'name', 'campaign_ids', 'attribute_value_ids', 'default_code', 'price_45', 'price_20', 'recommended_price', 'is_offer_product_reseller', 'is_offer_product_consumer', 'website_style_ids_variant', 'product_tmpl_id'], limit=PPG, order=default_order)
        request.session['product_count'] = 2000

        from_currency = pool.get('product.price.type')._get_field_currency(cr, uid, 'list_price', context)
        to_currency = pricelist.currency_id
        compute_currency = lambda price: pool['res.currency']._compute(cr, uid, from_currency, to_currency, price, context=context)

        if post.get('post_form') and post.get('post_form') == 'ok':
            request.session['form_values'] = post

        request.session['url'] = url
        request.session['chosen_filter_qty'] = self.get_chosen_filter_qty(self.get_form_values())
        request.session['sort_name'] = self.get_chosen_order(self.get_form_values())[0]
        request.session['sort_order'] = self.get_chosen_order(self.get_form_values())[1]
        value_start = timer()

        for p in products:
            if len(p['campaign_ids']) > 0:
                phases = request.env['crm.tracking.campaign'].browse(p['campaign_ids'][0]).mapped('phase_ids').filtered(lambda p: p.reseller_pricelist)
                if len(phases) > 0:
                    p['purchase_phase'] = {
                        'start_date': phases[0].start_date,
                        'end_date': phases[0].end_date,
                    }
                else:
                    p['purchase_phase'] = {}
            p['attribute_value_ids'] = [name['name'] for name in request.env['product.attribute.value'].search_read([('id', 'in', p['attribute_value_ids'])], ['name'])]
            product_ribbon = ' '.join([pro['html_class'] for pro in request.env['product.style'].search_read([('id', 'in', p.get('website_style_ids_variant', []))], ['html_class'])])
            if product_ribbon == '':
                tmpl = request.env['product.template'].search_read([('id', '=', p.get('product_tmpl_id', [0])[0])], ['website_style_ids'])
                if tmpl:
                    product_ribbon = ' '.join([pro['html_class'] for pro in request.env['product.style'].search_read([('id', 'in', tmpl[0].get('website_style_ids', []))], ['html_class'])])
            p['get_this_variant_ribbon'] = product_ribbon

        values = {
            'search': search,
            'pricelist': pricelist,
            'products': products,
            'rows': PPR,
            'compute_currency': compute_currency,
            'url': url,
            'current_ingredient': request.env['product.ingredient'].browse(post.get('current_ingredient')),
            'shop_footer': True,
        }
        _logger.warn('after value: %s' %(timer()-value_start))
        start_render = timer()
        res = request.website.render("webshop_dermanord.products_list_reseller_view", values)
        _logger.warn('after render: %s' %(timer()-start_render))
        return res

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
            'show_purchase_button': self.show_purchase_button(variant),
            'get_attribute_value_ids': self.get_attribute_value_ids,
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

    @http.route(['/shop/cart/update'], type='http', auth="public", methods=['POST'], website=True)
    def cart_update(self, product_id, add_qty=1, set_qty=0, **kw):
        cr, uid, context = request.cr, request.uid, request.context
        request.website.with_context(supress_checks=True).sale_get_order(force_create=1)._cart_update(product_id=int(product_id), add_qty=float(add_qty), set_qty=float(set_qty))
        if kw.get('return_url'):
            return request.redirect(kw.get('return_url'))
        return request.redirect("/shop/cart")

    @http.route(['/dn_list/cart/update'], type='json', auth="public", website=True)
    def dn_cart_update(self, product_id, add_qty=1, set_qty=0, **kw):
        cr, uid, context = request.cr, request.uid, request.context
        try:
            res = request.website.with_context(supress_checks=True).sale_get_order(force_create=1)._cart_update(product_id=int(product_id), add_qty=float(add_qty), set_qty=float(set_qty))
            return [request.website.price_formate(res['amount_untaxed']), res['cart_quantity']]
        except Exception as e:
            _logger.error('Error in customer order: %s' %e)
            return e
        else:
            return None

    @http.route(['/website_sale_update_cart'], type='json', auth="public", website=True)
    def website_sale_update_cart(self):
        order = request.website.sale_get_order()
        res = {'amount_total': '0.00', 'cart_quantity': '0'}
        if order:
            res['amount_total'] = request.website.price_formate(order.amount_total)
            res['cart_quantity'] = order.cart_quantity
        return res

class webshop_dermanord(http.Controller):

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
            product = request.env['product.product'].browse(int(product_id))
            if product:
                image_ids = product.image_ids.filtered(lambda i: product in i.product_variant_ids)
                default_image_ids = product.image_ids.filtered(lambda i: len(i.product_variant_ids) == 0)
                images = []

                if len(image_ids) > 0:
                    images = image_ids.mapped('id') + default_image_ids.mapped('id')
                else:
                    images.append(0)
                    for d in default_image_ids.mapped('id'):
                        images.append(d)
                    #~ images = default_image_ids.mapped('id') or None

                facets = {}
                if len(product.facet_line_ids) > 0:
                    for line in product.facet_line_ids:
                        facets[line.facet_id.name] = []
                        for v in line.value_ids:
                            facets.get(line.facet_id.name).append([line.facet_id.id, v.name, v.id])

                ingredients_description = product.ingredients or ''
                ingredients = []
                product_ingredients = request.env['product.ingredient'].search([('product_ids', 'in', product_id)], order='sequence')
                if len(product_ingredients) > 0:
                    for i in product_ingredients:
                        ingredients.append([i.id, i.name])

                instock = ''
                in_stock = True
                if not product.is_mto_route:
                    if product.sale_ok:
                        if product.instock_percent > 100.0:
                            instock = _('In stock')
                        elif product.instock_percent >= 50.0 and product.instock_percent <= 100.0:
                            instock = _('Few in stock')
                        elif product.instock_percent < 50.0:
                            instock = _('Shortage')
                            in_stock = False

                offer = False
                if product in product.get_campaign_variants(for_reseller=request.env.user.partner_id.commercial_partner_id.property_product_pricelist.for_reseller):
                    offer = True
                elif product.product_tmpl_id in product.product_tmpl_id.get_campaign_tmpl(for_reseller=request.env.user.partner_id.commercial_partner_id.property_product_pricelist.for_reseller):
                    offer = True

                value['instock'] = instock
                value['images'] = images
                value['facets'] = facets
                value['ingredients_description'] = ingredients_description
                value['ingredients'] = ingredients
                value['default_code'] = product.default_code or ''
                value['public_desc'] = product.public_desc or ''
                value['use_desc'] = product.use_desc or ''
                value['reseller_desc'] = (product.reseller_desc or '') if is_reseller else ''
                value['offer'] = offer
                value['offer_text'] = _('Offer')
                value['news_text'] = _('News')
                value['ribbon'] = request.env.ref('website_sale.image_promo') in product.website_style_ids_variant if len(product.website_style_ids_variant) > 0 else (request.env.ref('website_sale.image_promo') in product.product_tmpl_id.website_style_ids)
                value['sale_ok'] = True if (product.sale_ok and in_stock and request.env.user.partner_id.commercial_partner_id.property_product_pricelist.for_reseller) else False
        return value

    @http.route(['/get/product_variant_value'], type='json', auth="public", website=True)
    def product_variant_value(self, product_id=None, value_id=None, **kw):
        if product_id and value_id:
            product = request.env['product.template'].browse(int(product_id))
            if product:
                variants = product.product_variant_ids.filtered(lambda v: int(value_id) in v.attribute_value_ids.mapped("id"))
                return variants[0].ingredients if len(variants) > 0 else ''


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
