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
from openerp.exceptions import except_orm
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

class stock_notification(models.Model):
    _name = 'stock.notification'
    _inherit = ['mail.thread']

    product_id = fields.Many2one(comodel_name='product.product', string='Product')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Partner')
    status = fields.Selection(string='Status', selection=[ ('pending', 'Pending'), ('sent', 'Sent') ], default='pending')
    created_datetime = fields.Datetime('Created', select=True, default=lambda self: fields.datetime.now())
    
    @api.multi
    def send_notification(self):
        author = self.env.ref('base.main_partner').sudo()
        template = self.env.ref('webshop_dermanord.stock_notify_message', False)
        
        for notify in self:
               
            ctx = {
                'default_model': 'stock.notification',
                'default_res_id': notify.id,
                'default_use_template': True,
                'default_template_id': template.id,
                'default_composition_mode': 'comment',
                'lang': notify.partner_id.lang,
            }
            composer = self.env['mail.compose.message'].sudo().with_context(ctx).create({})
            composer.send_mail()
        
        self.write({'status' : 'sent'})

    @api.multi
    def send_inactive_notification(self):
        author = self.env.ref('base.main_partner').sudo()
        template = self.env.ref('webshop_dermanord.stock_notify_inactive_message', False)
        
        for notify in self:
               
            ctx = {
                'default_model': 'stock.notification',
                'default_res_id': notify.id,
                'default_use_template': True,
                'default_template_id': template.id,
                'default_composition_mode': 'comment',
                'lang': notify.partner_id.lang,
            }
            composer = self.env['mail.compose.message'].sudo().with_context(ctx).create({})
            composer.send_mail()
        
        self.write({'status' : 'sent'})
        
    @api.model
    def cron_notify(self):
        notifications = self.search([])
        notifications_inactive = self.search([])
        products = notifications.mapped('product_id')
        to_send = self.browse()
        to_send_inactive = self.browse()
        for product in products.filtered('active'):
            if product.get_stock_info(product.id)[0]:
                 to_send |= notifications.filtered(lambda n: n.product_id == product and n.status == 'pending')
        for product in products.filtered(lambda n: not n.active):
            to_send_inactive |= notifications_inactive.filtered(lambda n: n.product_id == product and n.status == 'pending')
        if to_send:
            to_send.send_notification()
        if to_send_inactive:
            to_send_inactive.send_inactive_notification()
            
        self.search([('status', '=', 'sent'), ('message_last_post', '<', fields.Datetime.to_string(datetime.now() + timedelta(days=-7)))]).unlink()
        

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
                    o.object_id._is_offer_product()
                elif o.object_id._name == 'product.product':
                    o.object_id.product_tmpl_id._is_offer_product()
        return super(crm_tracking_campaign, self).write(vals)

    @api.model
    def create(self, vals):
        res = super(crm_tracking_campaign, self).create(vals)
        for o in res.object_ids:
            if o.object_id._name == 'product.template':
                o.object_id._is_offer_product()
            elif o.object_id._name == 'product.product':
                o.object_id.product_tmpl_id._is_offer_product()
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
        res = super(crm_campaign_object, self).create(vals)
        if vals.get('object_id') and vals.get('object_id').split(',')[0] == 'product.template':
            self.env['product.template'].browse(int(vals.get('object_id').split(',')[1]))._is_offer_product()
        elif vals.get('object_id') and vals.get('object_id').split(',')[0] == 'product.product':
            self.env['product.product'].browse(int(vals.get('object_id').split(',')[1])).product_tmpl_id._is_offer_product()
        return res

    @api.multi
    def write(self, vals):
        for r in self:
            if r.object_id and r.object_id._name == 'product.template':
                r.object_id._is_offer_product()
            elif r.object_id and r.object_id._name == 'product.product':
                r.object_id.product_tmpl_id._is_offer_product()
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
    sold_qty = fields.Integer(string='Sold', default=0)
    use_tmpl_name = fields.Boolean(string='Use Template Name', help='When checked. The template name will be used in webshop')
    campaign_changed = fields.Boolean()

    def _auto_init(self, cr, context=None):
        """Install custom sorting functions."""
        res = super(product_template, self)._auto_init(cr, context)
        cr.execute("""CREATE OR REPLACE FUNCTION dn_product_template_price_chart_sort(int, int) RETURNS float
LANGUAGE sql
AS
$$

    SELECT price FROM product_pricelist_chart WHERE pricelist_chart_id = $2 AND product_id IN (SELECT id FROM product_product WHERE product_tmpl_id = $1 AND sale_ok = true and active = true AND website_published = true) ORDER BY price LIMIT 1;
$$;""")
        return res

    def _generate_order_by_inner(self, alias, order_spec, query, reverse_direction=False, seen=None):
        """Handle sort by functions.
        dn_price_chart_sort_{pricelist_chart_id} = sort by prices for the given chart.
        """
        if seen is None:
            seen = set()
        order_by_elements = []
        special_order = []
        if 'dn_price_chart_sort_' in order_spec:
            new_order = []
            for expr in order_spec.split(','):
                if 'dn_price_chart_sort_' in expr:
                    expr = expr.strip().split(' ')
                    order_direction = expr[1].strip().upper() if len(expr) == 2 else ''
                    chart_id = expr[0].split('_')[-1]
                    if not chart_id.isdigit() and order_direction in ('', 'ASC', 'DESC'):
                        raise except_orm(_('AccessError'), _('Invalid "order" specified for dn_price_chart_sort_'))
                    special_order.append((chart_id, order_direction))
                else:
                    new_order.append(expr.strip())
            order_spec = ','.join(new_order)
        if order_spec:
            order_by_elements = super(product_template, self)._generate_order_by_inner(alias, order_spec, query, reverse_direction=reverse_direction, seen=seen)

        for order in special_order:
            order_by_elements.append('dn_product_template_price_chart_sort("%s"."id", %s) %s' % (alias, order[0], order[1]))
        return order_by_elements

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
    def fts_search_suggestion(self):
        """
        Return a search result for search_suggestion.
        """
        res = super(product_template, self).fts_search_suggestion()
        res['event_type_id'] = self.event_type_id and self.event_type_id.id or False
        return res


class ProductProduct(models.Model):
    _inherit = 'product.product'

    #~ so_line_ids = fields.One2many(comodel_name='sale.order.line', inverse_name='product_id')  # performance hog, do we need it?
    sold_qty = fields.Integer(string='Sold', default=0)
    website_style_ids_variant = fields.Many2many(comodel_name='product.style', string='Styles for Variant')
    has_tester = fields.Boolean(string='Has Tester')
    tester_product_id = fields.Many2one(comodel_name='product.product', string='Tester Product')
    tester_min = fields.Float(string='Minimum Quantity', default=6)

    @api.one
    def _fullname(self):
        self.fullname = '%s %s' % (self.name, ', '.join(self.attribute_value_ids.mapped('name')))
    fullname = fields.Char(compute='_fullname')

    def _auto_init(self, cr, context=None):
        """Install custom sorting functions."""
        res = super(ProductProduct, self)._auto_init(cr, context)
        cr.execute("""CREATE OR REPLACE FUNCTION dn_product_product_price_chart_sort(int, int) RETURNS float
LANGUAGE sql
AS
$$
    SELECT price FROM product_pricelist_chart WHERE pricelist_chart_id = $2 AND product_id = $1 LIMIT 1;
$$;""")
        return res

    def _generate_order_by_inner(self, alias, order_spec, query, reverse_direction=False, seen=None):
        """Handle sort by functions.
        dn_price_chart_sort_{pricelist_chart_type_id} = sort by prices for the given chart.
        """
        if seen is None:
            seen = set()
        order_by_elements = []
        special_order = []
        if 'dn_price_chart_sort_' in order_spec:
            new_order = []
            for expr in order_spec.split(','):
                if 'dn_price_chart_sort_' in expr:
                    expr = expr.strip().split(' ')
                    order_direction = expr[1].strip().upper() if len(expr) == 2 else ''
                    chart_id = expr[0].split('_')[-1]
                    if not chart_id.isdigit() and order_direction in ('', 'ASC', 'DESC'):
                        raise except_orm(_('AccessError'), _('Invalid "order" specified for dn_price_chart_sort_'))
                    special_order.append((chart_id, order_direction))
                else:
                    new_order.append(expr.strip())
            order_spec = ','.join(new_order)
        if order_spec:
            order_by_elements = super(ProductProduct, self)._generate_order_by_inner(alias, order_spec, query, reverse_direction=reverse_direction, seen=seen)

        for order in special_order:
            order_by_elements.append('dn_product_product_price_chart_sort("%s"."id", %s) %s' % (alias, order[0], order[1]))
        return order_by_elements

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
        res = super(ProductProduct, self).fts_search_suggestion()
        res['event_type_id'] = self.event_type_id and self.event_type_id.id or False
        return res


class product_facet(models.Model):
    _inherit = 'product.facet'

    @api.multi
    def get_filtered_facets(self, form_values):
        categories = []
        if form_values and len(form_values) > 0:
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

    # ~ @api.multi
    # ~ def price_get(self, prod_id, qty, partner=None):
        # ~ return super(product_pricelist, self).price_get(prod_id, qty, partner)


class product_public_category(models.Model):
    _inherit = 'product.public.category'

    text_hex = fields.Char(string='Text Color (Hex)', help='Text Color in hex', default='#000000')
    bg_hex = fields.Char(string='Background Color (Hex)', help='Background Color in hex', default='#ffffff')
    group_ids = fields.Many2many(comodel_name='res.groups', string='Access groups')

    @api.model
    def check_accessable(self, partner_access_group_ids, category_group_ids):
        accessable = False
        for a in partner_access_group_ids:
            if a in category_group_ids:
                accessable = True
                break
        return accessable

    @api.model
    def get_dn_category_desktop_tree_html(self, parent_categories, mobile):
        return self.dn_category_desktop_tree_html(parent_categories, mobile)

    @api.model
    def dn_category_desktop_tree(self, parent_categories):
        categ_lst = []
        def get_child_categories(categories):
            children = self.env['product.public.category'].search([('parent_id', 'in', categories.mapped('id')), ('website_published', '=', True), ('group_ids', 'in', self.env.user.commercial_partner_id.access_group_ids.mapped('id'))])
            if len(children) > 0:
                categ_lst.append(children)
                get_child_categories(children)
        categ_lst.append(parent_categories)
        get_child_categories(parent_categories)
        return categ_lst

    @api.model
    def dn_category_desktop_tree_html(self, parent_categories, mobile):
        def get_child_categs(categories):
            children = self.env['product.public.category'].search([('parent_id', 'in', categories.mapped('id')), ('website_published', '=', True), ('group_ids', 'in', self.env.user.commercial_partner_id.access_group_ids.mapped('id'))])
            if len(children) > 0:
                return children
            else:
                return []
        def get_last_parent_id(category):
            if category.parent_id:
                return get_last_parent_id(category.parent_id)
            else:
                return category.id
        def get_panel_heading_html(category, mobile, last):
            if self.check_accessable(self.env.user.commercial_partner_id.access_group_ids, category.group_ids):
                parent_categ = category in parent_categories
                parent_categ_bg = ''
                parent_categ_text = ''
                if parent_categ:
                    parent_categ_bg = 'background-color: %s; border: 1px solid #ddd; %s' %(category.bg_hex or '#fff', '' if last else 'border-bottom: none;')
                    parent_categ_text = 'color: %s;' %category.text_hex
                return u"""<div class="panel-heading {category_heading_level}" style="{parent_categ_bg}">
    <h4 class="panel-title parent_category_panel_title container">
        <input type="checkbox" name="{category_name}" value="{category_value}" class="category_checkbox {category_heading_parents_col}" data-category="{desktop_category}" data-parent_category="{desktop_parent_category}" {category_checked}/>
        <span class="{category_title_level}" style="padding-left: 3px; cursor: pointer; {parent_categ_text}">
            {desktop_category_name}
        </span>
        {desktop_category_collapse}
        {desktop_category_filter_match}
    </h4>
</div>""".format(
    parent_categ_bg = parent_categ_bg,
    parent_categ_text = parent_categ_text,
    category_heading_level = 'category_heading_parents' if parent_categ else 'category_heading_children',
    category_heading_parents_col = 'col-md-1 col-sm-1' if parent_categ else '',
    category_name = 'category_%s' %category.id,
    category_value = '%s' %category.id,
    desktop_category = '%s_category_%s' %('mobile' if mobile else 'desktop', category.id),
    desktop_parent_category = get_last_parent_id(category),
    category_checked = 'checked="checked"' if category.id in category_checked else '',
    category_title_level = 'category_parents_style onclick_category col-md-10 col-sm-10' if parent_categ else 'category_children_style onclick_category',
    desktop_category_name = category.name,
    desktop_category_collapse = ('<a data-toggle="collapse" href="#%s_category_%s" class="pull-right %s" style="%s"><i class="desktop_angle fa fa-angle-down"></i></a>' %('mobile' if mobile else 'desktop', category.id, 'col-md-1 col-sm-1' if parent_categ else '', 'padding:0px;' if parent_categ else 'padding: 5px 0px 0px 0px;')) if len(get_child_categs(category)) > 0 else '',
    desktop_category_filter_match = ''
)
            else:
                return ''

        def get_panel_body_html(category, mobile, first_level_children, last, bg):
            if self.check_accessable(self.env.user.commercial_partner_id.access_group_ids, category.group_ids):
                children = get_child_categs(category)
                panel_style = 'background-color: %s; %s %s' %(bg or '#fff', 'border-left: 1px solid #ddd; border-right: 1px solid #ddd;' if first_level_children else '', 'border-bottom: 1px solid #ddd;' if last else '')
                html_code = '<div id="%s_category_%s" class="panel-collapse collapse %s" style="%s"><div class="panel-body %s" style="%s">' %('mobile' if mobile else 'desktop', category.id, 'category_panel_parents' if category in parent_categories else 'category_panel_children', panel_style if category in parent_categories else '', '' if category in parent_categories else 'category_children_panel', 'background-color: %s;' %bg)
                for idx, child in enumerate(children):
                    html_code += get_panel_heading_html(child, mobile, False)
                    html_code += get_panel_body_html(child, mobile, idx == 0, False, bg)
                html_code += '</div></div>'
                return html_code
            else:
                return ''

        current_domain = request.session.get('current_domain')
        form_values = request.session.get('form_values')
        current_category = 0
        category_checked = []
        if current_domain:
            for d in current_domain:
                if d[0] == 'public_categ_ids':
                    current_category = d[2]
        if current_category != 0:
            category_checked = self.env['product.public.category'].search([('id', 'child_of', current_category)]).mapped('id')
        for k,v in form_values.items():
            if k.split('_')[0] == 'category' and v not in category_checked:
                category_checked.append(v)

        html = ''
        all_categories = self.dn_category_desktop_tree(parent_categories)
        if len(all_categories) > 0:
            for idx, category in enumerate(all_categories[0]):
                html += get_panel_heading_html(category, mobile, idx == len(all_categories[0]) -1)
                html += get_panel_body_html(category, mobile, True, idx == len(all_categories[0]) -1, category.bg_hex)
        return html

# ~ <div class="checkbox">
    # ~ <h5>
        # ~ <label>
            # ~ <t t-if="request.session.get('form_values')">
                # ~ <input type="checkbox" t-att-name="'facet_%s_%s' %(facet_value.facet_id.id, facet_value.id)" t-att-value="facet_value.id" t-att="{'checked': '1'} if (request.session.get('form_values').get('facet_%s_%s' %(facet_value.facet_id.id, facet_value.id)) and request.session.get('form_values').get('facet_%s_%s' %(facet_value.facet_id.id, facet_value.id)) == str(facet_value.id)) else {}" />
                # ~ <a href="javascript:void(0)" onclick="submit_facet($(this));">
                    # ~ <t t-esc="facet_value.name" />
                # ~ </a>
            # ~ </t>
            # ~ <t t-if="not request.session.get('form_values')">
                # ~ <input type="checkbox" t-att-name="'facet_%s_%s' %(facet_value.facet_id.id, facet_value.id)" t-att-value="facet_value.id" />
                # ~ <a href="javascript:void(0)" onclick="submit_facet($(this));">
                    # ~ <t t-esc="facet_value.name" />
                # ~ </a>
            # ~ </t>
        # ~ </label>
    # ~ </h5>
# ~ </div>

    @api.model
    def dn_facet_desktop_tree_html(self, mobile):
        current_domain = request.session.get('current_domain')
        facet_value_ids = []
        for domain in current_domain:
            if domain[0] == 'facet_line_ids.value_ids' or domain[0] == 'product_variant_ids.facet_line_ids.value_ids':
                if domain[2] not in facet_value_ids:
                    facet_value_ids.append(domain[2])
        spec = self.env.ref('webshop_dermanord.facet_specialforpackningar')
        rese = self.env.ref('webshop_dermanord.facet_value_reseforpackningar')
        salong = self.env.ref('webshop_dermanord.facet_value_salongsprodukter')
        af_groups_users = self.env.ref('webshop_dermanord.group_dn_af').sudo().mapped('users') | self.env.ref('webshop_dermanord.group_dn_ht').sudo().mapped('users') | self.env.ref('webshop_dermanord.group_dn_spa').sudo().mapped('users') | self.env.ref('webshop_dermanord.group_dn_sk').sudo().mapped('users')
        af = self.env.user in af_groups_users
        html_code = ''
        spec_facet_values = self.env['product.facet.value'].search([('facet_id', '=', spec.id)])
        def get_facet_value_div(facet_value, last):
            checked = ''
            chosen_facet = request.session.get('form_values').get('facet_%s_%s' %(facet_value.facet_id.id, facet_value.id), False)
            if chosen_facet and chosen_facet == str(facet_value.id):
                checked = 'checked="checked"'
            return '<div class="panel-heading" style="border: 1px solid #ddd; %s background-color: #fff;"><h4 class="panel-title container"><input type="checkbox" class="facet_heading_checkbox col-md-1 col-sm-1" name="facet_%s_%s" value="%s" %s/><span class="onrs_style col-md-11 col-sm-11" style="padding-left: 3px; cursor: pointer;" onclick="onclick_submit($(this));">%s</span></h4></div>' %('' if last else 'border-bottom: none;', facet_value.facet_id.id, facet_value.id, facet_value.id, checked, facet_value.name)
        if af:
            spec_vals = spec_facet_values
        else:
            spec_vals = spec_facet_values.filtered(lambda v: v != salong)
        for idx, facet_value in enumerate(spec_vals):
            if idx == len(spec_vals)-1:
                html_code += get_facet_value_div(facet_value, last=True)
            else:
                html_code += get_facet_value_div(facet_value, last=False)
        return html_code


class res_users(models.Model):
    _inherit = 'res.users'

    webshop_type = fields.Selection(selection=[('dn_shop', 'dn_shop'), ('dn_list', 'dn_list')])


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


class SaleOrder(models.Model):
    _inherit='sale.order'
    
    website_order_line = fields.One2many(domain=[('is_delivery', '=', False), ('is_min_order_fee', '=', False), ('is_tester', '=', False)])
    
    @api.one
    def verify_testers(self):
        """Remove any tester products that are invalid."""
        def tester_ok(products, tester):
            for product in products:
                if self.tester_ready(product):
                    return True
            return False
        wol = self.website_order_line
        for tester_line in self.order_line.filtered(lambda l: l.is_tester):
            tester = tester_line.product_id
            products = wol.filtered(lambda l: l.product_id.has_tester and l.product_id.tester_product_id == tester).mapped('product_id')
            if not tester_ok(products, tester):
                tester_line.unlink()
    @api.multi
    def has_tester(self, product):
        """Check if this order contains a tester for the given product."""
        if self.order_line.filtered(lambda l: l.is_tester and l.product_id == product.tester_product_id):
            return True
        return False
    
    @api.multi
    def tester_ready(self, product):
        """Check if we're ready to add the tester for this product."""
        minimum = product.tester_min
        quantity = sum(self.order_line.filtered(lambda l: l.product_id == product and not l.is_tester).mapped('product_uom_qty'))
        return quantity >= minimum
    
    @api.multi
    def onchange_delivery_id(self, company_id, partner_id, delivery_id, fiscal_position):
        """Get the carrier from the delivery address."""
        result = super(SaleOrder, self).onchange_delivery_id(company_id, partner_id, delivery_id, fiscal_position)
        if partner_id:
            dtype = self.env['res.partner'].browse(delivery_id).property_delivery_carrier.id
            if not dtype:
                dtype = self.env['res.partner'].browse(partner_id).property_delivery_carrier.id
            if dtype:
                result['value']['carrier_id'] = dtype
        return result

    @api.multi
    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, tester=False, **kwargs):
        """ Add or set product quantity, add_qty can be negative """
        self.ensure_one()

        product = 0
        quantity = 0
        if self.state != 'draft':
            request.session['sale_order_id'] = None
            raise Warning(_('It is forbidden to modify a sale order which is not in draft status'))

        ticket_id = self.env.context.get("event_ticket_id")
        # Maybe use website_order_line instead?
        if tester:
            line = self.order_line.filtered(lambda l: ((l.product_id.id == product_id)) and l.is_tester)
        else:
            line = self.order_line.filtered(
                lambda l:   ((line_id == l.id) if line_id else (l.product_id.id == product_id)) \
                            and (not ticket_id or l.event_ticket_id.id == ticket_id) \
                            and not l.is_tester)
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
                        partner_id=self.partner_id.id,  # TODO: IS this really needed? Looks like it has to do with the tickets below.
                        fiscal_position=self.fiscal_position.id,
                        qty=set_qty or add_qty,
                    )['value']
            values['agents'] = self.env['sale.order.line'].sudo().with_context(partner_id=self.partner_id.id)._default_agents()
            values['name'] = product.description_sale and "%s\n%s" % (product.display_name, product.description_sale) or product.display_name
            values['product_id'] = product.id
            values['order_id'] = self.id
            values['product_uom_qty'] = set_qty or add_qty
            if tester:
                values.update({
                    'is_tester': True,
                    'discount': 100,
                })
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

        # Do not allow more than 5 if educational purchase    
        if (line.product_id.purchase_type == 'edu') and (quantity > 5):
            quantity = 5

        # Remove zero of negative lines
        if quantity <= 0:
            line.unlink()
        else:
            values = self._website_product_id_change(line.order_id.id, line.product_id.id, qty=quantity, line_id=line.id)
            values['product_uom_qty'] = quantity
            line.write(values)

        return {
                'name': self.name,
                'line_id': line.id,
                'quantity': quantity,
                'cart_quantity': self.cart_quantity,
                'amount_total':self.amount_total,
                'amount_untaxed': self.amount_untaxed,
            }

    @api.multi
    def action_button_confirm(self):
        self.ensure_one()
        if not self.client_order_ref:
            self.client_order_ref = '%s (%s)' %(self.partner_id.name, self.name)
        return super(SaleOrder, self).action_button_confirm()

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    is_tester = fields.Boolean(string='Tester', help="This line contains a tester product.")
    
    @api.multi
    def tester_html_attributes(self):
        """Build HTML attributes for the Add / Remove Tester buttons."""
        res = {
            'data-tester-min': int(self.product_id.tester_min),
            'data-tester-id': self.product_id.tester_product_id.id,
            'data-tester-added': int(self.order_id.has_tester(self.product_id)),
        }
        result = { 'buttons': res }
        # Show/hide add and remove buttons
        result['add'] = 'add-tester'
        if res['data-tester-added'] or not self.order_id.tester_ready(self.product_id):
            result['add'] += ' hidden'
        result['remove'] = 'remove-tester'
        if not res['data-tester-added']:
            result['remove'] += ' hidden'
        # Convert to string, because in the XML we lose the attributes
        # when the value evalutes as False (0 in this case)
        for key, value in res.iteritems():
            res[key] = '%s' % value
        return result
    
    def check_product_lang(self):
        for value in self.product_id.attribute_value_ids:
            lang_attr = self.env.ref("__export__.product_attribute_290")
            if value.attribute_id == lang_attr:
                partner_country = self.order_id.partner_shipping_id.country_id and self.order_id.partner_shipping_id.country_id.code or '*'
                # Check if partners country is tied to an attribute. Otherwise we want to match with the wildcard (*).
                if partner_country not in ' '.join([c for c in lang_attr.value_ids.mapped('color') if c]).split():
                    partner_country = '*'
                if partner_country not in (value.color or '').split():
                    return _("%s appears to not be in your preferred language. Are you sure this is the correct product?") % self.product_id.name
    
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
        sort_name = 'name'
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
        form_values = {}

        for k, v in dic.iteritems():
            if k.split('_')[0] == 'facet':
                if v:
                    group, id = k.split('_')[1:]
                    if not group in facet_ids:
                        facet_ids[group] = []
                    facet_ids[group].append(int(v))
                    form_values['facet_%s_%s' %(group, id)] = id
            if k.split('_')[0] == 'category':
                if v:
                     category_ids.append(int(v))
                     form_values['category_%s' % int(v)] = int(v)
            if k.split('_')[0] == 'ingredient':
                if v:
                    ingredient_ids.append(int(v))
                    form_values['ingredient_%s' %int(v)] = int(v)
            if k == 'current_news':
                if v:
                    current_news = 'current_news'
                    form_values['current_news'] = 'current_news'
            if k == 'current_offer':
                if v:
                    current_offer = 'current_offer'
                    form_values['current_offer'] = 'current_offer'
            if k.split('_')[0] == 'notingredient':
                if v:
                    not_ingredient_ids.append(int(v))
                    form_values['notingredient_%s' % int(v)] = int(v)
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
            # ~ domain_append += [('public_categ_ids', 'in', [id for id in category_ids])]
            category_domain = [('public_categ_ids', 'child_of', id) for id in category_ids]
            category_domain = ['|' for i in range(len(category_domain) - 1)] + category_domain
            domain_append += category_domain
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
        if form_values:
            if form_values.get('current_news') or form_values.get('current_offer'):
                offer_domain = self.domain_current(model, dic)
                if len(offer_domain) > 0:
                    for d in offer_domain:
                        domain_append.append(d)
        request.session['form_values'] = form_values
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
                reseller = request.env.user.partner_id.property_product_pricelist and request.env.user.partner_id.property_product_pricelist.for_reseller or False
                if model == 'product.template':
                    campaign_product_ids = [v['product_id'][0] for v in self.env['crm.tracking.campaign.helper'].sudo().search_read([('for_reseller', '=', reseller), ('country_id', '=', self.env.user.partner_id.commercial_partner_id.country_id.id)], ['product_id',]) if v['product_id']]
                    for t in self.env['crm.tracking.campaign.helper'].sudo().search([('for_reseller', '=', reseller), ('country_id', '=', self.env.user.partner_id.commercial_partner_id.country_id.id)]):
                        campaign_product_ids = campaign_product_ids + t.variant_id.product_tmpl_id.mapped('id')
                if model == 'product.product':
                    campaign_product_ids = [v['variant_id'][0] for v in self.env['crm.tracking.campaign.helper'].sudo().search_read([('for_reseller', '=', reseller), ('country_id', '=', self.env.user.partner_id.commercial_partner_id.country_id.id)], ['variant_id',]) if v['variant_id']]
                    for t in self.env['crm.tracking.campaign.helper'].sudo().search([('for_reseller', '=', reseller), ('country_id', '=', self.env.user.partner_id.commercial_partner_id.country_id.id)]):
                        campaign_product_ids = campaign_product_ids + t.product_id.product_variant_ids.mapped('id')
                if campaign_product_ids:
                    append_domain(domain_current, [('id', 'in', campaign_product_ids)])
                else:
                    append_domain(domain_current, [('id', '=', 0)])
        return [('sale_ok', '=', True), ('dv_name', '!=', 'Error')] + domain_current

    def dn_shop_set_session(self, model, post, url):
        """Update session for /dn_shop"""
        default_order = request.session.get('current_order', 'name asc')
        if post.get('order'):
            default_order = post.get('order')
            if request.session.get('form_values'):
                request.session['form_values']['order'] = default_order
        request.session.update({
            'current_order': default_order,
            'sort_name': default_order.split(' ')[0],
            'sort_order': default_order.split(' ')[1],
        })

        if post.get('post_form') == 'ok':
            request.session['form_values'] = post

        request.session['url'] = url
        request.session['chosen_filter_qty'] = self.get_chosen_filter_qty(self.get_form_values())
        if post:
            request.session['form_values']['current_ingredient'] = post.get('current_ingredient')
            try:
                current_ingredient = post.get('current_ingredient', '0') or '0'
                current_ingredient = current_ingredient.isdigit() and int(current_ingredient) or 0
            except:
                current_ingredient = 0
            request.session['current_ingredient'] = current_ingredient
            domain = self.get_domain_append(model, post)
        else:
            domain = self.get_domain_append(model, request.session.get('form_values', {}))
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

        if code and code != sale_order.pricelist_id.code:
            # _logger.warn("DAER code: %s" % code)
            pricelist_ids = self.pool['product.pricelist'].search(cr, SUPERUSER_ID, [('code', '=', code)], context=context)
            if pricelist_ids:
                pricelist_id = pricelist_ids[0]
                request.session['sale_order_code_pricelist_id'] = pricelist_id
                update_pricelist = True

            pricelist_id = request.session.get('sale_order_code_pricelist_id') or env.user.partner_id.property_product_pricelist.id

            # check for change of partner_id ie after signup
            if sale_order.partner_id.id != env.user.partner_id.id and request.website.partner_id.id != env.user.partner_id.id:
                flag_pricelist = False
                if pricelist_id != sale_order.pricelist_id.id:
                    flag_pricelist = True
                fiscal_position = sale_order.fiscal_position and sale_order.fiscal_position.id or False

                values = sale_order_obj.onchange_partner_id(cr, SUPERUSER_ID, [sale_order_id], env.user.partner_id.id, context=context)['value']
                if values.get('fiscal_position'):
                    order_lines = map(int,sale_order.order_line)
                    values.update(sale_order_obj.onchange_fiscal_position(cr, SUPERUSER_ID, [],
                        values['fiscal_position'], [[6, 0, order_lines]], context=context)['value'])

                values['partner_id'] = env.user.partner_id.id
                sale_order_obj.write(cr, SUPERUSER_ID, [sale_order_id], values, context=context)

                if flag_pricelist or values.get('fiscal_position', False) != fiscal_position:
                    update_pricelist = True

            # update the pricelist
            if update_pricelist:
                values = {'pricelist_id': pricelist_id}
                values.update(sale_order.onchange_pricelist_id(pricelist_id, None)['value'])
                sale_order.write(values)
                for line in sale_order.order_line:
                    if line.exists():
                        sale_order._cart_update(product_id=line.product_id.id, line_id=line.id, add_qty=0)

            # update browse record
            if (code and code != sale_order.pricelist_id.code) or sale_order.partner_id.id !=  env.user.partner_id.id:
                sale_order = sale_order_obj.browse(cr, SUPERUSER_ID, sale_order.id, context=context)

        return sale_order

    def price_format(self, price, dp=None):
        if not dp:
            dp = request.env['res.lang'].search_read([('code', '=', request.env.lang)], ['decimal_point'])
            dp = dp and dp[0]['decimal_point'] or '.'
        return ('%.2f' %price).replace('.', dp)
    
    def dn_handle_webshop_session(self, category, preset, post, require_cat_preset=False):
        """Save session data for /webshop."""
        if preset:
            if preset == 'offer':
                post['current_offer'] = u'current_offer'
            elif preset == 'news':
                post['current_news'] = u'current_news'
            elif preset == 'travel':
                post['facet_44_329'] = u'329'
            elif preset == 'set':
                post['facet_44_331'] = u'331'
        if category:
            post['category_%s' % category.id] = category.id
        if require_cat_preset and not (category or preset):
            return
        if request.env.user.webshop_type == 'dn_list':
            self.dn_shop_set_session('product.product', post, '/dn_list')
        else:
            self.dn_shop_set_session('product.template', post, '/dn_shop')

class WebsiteSale(website_sale):

    FACETS = {}  # Static variable
    dn_cart_lock = Lock()

    @http.route('/webshop_dermanord/add_tester', type='json', auth="user", website=True)
    def add_tester(self, product_id=None, **post):
        """Add a tester product to the customers cart."""
        product = request.env['product.product'].sudo().browse(product_id)
        order = request.website.sale_get_order()
        # Kontrollera och addera tester
        res = {}
        if not (product.has_tester and product.tester_product_id):
            res['message'] = _(u"This product doesn't have a tester.")
            return res
        if not order.tester_ready(product):
            res['not_ready'] = product.tester_product_id.id
            res['message'] = _(u"You need to buy at least %s to order a tester.") % product.tester_min
            return res
        res['added'] = product.tester_product_id.id
        if order.has_tester(product):
            res['message'] = _(u"You have already added a tester for this product.")
            return res
        order._cart_update(product_id=product.tester_product_id.id, set_qty=1, tester=True)
        return res

    @http.route('/webshop_dermanord/remove_tester', type='json', auth="user", website=True)
    def remove_tester(self, product_id=None, **post):
        """Remove a tester product from the customers cart."""
        product = request.env['product.product'].sudo().browse(product_id)
        order = request.website.sale_get_order()
        if not (product.has_tester and product.tester_product_id):
            return {'message': _(u"This product doesn't have a tester.")}
        tester_lines = order.order_line.filtered(lambda l: l.is_tester and l.product_id == product.tester_product_id)
        if tester_lines:
            tester_lines.unlink()
        return {'removed': product.tester_product_id.id}

    @http.route('/webshop_dermanord/stock/notify', type='json', auth="user", website=True)
    def stock_notify(self, product_id=None, **post):
        notify = request.env['stock.notification'].sudo()
        partner = request.env.user.partner_id
        product = request.env['product.product'].browse(product_id)
        if not notify.search([('product_id', '=', product_id), ('partner_id', '=', partner.id), ('status', '=', 'pending')]):
            notify.create({'product_id':product_id, 'partner_id': partner.id})
            return _("A mail will be sent to %s, when %s is back in stock") % (partner.email, product.display_name)
        return _("Your mail is already registered for notifications on this product")
            
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
        _logger.warn('Partner_id (confirm) %s shipping %s invoice %s carrier_id %s' % (order.partner_id,order.partner_shipping_id,order.partner_invoice_id, order.carrier_id))
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
            order.verify_testers()
            if order.partner_shipping_id.id:
                shipping_partner_id = order.partner_shipping_id.id
            else:
                shipping_partner_id = order.partner_invoice_id.id
            order.onchange_delivery_id(order.company_id.id, order.partner_id.id, order.partner_shipping_id.id, order.fiscal_position.id)
            # ~ [1614] NO SHIPPING WHEN ORDERING ONLY EVENT // COURSES
            _logger.warn('order_info[carrier_id] 1085  :%s' % ( order.carrier_id ))
            _logger.warn('\n\n\n <<<<<<< listan ........ 1085 :%s %s' % ( [line.product_id and line.product_id.type == 'service' for line in order.order_line],all([line.product_id and line.product_id.type == 'service' for line in order.order_line]) ) )
            if all([line.product_id and line.product_id.type == 'service' for line in order.order_line]):
                # ~ REMOVE ALL PRODUCTS OF CATEGORY "Alla / Tjänst / Frakt"
                order.order_line.filtered(lambda line: line.product_id.categ_id == request.env.ref('__export__.product_category_9')).unlink()
                order.carrier_id = False
            try:
            # ~ _logger.warn('order_info[carrier_id] 1085  :%s' % ( order.carrier_id )
    
                if order.carrier_id:
                    order.delivery_set()
            except except_orm as e:
                # Couldn't use the customers carrier. Find one that works and report the error.
                original = order.carrier_id
                replacement = None
                for carrier in request.env['delivery.carrier'].browse(order._get_delivery_methods(order)):
                    try:
                        order.carrier_id = carrier
                        order.delivery_set()
                        replacement = carrier
                        break
                    except except_orm:
                        pass
                subject = u"Kunde ej använda %ss leveransmetod på %s" % (order.partner_id.name, order.name)
                body = u"Kund: %s (id %s)\n"\
                       u"Leveransadress: %s (id %s)\n"\
                       u"Leveransmetod: %s (id %s)" % (
                            order.partner_id.name, order.partner_id.id,
                            order.partner_shipping_id.name, order.partner_shipping_id.id,
                            original.name, original.id,
                        )
                if replacement:
                    body += u"\n\nPå order %s har leveransmetoden ersatts med %s (id %s)." % (
                        order.name, replacement.name, replacement.id)
                else:
                    body += u"\n\nKunde ej hitta en fungerande leveransmetod för order %s!" % order.name
                author = request.env.ref('base.partner_root').sudo()
                request.env['mail.message'].sudo().create({
                    'subject': subject,
                    'body': body.replace('\n', '<BR/>'),
                    'author_id': author.id,
                    'res_id': order.partner_id.id,
                    'model': order.partner_id._name,
                    'type': 'notification',
                    'partner_ids': [(4, pid) for pid in order.partner_id.message_follower_ids.mapped('id')],
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
            _logger.warn('\n\ninvoicings: %s\n' % invoicings)
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
        _logger.warn('\n\nres["invoicings"]: %s\n' % res['invoicings'])
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
        # ~ [1614] NO SHIPPING WHEN ORDERING ONLY EVENT // COURSES
        # ~ if len( order.order_line.filtered(lambda line: line.product_id.event_ok ) ) == len(order_info.order_line):
        _logger.warn('order_info[carrier_id] 1280 :%s' % ( order_info['carrier_id'] ) )
        _logger.warn('\n\n\n <<<<<<< listan ........ 1280 :%s' % ( [line.product_id and line.product_id.type == 'service' for line in order.order_line] ) )
        if all([line.product_id and line.product_id.type == 'service' for line in order.order_line ]):
            # ~ REMOVE ALL PRODUCTS OF CATEGORY "Alla / Tjänst / Frakt"
            order.order_line.filtered(lambda line: line.product_id.categ_id == request.env.ref('__export__.product_category_9')).unlink()
            order_info['carrier_id'] = False
        _logger.warn('order_info[carrier_id] 1280 :%s' % ( order_info['carrier_id'] ) )

        order.sudo().write(order_info)

        #super(WebsiteSale, self).checkout_form_save(checkout)
        # ~ _logger.warn('checkout_form_save super:%s' % (timer() - start))
        #~ order = request.website.sale_get_order(force_create=1)
        #~ order.date_order = fields.Datetime.now()
        #~ partner_invoice_id = checkout.get('invoicing_id') or request.env.user.partner_id.id
        #~ if order.partner_invoice_id.id != partner_invoice_id:
            #~ order.write({'partner_invoice_id': partner_invoice_id})

        # ~ _logger.warn('checkout_form_save:%s' % (timer() - start))

    # ~ @http.route([
        # ~ '/dn_shop',
        # ~ '/dn_shop/page/<int:page>',
        # ~ '/dn_shop/category/<model("product.public.category"):category>',
        # ~ '/dn_shop/category/<model("product.public.category"):category>/page/<int:page>',
    # ~ ], type='http', auth="public", website=True)
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
        '/webshop/webshop_type/<string:webshop_type>',
        ], type='http', auth="public", website=True)
    def webshop_webshop_type(self, webshop_type='dn_shop', **post):
        if not (webshop_type in ['dn_shop', 'dn_list'] and request.env.user.commercial_partner_id.property_product_pricelist.for_reseller):
            webshop_type = 'dn_shop'
        request.env.user.webshop_type = webshop_type
        return request.redirect('/webshop')

    @http.route([
        '/webshop',
        '/webshop/category/<model("product.public.category"):category>',
        '/webshop/preset/<string:preset>',
        ], type='http', auth="public", website=True)
    def webshop(self, category=None, search='', preset=None, **post):
        # ~ _logger.warn('\n\ncurrent_order: %s\ncurrent_comain: %s\nform_values: %s\n' % (request.session.get('current_order'), request.session.get('current_domain'), request.session.get('form_values')))
        _logger.warn(post)
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

        # ~ def update_current_domain(model):
            # ~ public_categ_ids = []
            # ~ def get_all_children_category(categ_id):
                # ~ public_categ_ids.append(categ_id)
                # ~ children = request.env['product.public.category'].search([('parent_id', '=', categ_id)])
                # ~ if len(children) > 0:
                    # ~ for c in children:
                        # ~ get_all_children_category(c.id)
            # ~ get_all_children_category(category.id)
            # ~ domain_field = 'public_categ_ids'
            # ~ found_public_categ_ids = False
            # ~ for idx, d in enumerate(request.session.get('current_domain')):
                # ~ if d[0] == 'public_categ_ids':
                    # ~ request.session['current_domain'][idx] = tuple((domain_field, 'in', public_categ_ids)) # replace the public categories to current category and it's child categories
                    # ~ found_public_categ_ids = True
            # ~ if not found_public_categ_ids:
                # ~ request.session['current_domain'].append(tuple((domain_field, 'in', public_categ_ids))) # add categories in the first time

        if request.env.user.webshop_type == 'dn_list':
            request.website.dn_shop_set_session('product.product', post, '/webshop')
            # ~ if category:
                # ~ update_current_domain('product.product')
        else:
            request.website.dn_shop_set_session('product.template', post, '/webshop')
            # ~ if category:
                # ~ update_current_domain('product.template')
        
        request.website.dn_handle_webshop_session(category, preset, post)

        if not request.context.get('pricelist'):
            request.context['pricelist'] = int(self.get_pricelist())
        if search:
            post["search"] = search
        user = request.env['res.users'].browse(request.uid)

                  
        no_product_message = ''
        if request.env.user.webshop_type == 'dn_list' and request.env.user != request.env.ref('base.public_user'):
            products=request.env['product.product'].get_list_row(request.session.get('current_domain'),request.context['pricelist'],limit=PPG, order=request.session.get('current_order'))
        else:
            product_ids = request.env['product.template'].sudo(user).search_read(request.session.get('current_domain'), fields=['name', 'dv_ribbon','is_offer_product_reseller', 'is_offer_product_consumer','dv_image_src',], limit=PPG, order=request.session.get('current_order'),offset=0)
            products=request.env['product.template'].get_thumbnail_default_variant2(request.context['pricelist'],product_ids)
        if len(products) == 0:
            no_product_message = _('Your filtering did not match any results. Please choose something else and try again.')
        pricelist_chart_type_id = request.env['pricelist_chart.type'].sudo().search_read([('pricelist', '=', request.context['pricelist'])], ['id'])[0]['id']
        if request.env.user.webshop_type == 'dn_list' and request.env.user != request.env.ref('base.public_user'):
            return request.website.render("webshop_dermanord.products_list_reseller_view", {
                'title': _('Shop'),
                'search': search,
                'products': products,
                'rows': PPR,
                'url': '/webshop',
                'webshop_type': 'dn_list',
                'current_ingredient': request.env['product.ingredient'].browse(int(post.get('current_ingredient', 0) or 0) or int(request.session.get('current_ingredient', 0) or 0)),
                'shop_footer': True,
                'no_product_message': no_product_message,
                'all_products_loaded': True if len(products) < PPG else False,
                'filter_version': request.env['ir.config_parameter'].get_param('webshop_dermanord.filter_version'),
                'pricelist_chart_type_id': pricelist_chart_type_id,
            })
        else:
            return request.website.render("webshop_dermanord.products", {
                'search': search,
                'category': category,
                'products':  products,
                'rows': PPR,
                'is_reseller': request.env.user.partner_id.property_product_pricelist.for_reseller,
                'url': '/webshop',
                'webshop_type': 'dn_shop',
                'current_ingredient': request.env['product.ingredient'].browse(int(post.get('current_ingredient', 0) or 0) or int(request.session.get('current_ingredient', 0) or 0)),
                'shop_footer': True,
                'page_lang': request.env.lang,
                'no_product_message': no_product_message,
                'all_products_loaded': True if len(products) < PPG else False,
                'filter_version': request.env['ir.config_parameter'].get_param('webshop_dermanord.filter_version'),
                'pricelist_chart_type_id': pricelist_chart_type_id,
            })

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

    # ~ @http.route(['/get/product_variant_value'], type='json', auth="public", website=True)
    # ~ def product_variant_value(self, product_id=None, value_id=None, **kw):
        # ~ if product_id and value_id:
            # ~ product = request.env['product.template'].browse(int(product_id))
            # ~ if product:
                # ~ variants = product.product_variant_ids.filtered(lambda v: int(value_id) in v.attribute_value_ids.mapped("id"))
                # ~ return variants[0].ingredients if len(variants) > 0 else ''

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

    @http.route(['/shop/order/client_order_ref'], type='json', auth="public", website=True)
    def order_note(self, client_order_ref, **post):
        order = request.website.sale_get_order()
        if order:
            order.sudo().client_order_ref = client_order_ref

    # ~ @http.route(['/validate_attibute_value'], type='json', auth="public", website=True)
    # ~ def validate_attibute_value(self, product_id=0, attribute_value_id=0, attribute_value_list=[], **kw):
        # ~ attribute_value_list = map(int, attribute_value_list)
        # ~ product = request.env['product.template'].browse(int(product_id))
        # ~ if product:
            # ~ # variant found with all matched attributes
            # ~ if len(product.product_variant_ids.with_context(att_value_list=sorted(attribute_value_list)).filtered(lambda v: sorted(v.attribute_value_ids.mapped('id')) == v.env.context.get('att_value_list'))) == 1:
                # ~ return map(str, attribute_value_list)
            # ~ # variant not found with matched attributes, return variant with chosen attribute or the matched with other attributes in attribute_value_list
            # ~ else:
                # ~ variant = product.product_variant_ids.with_context(att_value_id=int(attribute_value_id)).filtered(lambda v: v.env.context.get('att_value_id') in v.attribute_value_ids.mapped('id'))
                # ~ if len(variant) == 1:
                    # ~ if len(variant.attribute_value_ids) == 1:
                        # ~ return [str(attribute_value_id)]
                    # ~ else:
                        # ~ return map(str, variant.attribute_value_ids.mapped('id'))
                # ~ elif len(variant) > 1:
                    # ~ for att_value_id in attribute_value_list:
                        # ~ if att_value_id not in variant.attribute_value_ids.mapped('id'):
                            # ~ attribute_value_list.remove(att_id)
                    # ~ return map(str, attribute_value_list)
                # ~ else:
                    # ~ return []
        # ~ return []
