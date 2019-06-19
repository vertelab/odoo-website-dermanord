# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2004-2018 Vertel AB (<http://vertel.se>).
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

from openerp import models, fields, api
from datetime import datetime, date, timedelta
from openerp.addons.website_memcached import memcached
import base64
import werkzeug
from openerp.addons.website.models.website import slug 

from openerp import http
from openerp.http import request

from timeit import default_timer as timer
import sys, traceback
import json

import logging
_logger = logging.getLogger(__name__)

from openerp.tools.translate import GettextAlias
from openerp import SUPERUSER_ID
import inspect
import openerp

class GettextAlias(GettextAlias):
    def __init__(self, name=None):
        self.name = '/'.join(name.split('.')[1:]) + '.py'

    def __call__(self, source):
        res = source
        cr = None
        is_new_cr = False
        try:
            frame = inspect.currentframe()
            if frame is None:
                return source
            frame = frame.f_back
            if not frame:
                return source
            lang = self._get_lang(frame)
            if lang:
                cr, is_new_cr = self._get_cr(frame)
                if cr:
                    # Try to use ir.translation to benefit from global cache if possible
                    registry = openerp.registry(cr.dbname)
                    res = registry['ir.translation']._get_source(cr, SUPERUSER_ID, self.name, ('code','sql_constraint'), lang, source)
                else:
                    _logger.debug('no context cursor detected, skipping translation for "%r"', source)
            else:
                _logger.debug('no translation language detected, skipping translation for "%r" ', source)
        except Exception:
            _logger.debug('translation went wrong for "%r", skipped', source)
                # if so, double-check the root/base translations filenames
        finally:
            if cr and is_new_cr:
                cr.close()
        return res

_ = GettextAlias(__name__)

#
#  tumnagel template + default variant, tumnagel variant, rad variant
#
#        page_dict = memcached.mc_load(key)
#        if page_dict:
#            return page_dict.get('page').decode('base64')
#        return request.registry['ir.http']._handle_exception(None, 404)
#





THUMBNAIL = u"""
<div class="dn_oe_product col-md-4 col-sm-6 col-xs-12">
            <form action="/shop/cart/update" method="post">
                <div class="dn_product_div {product_ribbon}">
                    <!-- Ribbons -->
                    <div class="ribbon-wrapper">
                        {product_ribbon_promo}
                        {product_ribbon_limited}
                    </div>
                    <div class="offer-wrapper">
                        {product_ribbon_offer}
                    </div>
                    <!-- Image -->
                    <div class="dn_product_image">
                        <div class="dn_product_image_div">
                            <a itemprop="url" href="/dn_shop/{view_type}/{product_id}">
                                <img class="img img-responsive" src="{product_image}" alt="{product_name}">
                                <div class="dn_product_image_hover_btn text-center hidden-xs">
                                    <p class="dn_btn dn_primary">{details}</p>
                                </div>
                            </a>
                        </div>
                    </div>
                    <!-- Product info (name and price) -->
                    <div class="dn_product_info text-center">
                        <!-- Product name -->
                        <h4 class="p_name">
                            <strong>
                                <a itemprop="name" href="/dn_shop/{view_type}/{product_id}">{product_name}</a>
                            </strong>
                        </h4>
                        <div class="product_price">
                            <b class="text-muted">
                            <h5>{price_from}</h5>
                                <h4 style="font-size: 0.9em;">
                                    {product_price}
                                </h4>
                            </b>
                        </div>
                    </div>
                    <!-- Product info end -->
                    <!-- key {key} key_raw {key_raw} render_time {render_time} -->
                    <!-- http:/mcpage/{key} http:/mcpage/{key}/delete  http:/mcmeta/{key} -->
                </div>
            </form>
</div>
"""



class product_template(models.Model):
    _inherit = 'product.template'

    # ~ @api.one
    # ~ @api.depends('product_variant_ids.active')
    # ~ def _compute_product_variant_count(self):
        # ~ self.product_variant_count = len(self.product_variant_ids.filtered('active'))
    # ~ product_variant_count = fields.Integer(string='# of Product Variants', compute='_compute_product_variant_count', store=True)

    @api.multi
    def dn_clear_cache(self):
        
        
        db_name = self.env.cr.dbname
        website = self.env.ref('website.default_website')
        
        for key in memcached.get_keys(path=[('%s,%s' % (p._model, p.id)) for p in self], db=db_name):
            memcached.mc_delete(key)
        for p in self:
            for lang in website.language_ids:
                for key in memcached.get_keys(path=['/dn_shop/product/%s' % slug(p.with_context(lang=lang.code))], db=db_name):
                    memcached.mc_delete(key)
            
        for p in self:
            for key in memcached.get_keys(path=[('%s,%s' % (v._model, v.id)) for v in p.product_variant_ids], db=db_name):
                memcached.mc_delete(key)
            for v in p.product_variant_ids:
                for lang in website.language_ids:
                    for key in memcached.get_keys(path=['/dn_shop/variant/%s' % slug(v.with_context(lang=lang.code))], db=db_name):
                        memcached.mc_delete(key)
        
        for key in memcached.get_keys(flush_type='webshop', db=db_name):
            memcached.mc_delete(key)

    @api.multi
    @api.depends('name', 'list_price', 'taxes_id', 'default_code', 'description_sale', 'image', 'image_attachment_ids', 'image_attachment_ids.datas', 'image_attachment_ids.sequence', 'product_variant_ids.image_attachment_ids', 'product_variant_ids.image_attachment_ids.datas', 'product_variant_ids.image_medium', 'product_variant_ids.image_attachment_ids.sequence', 'website_style_ids', 'attribute_line_ids.value_ids', 'sale_ok', 'product_variant_ids.sale_ok')
    def _get_all_variant_data(self):
        placeholder = '/web/static/src/img/placeholder.png'

        for p in self:
            if not p.product_variant_ids:
                continue
            try:
                variant = p.get_default_variant().read(['name', 'fullname', 'default_code', 'description_sale', 'image_main_id', 'website_style_ids_variant', 'sale_ok'])[0]
                if p.sale_ok and not variant['sale_ok']:
                    raise Warning(_('Default variant on %s can not be sold' % p.name))
                website_style_ids_variant = ' '.join([s['html_class'] for s in self.env['product.style'].browse(variant['website_style_ids_variant']).read(['html_class'])])
                p.dv_id = variant['id']
                p.dv_default_code = variant['default_code'] or ''
                p.dv_description_sale = variant['description_sale'] or ''
                p.dv_name = p.name if p.use_tmpl_name else variant['fullname']
                p.dv_image_src = self.env['website'].imagefield_hash('ir.attachment', 'datas', variant['image_main_id'][0], 'snippet_dermanord.img_product') if variant['image_main_id'] else placeholder
                p.dv_ribbon = website_style_ids_variant if website_style_ids_variant else ' '.join([c for c in p.website_style_ids.mapped('html_class') if c])
            except:
                e = sys.exc_info()
                msg = u'%s' % e[1]
                # Find latest error message to compare with
                msg_old = self.env['mail.message'].search([
                    ('subject', '=like', 'Default variant recompute failed on %'),
                    ('model', '=', 'product.template'),
                    ('res_id', '=', p.id)], order='date desc', limit=1)
                if msg_old:
                    msg_old = msg_old.body.replace('<p>', '').replace('</p>', '').split('<br>')
                    if len(msg_old) > 1:
                        msg_old = msg_old[-2].split(': ', 1)
                        if len(msg_old) == 2:
                            msg_old = msg_old[1]
                        else:
                            msg_old = ''
                    else:
                        msg_old = ''
                else:
                    msg_old = ''
                send = True
                if msg.startswith(u'Default variant on ') and msg.endswith(u' can not be sold'):
                    if msg_old.startswith(u'Default variant on ') and msg_old.endswith(u' can not be sold'):
                        send = False
                elif msg == msg_old:
                    send = False
                tb = ''.join(traceback.format_exception(e[0], e[1], e[2]))
                _logger.error(tb)
                if send:
                    self.env['mail.message'].create({
                        'body': tb.replace('\n', '<br/>'),
                        'subject': 'Default variant recompute failed on %s' % p.name,
                        'author_id': self.env.ref('base.partner_root').id,
                        'res_id': p.id,
                        'model': p._name,
                        'type': 'notification',
                        'partner_ids': [(4, pid) for pid in p.message_follower_ids.mapped('id')],
                    })
                p.dv_default_code = 'error'
                p.dv_description_sale = msg
                p.dv_name = 'Error'
                p.dv_image_src = placeholder
                p.dv_ribbon = ''

    dv_id = fields.Integer(compute='_get_all_variant_data', store=True)
    dv_default_code = fields.Char(compute='_get_all_variant_data', store=True)
    dv_description_sale = fields.Text(compute='_get_all_variant_data', store=True)
    dv_image_src = fields.Char(compute='_get_all_variant_data', store=True)
    dv_name = fields.Char(compute='_get_all_variant_data', store=True)
    dv_ribbon = fields.Char(compute='_get_all_variant_data', store=True)


    @api.one
    @api.depends('campaign_changed', 'product_variant_ids.campaign_changed')
    def _is_offer_product(self):
        self.is_offer_product_reseller = self in self.get_campaign_tmpl(for_reseller=True)
        if not self.is_offer_product_reseller:
            self.is_offer_product_reseller = bool(self.product_variant_ids & self.get_campaign_variants(for_reseller=True))
        self.is_offer_product_consumer = self in self.get_campaign_tmpl(for_reseller=False)
        if not self.is_offer_product_consumer:
            self.is_offer_product_consumer = bool(self.product_variant_ids & self.get_campaign_variants(for_reseller=False))
    is_offer_product_consumer = fields.Boolean(compute='_is_offer_product', store=True)
    is_offer_product_reseller = fields.Boolean(compute='_is_offer_product', store=True)



    @api.model
    def get_thumbnail_default_variant(self,domain,pricelist,limit=21,order='',offset=0):
        if isinstance(pricelist,int):
            pricelist = self.env['product.pricelist'].browse(pricelist)
        # ~ _logger.warn('get_thumbnail_default_variant --------> %s' % ('Start'))
        # ~ _logger.warn('get_thumbnail_default_variant --------> %s' % self.env['product.template'].search_read(domain, fields=['id','name', 'dv_ribbon' ,'is_offer_product_reseller', 'is_offer_product_consumer','dv_image_src',], limit=limit, order=order,offset=offset))
        thumbnail = []
        flush_type = 'thumbnail_product'
        ribbon_promo = None
        ribbon_limited = None

        # ~ domain += [('website_published','=',True),('event_ok','=',False),('sale_ok','=',True),('access_group_ids','in',[286])]
        # ~ d2 = []
        # ~ for d in domain:
            # ~ if not d[0] == 'product_variant_ids':
                # ~ d2.append(d)
        # ~ domain = d2
        user = self.env.ref('base.public_user')

        # ~ domain += [('website_published','=',True),('event_ok','=',False),('sale_ok','=',True),('access_group_ids','in',[286])]

        # ~ for product in self.env['product.template'].sudo().search_read([('website_published','=',True),('event_ok','=',False),('sale_ok','=',True),('access_group_ids','in',[286])],['name']):
            # ~ _logger.warn('get_thumbnail_default_variant product --------> %s' % (product))
            # ~ p = self.env['product.template'].browse(product['id'])

        # ~ for p in self.env['product.template'].search(domain,limit=limit, order=order,offset=offset):
            # ~ _logger.warn('get_thumbnail_default_variant product --------> %s' % (p))
            # ~ product = self.env['product.template'].read(p.id,['name', 'dv_ribbon','is_offer_product_reseller', 'is_offer_product_consumer','dv_image_src',])

        for product in self.env['product.template'].search_read(domain, fields=['name', 'dv_ribbon','is_offer_product_reseller', 'is_offer_product_consumer','dv_image_src',], limit=limit, order=order,offset=offset):
            # ~ _logger.warn('get_thumbnail_default_variant --------> %s' % (product))
            key_raw = 'thumbnail_default_variant %s %s %s %s %s %s %s %s' % (
                self.env.cr.dbname, flush_type, product['id'], pricelist.id,
                self.env.lang, request.session.get('device_type','md'),
                self.env.user in self.sudo().env.ref('base.group_website_publisher').users,
                ','.join([str(id) for id in sorted(self.env.user.commercial_partner_id.access_group_ids._ids)]))  # db flush_type produkt prislista språk webeditor kundgrupper,
            key,page_dict = self.env['website'].get_page_dict(key_raw)
            # ~ _logger.warn('get_thumbnail_default_variant --------> %s %s' % (key,page_dict))
            if not page_dict:
                render_start = timer()
                if not ribbon_limited:
                    ribbon_limited = request.env.ref('webshop_dermanord.image_limited')
                    ribbon_promo   = request.env.ref('website_sale.image_promo')

                #
                # TODO: get_html_price_long(pricelist) and variant.image_main_id[0].id  dv_ribbon
                #

                # ~ product = self.env['product.template'].browse(pid['id'])
                # ~ if not product.product_variant_ids:
                    # ~ continue
                # ~ variant = product.product_variant_ids[0]
                # ~ variant = product.get_default_variant()
                # ~ if not variant:
                    # ~ continue

                page = THUMBNAIL.format(
                    details=_('DETAILS'),
                    product_id=product['id'],
                    # ~ product_image=self.env['website'].imagefield_hash('ir.attachment', 'datas', variant.image_main_id[0].id, 'snippet_dermanord.img_product') if variant.image_main_id else '',
                    product_image=product['dv_image_src'],
                    product_name=product['name'],
                    product_price = self.env['product.template'].browse(product['id']).get_pricelist_chart_line(pricelist).get_html_price_long(),
                    product_ribbon=product['dv_ribbon'],
                    # ~ product_ribbon=' '.join([c for c in self.env['product.style'].browse(ribbon_ids).mapped('html_class') if c]),
                    product_ribbon_offer  = '<div class="ribbon ribbon_offer   btn btn-primary">%s</div>' % _('Offer') if (product['is_offer_product_reseller'] and pricelist.for_reseller == True) or (product['is_offer_product_consumer'] and  pricelist.for_reseller == False) else '',
                    product_ribbon_promo  = '<div class="ribbon ribbon_news    btn btn-primary">' + _('New') + '</div>' if (product['dv_ribbon'] and (ribbon_promo.html_class in product['dv_ribbon'])) else '',
                    product_ribbon_limited= '<div class="ribbon ribbon_limited btn btn-primary">' + _('Limited<br/>Edition') + '</div>' if (product['dv_ribbon'] and (ribbon_limited.html_class in product['dv_ribbon'])) else '',
                    key_raw=key_raw,
                    key=key,
                    view_type='product',
                    render_time='%s' % (timer() - render_start),
                    price_from=_('Price From'),
                ).encode('utf-8')
                # ~ _logger.warn('get_thumbnail_default_variant --------> %s' % (page))
                self.env['website'].put_page_dict(key_raw, flush_type, page, 'product.template,%s' % product['id'])
                page_dict['page'] = base64.b64encode(page)
            thumbnail.append(page_dict.get('page', '').decode('base64'))
        return thumbnail

    @api.model
    def get_thumbnail_default_variant2(self,pricelist,product_ids):
        if isinstance(pricelist,int):
            pricelist = self.env['product.pricelist'].sudo().browse(pricelist)
        # ~ _logger.warn('get_thumbnail_default_variant --------> %s' % ('Start'))
        # ~ _logger.warn('get_thumbnail_default_variant --------> %s' % self.env['product.template'].search_read(domain, fields=['id','name', 'dv_ribbon' ,'is_offer_product_reseller', 'is_offer_product_consumer','dv_image_src',], limit=limit, order=order,offset=offset))
        thumbnail = []
        flush_type = 'thumbnail_product'
        ribbon_promo = None
        ribbon_limited = None

        user = self.env.ref('base.public_user')

        _logger.warn('Notice get_thunmb2 --------> %s user %s %s %s ' % (self.env.ref('base.public_user'),self.env.user,self._uid,user))

        for product in product_ids:
            # ~ _logger.warn('get_thumbnail_default_variant --------> %s' % (product))
            key_raw = 'thumbnail_default_variant %s %s %s %s %s %s %s %s' % (
                self.env.cr.dbname, flush_type, product['id'], pricelist.id,
                self.env.lang, request.session.get('device_type','md'),
                self.env.user in self.sudo().env.ref('base.group_website_publisher').users,
                ','.join([str(id) for id in sorted(self.env.user.commercial_partner_id.access_group_ids._ids)]))  # db flush_type produkt prislista språk webeditor kundgrupper,
            key, page_dict = self.env['website'].get_page_dict(key_raw)
            # ~ _logger.warn('get_thumbnail_default_variant --------> %s %s' % (key,page_dict))
            if not page_dict:
                render_start = timer()
                if not ribbon_limited:
                    ribbon_limited = request.env.ref('webshop_dermanord.image_limited')
                    ribbon_promo   = request.env.ref('website_sale.image_promo')

                #
                # TODO: get_html_price_long(pricelist) and variant.image_main_id[0].id  dv_ribbon
                #

                # ~ product = self.env['product.template'].browse(pid['id'])
                # ~ if not product.product_variant_ids:
                    # ~ continue
                # ~ variant = product.product_variant_ids[0]
                # ~ variant = product.get_default_variant()
                # ~ if not variant:
                    # ~ continue

                page = THUMBNAIL.format(
                    details=_('DETAILS'),
                    product_id=product['id'],
                    # ~ product_image=self.env['website'].imagefield_hash('ir.attachment', 'datas', variant.image_main_id[0].id, 'snippet_dermanord.img_product') if variant.image_main_id else '',
                    product_image=product['dv_image_src'],
                    product_name=product['name'],
                    product_price = self.env['product.template'].sudo().browse(product['id']).get_pricelist_chart_line(pricelist).get_html_price_long(),
                    product_ribbon=product['dv_ribbon'],
                    # ~ product_ribbon=' '.join([c for c in self.env['product.style'].browse(ribbon_ids).mapped('html_class') if c]),
                    product_ribbon_offer  = '<div class="ribbon ribbon_offer   btn btn-primary">%s</div>' % _('Offer') if (product['is_offer_product_reseller'] and pricelist.for_reseller == True) or (product['is_offer_product_consumer'] and  pricelist.for_reseller == False) else '',
                    product_ribbon_promo  = '<div class="ribbon ribbon_news    btn btn-primary">' + _('New') + '</div>' if (product['dv_ribbon'] and (ribbon_promo.html_class in product['dv_ribbon'])) else '',
                    product_ribbon_limited= '<div class="ribbon ribbon_limited btn btn-primary">' + _('Limited<br/>Edition') + '</div>' if (product['dv_ribbon'] and (ribbon_limited.html_class in product['dv_ribbon'])) else '',
                    key_raw=key_raw,
                    key=key,
                    view_type='product',
                    render_time='%s' % (timer() - render_start),
                    price_from=_('Price From'),
                ).encode('utf-8')
                # ~ _logger.warn('get_thumbnail_default_variant --------> %s' % (page))
                self.env['website'].put_page_dict(key_raw, flush_type, page, 'product.template,%s' % product['id'])
                page_dict['page'] = base64.b64encode(page)
            thumbnail.append(page_dict.get('page', '').decode('base64'))
        return thumbnail
        
    @api.model
    def get_thumbnail_variant(self,pricelist,variant_ids):
        if isinstance(pricelist,int):
            pricelist = self.env['product.pricelist'].sudo().browse(pricelist)
        # ~ _logger.warn('get_thumbnail_default_variant --------> %s' % ('Start'))
        # ~ _logger.warn('get_thumbnail_default_variant --------> %s' % self.env['product.template'].search_read(domain, fields=['id','name', 'dv_ribbon' ,'is_offer_product_reseller', 'is_offer_product_consumer','dv_image_src',], limit=limit, order=order,offset=offset))
        thumbnail = []
        flush_type = 'thumbnail_variant'
        ribbon_promo = None
        ribbon_limited = None

        user = self.env.ref('base.public_user')

        _logger.warn('Notice get_thunmb2 --------> %s user %s %s %s ' % (self.env.ref('base.public_user'),self.env.user,self._uid,user))

        for variant in variant_ids:
            # ~ _logger.warn('get_thumbnail_default_variant --------> %s' % (product))
            key_raw = 'thumbnail_variant %s %s %s %s %s %s %s %s' % (
                self.env.cr.dbname, flush_type, variant['id'], pricelist.id,
                self.env.lang, request.session.get('device_type','md'),
                self.env.user in self.sudo().env.ref('base.group_website_publisher').users,
                ','.join([str(id) for id in sorted(self.env.user.commercial_partner_id.access_group_ids._ids)]))  # db flush_type produkt prislista språk webeditor kundgrupper,
            key, page_dict = self.env['website'].get_page_dict(key_raw)
            # ~ _logger.warn('get_thumbnail_default_variant --------> %s %s' % (key,page_dict))
            if not page_dict:
                render_start = timer()
                if not ribbon_limited:
                    ribbon_limited = request.env.ref('webshop_dermanord.image_limited')
                    ribbon_promo   = request.env.ref('website_sale.image_promo')

                #
                # TODO: get_html_price_long(pricelist) and variant.image_main_id[0].id  dv_ribbon
                #

                # ~ product = self.env['product.template'].browse(pid['id'])
                # ~ if not product.product_variant_ids:
                    # ~ continue
                # ~ variant = product.product_variant_ids[0]
                # ~ variant = product.get_default_variant()
                # ~ if not variant:
                    # ~ continue

                page = THUMBNAIL.format(
                    details=_('DETAILS'),
                    product_id=variant['id'],
                    # ~ product_image=self.env['website'].imagefield_hash('ir.attachment', 'datas', variant.image_main_id[0].id, 'snippet_dermanord.img_product') if variant.image_main_id else '',
                    product_image=variant['dv_image_src'],
                    product_name=variant['name'],
                    product_price = self.env['product.product'].sudo().browse(variant['id']).get_pricelist_chart_line(pricelist).get_html_price_long(),
                    product_ribbon=variant['dv_ribbon'],
                    # ~ product_ribbon=' '.join([c for c in self.env['product.style'].browse(ribbon_ids).mapped('html_class') if c]),
                    product_ribbon_offer  = '<div class="ribbon ribbon_offer   btn btn-primary">%s</div>' % _('Offer') if (variant['is_offer_product_reseller'] and pricelist.for_reseller == True) or (variant['is_offer_product_consumer'] and  pricelist.for_reseller == False) else '',
                    product_ribbon_promo  = '<div class="ribbon ribbon_news    btn btn-primary">' + _('New') + '</div>' if (variant['dv_ribbon'] and (ribbon_promo.html_class in variant['dv_ribbon'])) else '',
                    product_ribbon_limited= '<div class="ribbon ribbon_limited btn btn-primary">' + _('Limited<br/>Edition') + '</div>' if (variant['dv_ribbon'] and (ribbon_limited.html_class in variant['dv_ribbon'])) else '',
                    key_raw=key_raw,
                    key=key,
                    view_type='product',
                    render_time='%s' % (timer() - render_start),
                    price_from=_('Price From'),
                ).encode('utf-8')
                # ~ _logger.warn('get_thumbnail_default_variant --------> %s' % (page))
                self.env['website'].put_page_dict(key_raw, flush_type, page, 'product.variant,%s' % variant['id'])
                page_dict['page'] = base64.b64encode(page)
            thumbnail.append(page_dict.get('page', '').decode('base64'))
        return thumbnail

class product_product(models.Model):
    _inherit = 'product.product'
    
    purchase_type = fields.Selection(selection=[('none', 'None'), ('consumer', 'Consumer Purchase'), ('buy', 'Purchase'), ('edu', 'Educational Purchase')], string='Purchase Type', compute='_compute_purchase_type', help="Purchase type for active user.")
    
    @api.one
    def _compute_purchase_type(self):
        """ Checks what kind of purchase the given product should have for the active user."""
        partner = request.env.user.partner_id.commercial_partner_id
        def check_groups(*groups):
            for group in groups:
                if group in self.access_group_ids:
                    return True
            return False
        
        sk  = self.env.ref('webshop_dermanord.group_dn_sk')     # id: 286
        af  = self.env.ref('webshop_dermanord.group_dn_af')     # id: 283
        spa = self.env.ref('webshop_dermanord.group_dn_spa')    # id: 285
        ht  = self.env.ref('webshop_dermanord.group_dn_ht')     # id: 284
        
        #                       1   2   3       4   5   6       7   8   9       10  11  12
        #    Kundtyp            Slutkonsument   Återförsäljare  Spa-terapeut    Hud-terapeut
        #    -------------------------------------------------------------------------------
        #    Produktgrupper  |  Se  Utb Köp     Se  Utb Köp     Se  Utb Köp     Se  Utb Köp
        # A  SK              |  x       x                                              
        # B  SK, ÅF          |  x       x       x       x       x       x       x       x
        # C  SK, SPA, HT     |  x       x       x   x           x       x       x       x
        # D  SK, HT          |  x       x       x   x           x   x           x       x
        # E  SPA, HT         |                  x               x       x       x       x
        # F  ÅF              |                  x       x       x       x       x       x
        # G  SPA             |                  x               x       x       x       x
        # H  HT              |                  x               x               x       x
        
        def get_purchase_type():
            if sk in partner.access_group_ids:
                # Slutkonsument
                return 'consumer'
            elif ht in partner.access_group_ids:
                # Hudterapeut
                #   Köp:    HT or SPA or ÅF
                #   Utb:
                if check_groups(ht, spa, af):
                    # Köp
                    return 'buy'
            elif spa in partner.access_group_ids:
                # SPA-terapeut
                #   Köp:    SPA or ÅF
                #   Utb:    SK and not SPA
                if check_groups(spa, af):
                    # Köp
                    return 'buy'
                elif check_groups(sk):
                    # Utb
                    return 'edu'
            elif af in partner.access_group_ids:
                # Återförsäljare
                #   Köp:    ÅF
                #   Utb:    SK and not ÅF
                if check_groups(af):
                    # Köp
                    return 'buy'
                elif check_groups(sk):
                    # Utb
                    return 'edu'
            return 'none'
            
        self.purchase_type = get_purchase_type()
    
    @api.multi
    def get_add_to_cart_buttons(self):
        """ Returns a dict with the relevant kinds of 'add to cart' buttons """
        res = {}
        
        if self.purchase_type == 'none':
            res['list_view'] = u"""""" # There is never a reseller button on the list view. 
            res['product_view'] = u""""""
        elif self.purchase_type == 'consumer':
            res['list_view'] = u"""""" # There is never a reseller button on the list view. 
            res['product_view'] = u"""<button type="button" class="add_to_cart_consumer dn_btn dn_primary mt8 text-center {buy_button_hidden}" data-toggle="modal" data-target="#reseller_search">{text}</button>""".format(
                buy_button_hidden = '',
                text = _('Find Reseller')
            )
        elif self.purchase_type == 'edu':
            res['list_view'] = u"""<a class="btn btn-default dn_list_add_to_cart_edu" href="javascript:void(0);"><i class="fa fa-shopping-cart" style="color: #839794;"></i></a>""".format(
                text = _('Add to cart')
            )
            res['product_view'] = u"""<a id="add_to_cart_edu" href="#" class="dn_btn dn_primary mt8 js_check_product a-submit text-center {buy_button_hidden}" groups="base.group_user,base.group_portal" disable="1">{text}</a>""".format(
                buy_button_hidden = '{%s_buy_button_hidden}' % self.id,
                text = _('Add to cart')
            )
        elif self.purchase_type == 'buy':
            res['list_view'] = u"""<a class="btn btn-default dn_list_add_to_cart" href="javascript:void(0);"><i class="fa fa-shopping-cart" style="color: #839794;"></i></a>""".format(
                text = _('Add to cart')
            )
            res['product_view'] = u"""<a id="add_to_cart" href="#" class="dn_btn dn_primary mt8 js_check_product a-submit text-center {buy_button_hidden}" groups="base.group_user,base.group_portal" disable="1">{text}</a>""".format(
                buy_button_hidden = '{%s_buy_button_hidden}' % self.id,
                text = _('Add to cart')
            )
        return res
    
    @api.multi
    def dn_clear_cache(self):
        for key in memcached.get_keys(path=[('%s,%s' % (p._model, p.id)) for p in self]):
            memcached.mc_delete(key)
            

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
    # ~ force_out_of_stock = fields.Boolean(string='Out of Stock', help="Forces this product to display as out of stock in the webshop.")
    inventory_availability = fields.Selection([
        ('never', 'Never sell'),
        ('always', 'Sell regardless of inventory'),
        ('threshold', 'Only prevent sales if not enough stock'),
    ], string='Inventory Availability', help='Adds an inventory availability status on the web product page.', default='threshold')
    
    
    @api.model
    def get_thumbnail_variant(self,domain,pricelist,limit=21,offset=0,order=''):
        thumbnail = []
        flush_type = 'thumbnail_variant'
        for product in self.env['product.template'].search_read(domain, fields=['id','name', 'dv_ribbon','is_offer_product_reseller', 'is_offer_product_consumer','dv_image_src'],limit=limit, order=order):
            key_raw = 'dn_shop %s %s %s %s %s %s' % (self.env.cr.dbname,flush_type,product['id'],pricelist.id,self.env.lang,request.session.get('device_type','md'))  # db flush_type produkt prislista språk
            key,page_dict = self.env['website'].get_page_dict(key_raw)
            # ~ _logger.warn('get_thumbnail_default_variant --------> %s %s' % (key,page_dict))
            ribbon_promo = None
            ribbon_limited = None
            if not page_dict:
                render_start = timer()
                if not ribbon_limited:
                    ribbon_limited = request.env.ref('webshop_dermanord.image_limited')
                    ribbon_promo   = request.env.ref('website_sale.image_promo')

                #
                # TODO: get_html_price_long(pricelist) and variant.image_main_id[0].id  dv_ribbon
                #

                # ~ product = self.env['product.template'].browse(pid['id'])
                # ~ if not product.product_variant_ids:
                    # ~ continue
                # ~ variant = product.product_variant_ids[0]
                # ~ variant = product.get_default_variant()
                # ~ if not variant:
                    # ~ continue

                page = THUMBNAIL.format(
                    details=_('DETAILS'),
                    product_id=product['id'],
                    # ~ product_image=self.env['website'].imagefield_hash('ir.attachment', 'datas', variant.image_main_id[0].id, 'snippet_dermanord.img_product') if variant.image_main_id else '',
                    product_image=product['dv_image_src'],
                    product_name=product['name'],
                    product_price = self.env['product.template'].browse(product['id']).get_pricelist_chart_line(pricelist).get_html_price_long(),
                    product_ribbon=product['dv_ribbon'],
                    # ~ product_ribbon=' '.join([c for c in self.env['product.style'].browse(ribbon_ids).mapped('html_class') if c]),
                    product_ribbon_offer  = '<div class="ribbon ribbon_offer   btn btn-primary">%s</div>' % _('Offer') if (product['is_offer_product_reseller'] and pricelist.for_reseller == True) or (product['is_offer_product_consumer'] and  pricelist.for_reseller == False) else '',
                    product_ribbon_promo  = '<div class="ribbon ribbon_news    btn btn-primary">' + _('New') + '</div>' if ribbon_promo.html_class in product['dv_ribbon'] else '',
                    product_ribbon_limited= '<div class="ribbon ribbon_limited btn btn-primary">' + _('Limited<br/>Edition') + '</div>' if ribbon_limited.html_class in product['dv_ribbon'] else '',
                    key_raw=key_raw,
                    key=key,
                    view_type='variant',
                    render_time='%s' % (timer() - render_start),
                    price_from=_('Price From'),
                ).encode('utf-8')
                _logger.warn('get_thumbnail_default_variant --------> %s' % (page))
                self.env['website'].put_page_dict(key_raw, flush_type, page, 'product.template,%s' % product['id'])
                page_dict['page'] = base64.b64encode(page)
            thumbnail.append(page_dict.get('page', '').decode('base64'))
            _logger.warn('get_thumbnail_default_variant (thiumnails)--------> %s' % (thumbnail))
        return thumbnail

    @api.model
    def get_packaging_info(self, product_id):
        packaging_ids = self.env['product.product'].sudo().search_read([('id','=',product_id)],['packaging_ids'])
        product = packaging_ids[0] if len(packaging_ids) > 0 else None
        if not product:
            return ''
        packagings = self.env['product.packaging'].sudo().browse(product['packaging_ids'])
        html = ''
        for packaging in packagings:
            html += u"""<div class="dn-tooltip text-centered"><i class="fa fa-cube"></i>
                        <div class="dn-tooltiptext">
                            <b>{ul_name}</b><br>
                            {qty}
                            {ean}
                            {width}
                            {length}
                            {height}
                            {ul_container_name}
                            {ul_qty}
                            {kfp}
                        </div>
                    </div>""".format(
                                ul_name=packaging.ul.name,
                                qty="""<b>%s</b> %s %s<br/>""" % (_('Quantity:') ,packaging.qty,_('pcs / box')) if packaging.qty else '',
                                ean="""<b>%s</b> %s %s<br/>""" % (_('EAN:') ,packaging.ean,_('pcs / box')) if packaging.ean else '',
                                width="""<b>%s</b> %s mm<br/>""" % (_('Width:') ,packaging.ul.width) if packaging.ul.width else '',
                                length="""<b>%s</b> %s mm<br/>""" % (_('Length:') ,packaging.ul.length) if packaging.ul.length else '',
                                height="""<b>%s</b> %s mm<br/>""" % (_('Height:') ,packaging.ul.height) if packaging.ul.height else '',
                                ul_container_name="""<b>%s</b><br/>""" % packaging.ul_container.name if packaging.ul_container else '',
                                ul_qty="""<b>%s</b> %s %s<br/>""" % (_('Quantity (DFP):') ,packaging.ul_qty * packaging.rows,_('boxes / pallet')) if packaging.ul_container else '',
                                kfp="""<b>%s</b> %s %s<br/>""" % (_('Quantity (KFP):') ,packaging.qty * packaging.ul_qty * packaging.rows,_('pcs / pallet')) if packaging.ul_container else '',
                            )
        return html

    @api.model
    def get_stock_info(self, product_id):
        # ~ product = self.env['product.product'].sudo().search_read([('id', '=', product_id)], ['virtual_available_days', 'type', 'force_out_of_stock', 'is_offer'])
        product = self.env['product.product'].sudo().search_read([('id', '=', product_id)], ['virtual_available_days', 'type', 'inventory_availability', 'is_offer'])
        if len(product) > 0:
            product = product[0]
        else:
            product = {}
        state = None
        # ~ if product.get('force_out_of_stock', False):
        if product['inventory_availability'] == 'never':
            state = 'short'
        # ~ elif product.get('type', False) != 'product':
        elif product.get('type', False) != 'product' or product['inventory_availability'] == 'always':
            state = 'in'
        elif product.get('is_offer', False):
            # Can produce strange results if there's more than one active BoM. Probably not an issue.
            states = ['short', 'few', 'in']
            state = None
            for id in [p['product_id'][0] for p in self.env['mrp.bom.line'].sudo().search_read([('bom_id.product_id', '=', product_id), ('bom_id.active', '=', True)], ['product_id'])]:
                child_state = self.get_stock_info(id)[1]
                if not state:
                    state = child_state
                elif states.index(child_state) < states.index(state):
                    state = child_state
                # Default if there is no BoM
                state = state or 'short'
        elif product.get('virtual_available_days', 0) > 5:
            state = 'in'
        elif product.get('virtual_available_days', 0.0) >= 1.0:
            state = 'few'
        state = state or 'short'
        return (state in ['in', 'few'], state, '' if  product.get('type') == 'consu' else {'in': _('In stock'), 'few': _('Few in stock'), 'short': _('Shortage')}[state].encode('utf-8'))  # in_stock,state,info
    
    @api.model
    def get_list_row(self,domain,pricelist,limit=21,order='',offset=0):
        if isinstance(pricelist,int):
            pricelist = self.env['product.pricelist'].browse(pricelist)
        rows = []
        flush_type = 'product_list_row'
        ribbon_limited = request.env.ref('webshop_dermanord.image_limited')
        ribbon_promo   = request.env.ref('website_sale.image_promo')
        for product in self.env['product.product'].search_read(domain, fields=['id','fullname', 'default_code','type', 'is_offer_product_reseller', 'is_offer_product_consumer', 'product_tmpl_id', 'sale_ok','campaign_ids', 'website_style_ids', 'website_style_ids_variant'], limit=limit, order=order,offset=offset):
            key_raw = 'list_row %s %s %s %s %s %s Groups: %s' % (self.env.cr.dbname,flush_type,product['id'],pricelist.id,self.env.lang,request.session.get('device_type','md'), request.website.get_dn_groups())  # db flush_type produkt prislista språk användargrupp
            key,page_dict = self.env['website'].get_page_dict(key_raw)
            if not page_dict:
                render_start = timer()
                campaign = self.env['crm.tracking.campaign'].browse(product['campaign_ids'][0] if product['campaign_ids'] else 0)
                template = self.env['product.template'].search_read([('id', '=', product['product_tmpl_id'][0])], fields=['is_offer_product_reseller', 'is_offer_product_consumer'])[0]
                product_ribbon_offer  = False
                if pricelist.for_reseller:
                    if product['is_offer_product_reseller'] or template['is_offer_product_reseller']:
                        product_ribbon_offer  = True
                else:
                    if product['is_offer_product_consumer'] or template['is_offer_product_consumer']:
                        product_ribbon_offer  = True
                product_obj = self.env['product.product'].browse(product['id'])
                is_edu_purchase = product_obj.purchase_type == 'edu'
                buttons = product_obj.get_add_to_cart_buttons()
                page = u"""<tr class="tr_lst ">
                                <td class="td_lst">
                                    <div class="lst-ribbon-wrapper">{product_ribbon_offer}{product_ribbon_promo}{product_ribbon_limited}</div>
                                </td>
                                <td>
                                    <h5 class="list_product_name">
                                        <span>{product_default_code}</span>
                                    </h5>
                                </td>
                                <td style="max-width: 250px;">
                                    <h5 class="list_product_name">
                                        <div itemprop="offers" itemscope="itemscope" itemtype="http://schema.org/Offer" class="product_name">
                                            <strong>
                                                <a href="/dn_shop/variant/{product_id}" title="{product_name}">
                                                    <span itemprop="name">{product_name}</span>
                                                </a>
                                            </strong>
                                        </div>
                                    </h5>
                                </td>
                                <td>
                                    <h5>
                                        <div class="text-center">
                                            <span>{product_startdate}</span>
                                            <br>
                                            <span>{product_stopdate}</span>
                                        </div>
                                    </h5>
                                </td>
                                <td>
                                    {product_price}
                                </td>
                                <td>
                                    <div class="dn-tooltip text-centered">
                                    {product_dfp}
                                    </div>
                                </td>
                                <td>
                                    <div class="{shop_widget}">
                                        <form action="/shop/cart/update" class="oe_dn_list {hide_spinner}" data-attribute_value_ids="{product_id}" method="POST">
                                            <div class="product_shop" style="margin: 0px;">
                                                <input class="product_id" name="product_id" value="{product_id}" type="hidden">
                                                <input name="return_url" value="{return_url}" type="hidden">
                                                <div class="css_quantity input-group oe_website_spinner">
                                                    <span class="input-group-addon">
                                                        <a href="#" class="mb8 js_add_cart_json">
                                                            <i class="fa fa-minus"></i>
                                                        </a>
                                                    </span>
                                                    <input class="js_quantity form-control" data-min="1" data-max="{edu_max}" data-edu-purchase="{edu_purchase}" name="add_qty" value="1" type="number">
                                                    <span class="input-group-addon">
                                                        <a href="#" class="mb8 float_left js_add_cart_json">
                                                            <i class="fa fa-plus"></i>
                                                        </a>
                                                    </span>
                                                </div>
                                                {buy_button}
                                            </div>
                                        </form>
                                    </div>
                                    <span class="dn_list_instock">{product_stock}</span>
                                    <!-- key {key} key_raw {key_raw} render_time {render_time} -->
                                    <!-- http:/mcpage/{key} http:/mcpage/{key}/delete  http:/mcmeta/{key} -->
                                </td>
                        </tr>""".format(
                    product_default_code=product['default_code'],
                    return_url='%s/dn_list' % 'https://mariaakerberg.com',
                    product_id=product['id'],
                    product_startdate=campaign.date_start if campaign and campaign.date_start else '',
                    product_stopdate =campaign.date_stop  if campaign and campaign.date_stop else '',
                    product_dfp=self.get_packaging_info(product['id']) or '',
                    shop_widget='{shop_widget}',
                    product_stock='{product_stock}',
                    product_name=product['fullname'],
                    product_price = product_obj.get_pricelist_chart_line(pricelist).get_html_price_short(),
                    product_ribbon_offer = product_ribbon_offer and ('<div class="ribbon ribbon_offer   btn btn-primary">%s</div>' % _('Offer')) or '',
                    product_ribbon_promo = '<div class="ribbon ribbon_news    btn btn-primary">' + _('New') + '</div>' if ribbon_promo.id in (product['website_style_ids'] + product['website_style_ids_variant']) else '',
                    product_ribbon_limited= '<div class="ribbon ribbon_limited btn btn-primary">' + _('Limited<br/>Edition') + '</div>' if ribbon_limited.id in product['website_style_ids_variant'] else '',
                    hide_spinner = 'hidden' if product_obj.purchase_type == 'none' else '',
                    edu_max= '5' if is_edu_purchase else '',
                    edu_purchase= int(is_edu_purchase),
                    buy_button = buttons['list_view'],
                    key_raw=key_raw,
                    key=key,
                    render_time='%s' % (timer() - render_start),
                ).encode('utf-8')
                self.env['website'].put_page_dict(key_raw, flush_type, page, 'product.product,%s' % product['id'])
                page_dict['page'] = base64.b64encode(page)
            stock_info = self.get_stock_info(product['id'])
            rows.append(page_dict.get('page', '').decode('base64').format(shop_widget='' if stock_info[0] else 'hidden', product_stock=stock_info[2]))
        return rows

    # Product detail view with all variants
    @api.model
    def get_product_detail(self, product, variant_id, nbr=0):
        # right side product.description, directly after stock_status
        webshop_version = self.env['ir.config_parameter'].get_param('webshop_dermanord.filter_version')

        ## https://developers.google.com/search/docs/data-types/product
        ## https://schema.org/
        ## J-son code for product placement in google-index.
        def product_json_desc(variant, product, pricelist):
            product_images = variant.sudo().image_attachment_ids.sorted(key=lambda a: a.sequence)
            images = []
            for i in product_images:
                images.append(self.env['website'].imagefield_hash('ir.attachment', 'datas', i.id, 'website_sale_product_gallery.img_product_thumbnail'))
                images.append(self.env['website'].imagefield_hash('ir.attachment', 'datas', i.id, 'website_sale_product_gallery.img_product_detail'))
            jsonPageData = u"""<script type="application/ld+json">%s</script>""" % json.dumps(
            {
            "@context": "https://schema.org/",
            "@type": "Product",
            "name": variant.name,
            "image": images,
            "description": variant.public_desc,
            "sku": variant.default_code,
            "brand": {
                "@type": "Brand",
                "name": "Maria &Aring;kerberg"
            },
            "offers": {
                "@type": "Offer",
                "url": "https://mariaakerberg.com/dn_shop/variant/%s" % variant.id,
                "priceCurrency": "SEK",
                "price": variant.sudo().pricelist_chart_ids.with_context(pricelist = pricelist).filtered(lambda p: p.pricelist_chart_id.pricelist == p._context.get('pricelist')).price,
                "itemCondition": "https://schema.org/UsedCondition",
                "availability": u"$LEFT_MASVINGE$%s$RIGHT_MASVINGE$" % ('%s_google_stock_status' % variant.id),
                "seller": {
                    "@type": "Organization",
                    "name": "Maria &Aring;kerberg"
                    }
                }
            })
            # ~ _logger.warn(jsonPageData)
            # ~ https://schema.org/Product
            # 2019-03-08 Replace curly braces in two step: 1. To escape curly braces. 2. To parse code using curly braces.
            return jsonPageData.replace('{', '{{').replace('}', '}}').replace(u'$LEFT_MASVINGE$', u'{').replace(u'$RIGHT_MASVINGE$', u'}')

        def html_product_detail_desc( variant, partner, pricelist):
            is_reseller = False
            if pricelist and pricelist.for_reseller:
                is_reseller = True
            category_html = ''
            category_value = ''
            for idx, c in enumerate(variant.public_categ_ids):
                if idx != 0:
                    category_html += '<span style="color: #bbb;">, </span>'
                category_html += '<a href="/%s/category/%s"><span style="color: #bbb;">%s</span></a>' %(webshop_version, c.id, c.display_name)
                category_value += '&amp;category_%s=%s' %(c.id, c.id)
            facet_html = ''
            for line in variant.facet_line_ids:
                facet_html += '<div class="col-md-6"><h2 class="dn_uppercase">%s</h2>' %line.facet_id.name
                for idx, value in enumerate(line.value_ids):
                    facet_html += '<a href="/%s?facet_%s_%s=%s%s" class="text-muted"><span>%s</span></a>' %(webshop_version, line.facet_id.id, value.id, value.id, category_value, value.name)
                    if idx != len(line.value_ids)-1:
                        facet_html += '<span>, </span>'
                facet_html += '</div>'
            page = u"""<div>
    {public_desc}
    <h4 class="show_more_facet text-center hidden-lg hidden-md hidden-sm" style="text-decoration: underline;">{more_info}<i class="fa fa-angle-down"></i></h4>
    <div class="container facet_container hidden-xs">
        <div class="col-md-12 no_padding_div">
            {use_desc_title}
            {use_desc}
            {reseller_desc_title}
            {reseller_desc}
        </div>
        <div class="col-md-12 no_padding_div">
            <h2 class="category_title dn_uppercase">{category_title}</h2>
            {category_html}
        </div>
        <div class="col-md-12 facet_div">
            {facet_html}
        </div>
        <h4 class="hide_more_facet text-center hidden-lg hidden-md hidden-sm hidden" style="text-decoration: underline;">{less_info}<i class="fa fa-angle-up"></i></h4>
    </div>
</div>""".format(
                public_desc = '<p class="text-muted public_desc%s">%s</p>' %('' if variant.public_desc else ' hidden', variant.public_desc.replace('\n', '<br/>') if variant.public_desc else ''),
                more_info = _('More info'),
                use_desc_title = '<h2 class="use_desc_title dn_uppercase%s">%s</h2>' %('' if variant.use_desc else ' hidden', _('Directions')),
                use_desc = '<p class="text-muted use_desc%s">%s</p>' %('' if variant.use_desc else ' hidden', variant.use_desc.replace('\n', '<br/>') if variant.use_desc else ''),
                reseller_desc_title = '<h2 class="reseller_desc_title dn_uppercase%s">%s</h2>' %('' if variant.reseller_desc and is_reseller else ' hidden', _('For Resellers')),
                reseller_desc = '<p class="text-muted reseller_desc%s">%s</p>' %('' if variant.reseller_desc and is_reseller else ' hidden', variant.reseller_desc.replace('\n', '<br/>') if variant.reseller_desc else ''),
                category_title = _('Categories'),
                category_html = category_html,
                facet_html = facet_html,
                less_info = _('Less info')
            )
            return page

        # left side product image with image nav bar, product ingredients with nav bar
        def html_product_detail_image( variant, partner):
            ribbon_limited = self.env.ref('webshop_dermanord.image_limited')
            ribbon_promo = self.env.ref('website_sale.image_promo')
            ribbon_wrapper = ''
            if len(variant.website_style_ids_variant) > 0:
                if variant.website_style_ids_variant[0] == ribbon_promo:
                    ribbon_wrapper = '<div class="ribbon-wrapper"><div class="ribbon_news btn btn-primary">%s</div></div>' %_('New')
                elif variant.website_style_ids_variant[0] == ribbon_limited:
                    ribbon_wrapper = '<div class="ribbon-wrapper"><div class="ribbon_news btn btn-primary">%s</div></div>' %_('Limited Edition')
            elif len(variant.product_tmpl_id.website_style_ids) > 0:
                if variant.product_tmpl_id.website_style_ids[0] == ribbon_promo:
                    ribbon_wrapper = '<div class="ribbon-wrapper"><div class="ribbon_news btn btn-primary">%s</div></div>' %_('New')
                elif variant.product_tmpl_id.website_style_ids[0] == ribbon_limited:
                    ribbon_wrapper = '<div class="ribbon-wrapper"><div class="ribbon_news btn btn-primary">%s</div></div>' %_('Limited Edition')
            offer_wrapper = '<div class="offer-wrapper"><div class="ribbon ribbon_offer btn btn-primary">%s</div></div>' %_('Offer') if variant.is_offer_product_reseller or variant.is_offer_product_consumer else ''
            product_images = variant.sudo().image_attachment_ids.sorted(key=lambda a: a.sequence)
            product_images_html = ''
            product_images_nav_html = ''
            if len(product_images) > 0:
                for idx, image in enumerate(product_images):
                    product_images_html += '<div id="image_%s_%s" class="tab-pane fade%s">%s%s<img class="img img-responsive product_detail_img" style="margin: auto;" src="%s"/></div>' %(variant.id, image.id, ' active in' if idx == 0 else '', offer_wrapper, ribbon_wrapper, self.env['website'].imagefield_hash('ir.attachment', 'datas', image[0].id, 'website_sale_product_gallery.img_product_detail'))
                    product_images_nav_html += '<li class="%s"><a data-toggle="tab" href="#image_%s_%s"><img class="img img-responsive" src="%s"/></a></li>' %('active' if idx == 0 else '', variant.id, image.id, self.env['website'].imagefield_hash('ir.attachment', 'datas', image[0].id, 'website_sale_product_gallery.img_product_thumbnail'))
            else:
                product_images_html += '<div id="image_%s" class="tab-pane fade active in">%s%s<img class="img img-responsive product_detail_img" style="margin: auto; width: 505px; height: 505px;" src="/web/static/src/img/placeholder.png"/></div>' %(variant.id, offer_wrapper, ribbon_wrapper)
                product_images_nav_html = '<li class="active"><a data-toggle="tab" href="#image_%s"><img class="img img-responsive" src="/web/static/src/img/placeholder.png"/></a></li>' %variant.id
            ingredients_images_nav_html = ''
            product_ingredients = self.env['product.ingredient'].search([('product_ids', 'in', variant.id)], order='sequence')
            if len(product_ingredients) > 0:
                for i in product_ingredients:
                    ingredients_images_nav_html += '<a href="/%s?current_ingredient=%s"><div class="col-md-3 col-sm-3 ingredient_desc" style="padding: 0px;"><img class="img img-responsive" style="margin: auto;" src="%s"/><h6 class="text-center text-primary" style="padding: 0px; margin-top: 0px;"><i>%s</i></h6></div></a>' %(webshop_version, i.id, self.env['website'].imagefield_hash('product.ingredient', 'image', i.id, 'product_ingredients.img_ingredients'), i.name)
            page = u"""<div id="image_big" class="tab-content">
    {product_images_html}
</div>
<ul id="image_nav" class="nav nav-pills">
    {product_images_nav_html}
</ul>
<div id="ingredients_div">
    <div class="container mb16 hidden-xs">
        <h2 class="mt64 mb32 text-center dn_uppercase">{ingredients_title}</h2>
        {ingredients_images_nav_html}
    </div>
</div>
<p id="current_product_id" data-value="{current_product_id}" class="hidden"/>
<div id="ingredients_description" class="container hidden-xs {hide_ingredients_desc}">
    <div class="mt16">
        <p>
            <strong class="dn_uppercase">{ingredients} </strong>
            <span class="text-muted">
                {ingredients_desc}
            </span>
        </p>
    </div>
</div>
{html_alternative_products}
{html_accessory_products}
""".format(
                product_images_html = product_images_html,
                product_images_nav_html = product_images_nav_html,
                ingredients_title = _('made from all-natural ingredients') if len(product_ingredients) > 0 else '',
                ingredients_images_nav_html = ingredients_images_nav_html,
                current_product_id = variant.id,
                hide_ingredients_desc = '' if variant.ingredients else 'hidden',
                ingredients = _('ingredients:'),
                ingredients_desc = variant.ingredients.replace('\n', '<br/>') if variant.ingredients else '',
                html_alternative_products = generate_alternative_products(variant, partner),
                html_accessory_products =  generate_accessory_products(variant, partner),
            )
            
            return page

        def generate_alternative_products(variant, partner):
            if variant.alternative_product_ids:

                
                page = u"""<div id="alternatives_div">
                            <div class="container hidden-xs">
                                <h2 class="text-center dn_uppercase mt32 mb32">Suggested alternatives:</h2>"""
                
                thumb_list = self.product_tmpl_id.get_thumbnail_default_variant2(partner.property_product_pricelist.id, variant.alternative_product_ids.read(['name', 'dv_ribbon','is_offer_product_reseller', 'is_offer_product_consumer','dv_image_src',]))
                for th in thumb_list:
                    page += th.decode('utf-8').replace("col-md-4", "col-md-6", 1)
                
                page += """</div></div>"""
                
            else:
                page = u""""""
            
            return page
            
        def generate_accessory_products(variant, partner):
            if variant.accessory_product_ids:
                
                page = u"""<div id="accessory_div">
                            <div class="container hidden-xs">
                                <h2 class="text-center dn_uppercase mt32 mb32">Suggested accessories:</h2>"""
                
                thumb_list = self.product_tmpl_id.get_thumbnail_variant(partner.property_product_pricelist.id, variant.accessory_product_ids.read(['name', 'dv_ribbon','is_offer_product_reseller', 'is_offer_product_consumer','dv_image_src',]))
                for th in thumb_list:
                    page += th.decode('utf-8').replace("col-md-4", "col-md-6", 1)
                
                page += u"""</div></div>"""
                
            else:
                page = u""""""
            
            return page

        # product ingredients in mobile, directly after <section id="product_detail"></section>
        def html_product_ingredients_mobile(variant, partner):
            ingredients_carousel_html = ''
            ingredients_carousel_nav_html = ''
            product_ingredients = self.env['product.ingredient'].search([('product_ids', 'in', variant.id)], order='sequence')
            if len(product_ingredients) > 0:
                for idx, i in enumerate(product_ingredients):
                    ingredients_carousel_html += '<div class="item ingredient_desc%s"><a href="/%s?current_ingredient=%s"><img class="img img-responsive" style="margin: auto; display: block;" src="%s"/><h6 class="text-center" style="padding: 0px; margin-top: 0px;"><i>%s</i></h6></a></div>' %(' active' if idx == 0 else '', webshop_version, i.id, self.env['website'].imagefield_hash('product.ingredient', 'image', i.id, 'product_ingredients.img_ingredients'), i.name)
                    ingredients_carousel_nav_html += '<li class="%s" data-slide-to="%s" data-target="#%s_ingredient_carousel"></li>' %(' active' if idx == 0 else '', idx, variant.id)

            page = u"""<div id="ingredients_div_mobile">
    <div class="container mb16 hidden-lg hidden-md hidden-sm">
        <h4 class="text-center dn_uppercase">{ingredients_title}</h4>
        <div class="col-md-12">
            <div class="carousel slide" id="{product_id}_ingredient_carousel" data-ride="carousel">
                <div class="carousel-inner" style="width: 100%;">
                    {ingredients_carousel_html}
                </div>
                <div class="carousel-control left" data-slide="prev" data-target="#{product_id}_ingredient_carousel" href="#{product_id}_ingredient_carousel" style="width: 10%; left: 0px;"><i class="fa fa-chevron-left" style="right: 20%; color: #000;"></i></div>
                <div class="carousel-control right" data-slide="next" data-target="#{product_id}_ingredient_carousel" href="#{product_id}_ingredient_carousel" style="width: 10%; right: 0px;"><i class="fa fa-chevron-right" style="left: 20%; color: #000;"></i></div>
                <ol class="carousel-indicators" style="bottom: -10px;">
                    {ingredients_carousel_nav_html}
                </ol>
            </div>
        </div>
    </div>
</div>
<div id="ingredients_description_mobile" class="container hidden-lg hidden-md hidden-sm">
    <p><strong class="dn_uppercase">{ingredients} </strong><span class="text-muted">{ingredients_desc}</span></p>
</div>""".format(
                product_id = variant.id,
                ingredients_title = _('made from all-natural ingredients') if len(product_ingredients) > 0 else '',
                ingredients_carousel_html = ingredients_carousel_html,
                ingredients_carousel_nav_html = ingredients_carousel_nav_html,
                ingredients = _('ingredients:'),
                ingredients_desc = variant.ingredients.replace('\n', '<br/>') if variant.ingredients else ''
            )
            return page

        partner = self.env.user.partner_id.commercial_partner_id
        pricelist = partner.property_product_pricelist
        flush_type = 'get_product_detail'
        key_raw = 'product_detail %s %s %s %s %s %s %s %s' % (
            self.env.cr.dbname, flush_type, product.id, pricelist.id, self.env.lang,
            request.session.get('device_type', 'md'),
            self.env.user in self.sudo().env.ref('base.group_website_publisher').users,
            ','.join([str(id) for id in sorted(self.env.user.commercial_partner_id.access_group_ids._ids)]))
        key, page_dict = self.env['website'].get_page_dict(key_raw)
        if not page_dict:
            render_start_tot = timer()
            page = ''
            visible_attrs = set(l.attribute_id.id for l in product.attribute_line_ids if len(l.value_ids) > 1)
            decimal_precision = pricelist.currency_id.rounding
            variants = self.env['product.product'].search([('id', 'in', product.product_variant_ids.mapped('id'))])
            product_variant = self.browse(variant_id)
            for variant in variants:
                render_start = timer()
                attr_sel = ''
                is_edu_purchase = variant.purchase_type == 'edu'
                buttons = variant.get_add_to_cart_buttons()
                for attribute in variant.attribute_value_ids.sorted(key=lambda a: a.id):
                    attr_sel += '<li><strong style="font-family: futura-pt-light, sans-serif; font-size: 18px;">%s</strong><select class="form-control js_variant_change attr_sel" name="attribute-%s-%s">' %(attribute.attribute_id.name, product.id, attribute.attribute_id.id)
                    for att in variants.mapped('attribute_value_ids').with_context(attribute_id=attribute.attribute_id.id).filtered(lambda a: a.attribute_id.id == a.env.context.get('attribute_id')):
                        attr_sel += '<option value="%s" %s><span>%s</span></option>' %(att.id, 'selected="selected"' if att in product_variant.attribute_value_ids else '', att.name)
                    attr_sel += '</select></li>'

                # ~ variant_value_ids = product.product_variant_ids.mapped('attribute_value_ids')
                # ~ if len(product.attribute_line_ids) > 0:
                    # ~ for attr_line in product.attribute_line_ids:
                        # ~ if attr_line.attribute_id.type in ['select', 'hidden']:
                            # ~ attr_sel += '<li><strong style="font-family: futura-pt-light, sans-serif; font-size: 18px;">%s</strong><select class="form-control js_variant_change attr_sel" name="attribute-%s-%s">' %(attr_line.attribute_id.name, product.id, attr_line.attribute_id.id)
                            # ~ for value_id in attr_line.value_ids:
                                # ~ if value_id in variant_value_ids:
                                    # ~ attr_sel += '<option value="%s" %s><span>%s</span></option>' %(value_id.id, 'selected="selected"' if value_id in product_variant.attribute_value_ids else '', value_id.name)
                            # ~ attr_sel += '</select></li>'

            # ~ <t t-if="variant_id.attribute_id.type == 'radio'">
              # ~ <ul class="list-unstyled">
                  # ~ <t t-set="inc" t-value="0"/>
                  # ~ <t t-foreach="variant_id.value_ids" t-as="value_id">
                      # ~ <li class="form-group js_attribute_value" style="margin: 0;">
                          # ~ <label class="control-label" style="margin: 0 20px;">
                              # ~ <input type="radio" class="js_variant_change" t-att-checked="'checked' if not inc else ''" t-att-name="'attribute-%s-%s' % (product.id, variant_id.attribute_id.id)" t-att-value="value_id.id" style="vertical-align: top; margin-right: 10px;"/>
                              # ~ <span t-field="value_id.name"/>
                              # ~ <span class="badge" t-if="value_id.price_extra">
                                  # ~ <t t-esc="value_id.price_extra > 0 and '+' or ''"/><span t-field="value_id.price_extra" style="white-space: nowrap;" t-field-options='{
                                          # ~ "widget": "monetary",
                                          # ~ "from_currency": "product.company_id.currency_id",
                                          # ~ "display_currency": "user_id.partner_id.property_product_pricelist.currency_id"
                                       # ~ }'/>
                              # ~ </span>
                          # ~ </label>
                      # ~ </li>
                      # ~ <t t-set="inc" t-value="inc+1"/>
                  # ~ </t>
              # ~ </ul>
            # ~ </t>

            # ~ <t t-if="variant_id.attribute_id.type == 'color'">
              # ~ <ul class="list-inline">
                  # ~ <t t-set="inc" t-value="0"/>
                  # ~ <li t-foreach="variant_id.value_ids" t-as="value_id">
                      # ~ <label t-attf-style="background-color:#{value_id.color or value_id.name}"
                          # ~ t-attf-class="css_attribute_color #{'active' if not inc else ''}">
                        # ~ <input type="radio" class="js_variant_change"
                          # ~ t-att-checked="'checked' if not inc else ''"
                          # ~ t-att-name="'attribute-%s-%s' % (product.id, variant_id.attribute_id.id)"
                          # ~ t-att-value="value_id.id"
                          # ~ t-att-title="value_id.name"/>
                      # ~ </label>
                      # ~ <t t-set="inc" t-value="inc+1"/>
                  # ~ </li>
              # ~ </ul>
            # ~ </t>

          # ~ </li>
        # ~ </t>

                #TODO:
                # ~ if not chart_line:
                    # ~ price += _("No price available")
                pricelist_line = variant.get_pricelist_chart_line(pricelist)
                campaign = variant.campaign_ids[0] if variant.campaign_ids else None
                page += u"""<t t-set="title" t-value="{product_name}"/>
    <section id="section_{attribute_value}" class="product_detail container mt8 oe_website_sale discount {hide_variant}">
    <div class="row">
        <div class="col-sm-4 {publisher_manager}">
            <div groups="base.group_website_publisher" class="pull-right css_editable_mode_hidden" style="">
                <div class="btn-group js_publish_management {website_published}" data-id="{product_id}" data-object="product.template">
                    <button class="btn btn-danger js_publish_btn">{not_published}</button>
                    <button class="btn btn-success js_publish_btn">{published}</button>
                    <button type="button" class="btn btn-default dropdown-toggle" id="dopprod-{product_id}" data-toggle="dropdown">
                        <span class="caret"></span>
                    </button>
                    <ul class="dropdown-menu" role="menu" aria-labelledby="'dopprod-{product_id}">
                        <li>
                            <a href="#" class="js_publish_btn">
                                <span class="css_unpublish">Unpublish</span>
                                <span class="css_publish">Publish</span>
                            </a>
                        </li>
                        <li>
                            {action}
                        </li>
                    </ul>
                </div>
            </div>
        </div>
    </div>
    <div class="row mb32">
        <div class="col-sm-7 col-md-7 col-lg-7">
            {html_product_detail_image}
        </div>
        <div class="col-sm-5 col-md-5 col-lg-4 col-lg-offset-1">
            <h1 itemprop="name">{product_name}</h1>
            <h4 class="text-muted default_code">{default_code}</h4>
            <form action="/shop/cart/update" class="js_add_cart_variants" data-attribute_value_ids="{variant_ids}" method="POST">
                <div class="js_product">
                    <input class="product_id" name="product_id" value="{variant_id}" type="hidden">
                    <ul class="list-unstyled js_add_cart_variants nav-stacked" data-attribute_value_ids="{data_attribute_value_ids}">
                        {attr_sel}
                    </ul>
                    <div itemprop="offers" itemscope="itemscope" class="product_price mt16 mb16">
                        <p class="oe_price_h4 css_editable_mode_hidden decimal_precision" data-precision="{decimal_precision}">
                            {product_price}
                        </p>
                    </div>
                    <div class="css_quantity input-group oe_website_spinner {spinner_hidden}">
                        <span class="input-group-addon">
                            <a href="#" class="mb8 js_add_cart_json">
                                <i class="fa fa-minus"></i>
                            </a>
                        </span>
                        <input class="js_quantity form-control" data-min="1" data-max="{edu_max}" data-edu-purchase="{edu_purchase}" name="add_qty" value="1" type="number"/>
                        <span class="input-group-addon">
                            <a href="#" class="mb8 float_left js_add_cart_json">
                                <i class="fa fa-plus"></i>
                            </a>
                        </span>
                    </div>
                    {buy_button}
                    <h5>
                        <div>
                            <span>{product_startdate}</span>&nbsp;<span>{product_stopdate}</span>
                        </div>
                    </h5>
                </div>
            </form>
            <div class="stock_status mb16">
                <span>{stock_status}</span>
            </div>
            {html_product_detail_desc}
        </div>
    </div>
    {html_product_ingredients_mobile}
</section>
{website_description}
{html_product_json_desc}
<!-- key {key} key_raw {key_raw} render_time {render_time} -->
<!-- http:/mcpage/{key} http:/mcpage/{key}/delete  http:/mcmeta/{key} -->
""".format(
                    attribute_value = '_'.join([str(v.id) for v in variant.attribute_value_ids.sorted(lambda key: key.id)]),
                    product_id = product.id,
                    variant_id = variant.id,
                    hide_variant = '' if variant.id == variant_id else 'hidden',
                    website_published = variant.website_published and 'css_published' or 'css_unpublished',
                    publisher_manager = '' if self.env.user in self.env.ref('base.group_website_publisher').sudo().users else 'hidden',
                    not_published = _('Not Published'),
                    published = _('Published'),
                    unpublish = _('Unpublish'),
                    publish = _('Publish'),
                    action = '<a href="/web#return_label=Website&amp;view_type=form&amp;model=product.template&amp;id=%s&amp;action=%s" title="%s">Edit</a>' %(product.id, 'product.product_template_action', _('Edit in backend')),
                    product_name = variant.name,
                    default_code = variant.default_code or '',
                    variant_ids = product.product_variant_ids.mapped('id'),
                    data_attribute_value_ids = [[p.id, [v.id for v in p.attribute_value_ids if v.attribute_id.id in visible_attrs], pricelist_line.price, pricelist_line.rec_price, '{%s_in_stock}' % p.id] for p in product.product_variant_ids],
                    attr_sel = attr_sel,
                    decimal_precision = decimal_precision,
                    product_price = pricelist_line.get_html_price_long(),
                    spinner_hidden = '{%s_buy_button_hidden}' % variant.id,
                    edu_max= '5' if is_edu_purchase else '',
                    edu_purchase = int(is_edu_purchase),
                    buy_button = buttons['product_view'],
                    product_startdate = _('Available on %s') %campaign.date_start if campaign and campaign.date_start else '',
                    product_stopdate = _('to %s') %campaign.date_stop if campaign and campaign.date_stop else '',
                    stock_status = '{%s_stock_status}' % variant.id,
                    html_product_detail_desc = html_product_detail_desc(variant, partner, pricelist),
                    html_product_detail_image = html_product_detail_image(variant, partner),
                    # 2019-03-08 json https://schema.org/ImageObject
                    # https://developers.google.com/search/docs/data-types/product
                     html_product_json_desc = product_json_desc(variant, variant.product_tmpl_id, pricelist),
                    html_product_ingredients_mobile = html_product_ingredients_mobile(variant, partner),
                    website_description = u'<div itemprop="description" class="oe_structure mt16" id="product_full_description">%s</div>' %variant.website_description if variant.website_description else '',
                    key_raw=key_raw,
                    key=key,
                    render_time='%s' % (timer() - render_start),
                ).encode('utf-8')
            page += "\n<!-- render_time_total %s -->\n" % (timer() - render_start_tot)
            self.env['website'].put_page_dict(key_raw, flush_type, page, '%s,%s' % (product._model, product.id))
            page_dict['page'] = base64.b64encode(page)
        stock = {}
        for variant in product.product_variant_ids:
            # ~ _logger.warn('%s' % variant.id)
            #{
            #    '123_in_stock': True / False,
            #    '123_in_stock_state': 'short' / 'few' / 'in',
            #    '123_stock_status': 'Slut' / 'Fåtal' / 'I lager',
            #    '123_google_stock_status': 'https://schema.org/InStock' / 'https://schema.org/LimitedAvailability' / 'https://schema.org/OutOfStock'
            #}
            # https://schema.org/InStock
            # https://schema.org/LimitedAvailability
            # https://schema.org/OutOfStock
            stock['%s_in_stock' %variant.id], stock['%s_in_stock_state' %variant.id], stock['%s_stock_status' % variant.id] = self.get_stock_info(variant.id)
            stock['%s_google_stock_status' %variant.id] = {'short': 'https://schema.org/OutOfStock', 'few': 'https://schema.org/LimitedAvailability', 'in': 'https://schema.org/InStock'}[stock['%s_in_stock_state' %variant.id]]
            if not pricelist.for_reseller:
                stock['%s_stock_status' % variant.id] = ''
                stock['%s_buy_button_hidden' % variant.id] = 'hidden'
            elif (stock['%s_in_stock' %variant.id] and variant.sale_ok and variant.purchase_type != 'none'):
                stock['%s_buy_button_hidden' % variant.id] = ''
            else:       
                stock['%s_buy_button_hidden' % variant.id] = 'hidden'
                
        try:
            # ~ _logger.warn(stock)
            return page_dict.get('page','').decode('base64').format(**stock)
        except:
            _logger.warn(traceback.format_exc())
            if nbr == 0:
                nbr = 1
                request.website.remove_page_dict(key_raw)
                return self.env['product.product'].browse(variant_id).get_product_detail(product, variant_id, nbr=nbr)
            else:
                user = request.env.user
                if not user:
                    user = request.env['res.users'].with_context(active_test=False).browse(request.env.uid).sudo()
                _logger.warn('Get_product_detail: %s (%s) has variants missing in: %s for user %s' %(product.name, product.id, stock,user.login))
                subject = u'Felaktig konfiguration av %s' % product.name
                body = u'Användaren %s (%s) har varianter i visningen som saknas %s (%s): %s.' % (user.login, user.id, product.name, product.id,stock)
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
                        'dn_404_message': _("Missmatch variants and stock."),
                        'status_code': 404,
                        'status_message': werkzeug.http.HTTP_STATUS_CODES[404]
                    })
                return werkzeug.wrappers.Response(html, status=404, content_type='text/html;charset=utf-8')


class Website(models.Model):
    _inherit = 'website'

    @api.model
    def get_page_dict(self, key_raw):
        # ~ _logger.warn('get_page_dict %s' % key_raw)
        key = str(memcached.MEMCACHED_HASH(key_raw.encode('latin-1')))
        # ~ page_dict = None
        # ~ return key,page_dict
        try:
            page_dict = memcached.mc_load(key)
        except MemcacheClientError as e:
            error = "MemcacheClientError %s " % e
            _logger.warn(error)
        except MemcacheUnknownCommandError as e:
            error = "MemcacheUnknownCommandError %s " % e
            _logger.warn(error)
        except MemcacheIllegalInputError as e:
            error = "MemcacheIllegalInputError %s " % e
            _logger.warn(error)
        except MemcacheServerError as e:
            error = "MemcacheServerError %s " % e
            _logger.warn(error)
        except MemcacheUnknownError as e:
            error = str(e)
            _logger.warn("MemcacheUnknownError %s key: %s path: %s" % (eror, key, request.httprequest.path))
        except MemcacheUnexpectedCloseError as e:
            error = "MemcacheUnexpectedCloseError %s " % e
            _logger.warn(error)
        except Exception as e:
            err = sys.exc_info()
            # ~ error = "Memcached Error %s key: %s path: %s %s" % (e,key,request.httprequest.path, ''.join(traceback.format_exception(err[0], err[1], err[2])))
            error = ''.join(traceback.format_exception(err[0], err[1], err[2]))
            _logger.warn("Memcached Error %s key: %s path: %s" % (error, key, 'thumbnail'))
            error = str(e)
        return key,page_dict

    @api.model
    def put_page_dict(self, key_raw, flush_type, page, path):
        key = str(memcached.MEMCACHED_HASH(key_raw.encode('latin-1')))
        page_dict = {
            # ~ 'ETag':     '%s' % MEMCACHED_HASH(page),
            # ~ 'max-age':  max_age,
            # ~ 'cache-age':cache_age,
            # ~ 'private':  routing.get('private',False),
            'key_raw':  key_raw,
            # ~ 'render_time': '%.3f sec' % (timer()-render_start),
            # ~ 'controller_time': '%.3f sec' % (render_start-controller_start),
            'path':     path,
            'db':       self.env.cr.dbname,
            'page':     base64.b64encode(page),
            # ~ 'date':     http_date(),
            'module':   'webshop_dermanord',
            'status_code': 200,
            'flush_type': flush_type,
            # ~ 'headers': [],
            }
        # ~ MEMCACHED.mc_save(key, page_dict,24 * 60 * 60 * 7)  # One week
        memcached.mc_save(key, page_dict,60*60*24*7)  # One week

    @api.model
    def remove_page_dict(self, key_raw):
        key = str(memcached.MEMCACHED_HASH(key_raw.encode('latin-1')))
        # ~ MEMCACHED.mc_save(key, page_dict,24 * 60 * 60 * 7)  # One week
        memcached.mc_delete(key)  # One week
