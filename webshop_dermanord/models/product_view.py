# -*- coding: utf-8 -*-
##############################################################################
#
# odoo, Open Source Management Solution, third party addon
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

from odoo import models, fields, api, _
from datetime import datetime, date, timedelta
from openerp.addons.website_memcached import memcached
import base64
import werkzeug

from odoo import http
from odoo.http import request

from timeit import default_timer as timer
import sys, traceback
import json

import logging
_logger = logging.getLogger(__name__)

from odoo.tools.translate import GettextAlias
from odoo import SUPERUSER_ID
import inspect
import odoo


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

                        <!-- Available in more variants -->
                        <a href="/dn_shop/{view_type}/{product_id}">
                            <div class="dn_product_variants_div" {if_product_variants}>
                                <h5 class="text-muted">
                                    + {lang_variants}
                                </h5>
                            </div>
                        </a>
                        <!-- Available in more variants End-->

                    </div>
                    <!-- Product info end -->-->
                </div>
            </form>
</div>
"""

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.depends('name', 'list_price', 'default_code', 'description_sale', 'image_1920', 'attribute_line_ids.value_ids', 'sale_ok', 'product_variant_ids.sale_ok')
    def _get_all_variant_data(self):
        _logger.warning(f"self: {self}, context: {self.env.context}")
        _logger.warning("GET_ALL_VARIANT_DATA!!!"*99)
        placeholder = '/web/static/src/img/placeholder.png'

        for p in self:
            if type(p.id) != int:
                continue
            if not p.product_variant_ids:
                continue
            try:
                variant = p.get_default_variant().read(['name', 'fullname', 'default_code', 'description_sale', 'image_1920', 'sale_ok'])[0]
                if p.sale_ok and not variant['sale_ok']:
                    raise Warning(_('Default variant on %s can not be sold' % p.name))
                _logger.warning(f"made it past first check, product: {p}")
                p.dv_id = variant['id']
                p.dv_default_code = variant['default_code'] or ''
                p.dv_description_sale = variant['description_sale'] or ''
                p.dv_name = p.name if p.use_tmpl_name else variant['fullname']
                p.dv_image_src = variant['image_1920']
                # ~ p.dv_ribbon = ''
                p.dv_ribbon = "oe_image_full"
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
                    maily = {
                        'body': tb.replace('\n', '<br/>'),
                        'subject': 'Default variant recompute failed on %s' % p.name,
                        'author_id': self.env.ref('base.partner_root').id,
                        'res_id': p.id,
                        'model': p._name,
                        'message_type': 'notification',
                        'partner_ids': [(4, pid) for pid in p.message_follower_ids.mapped('id')],
                    }
                    _logger.warning(f"maily: {maily}")
                    self.env['mail.message'].create(maily)
                p.dv_default_code = 'error'
                p.dv_description_sale = msg
                p.dv_name = 'Error'
                p.dv_image_src = placeholder
                p.dv_ribbon = "oe_image_full"

    dv_id = fields.Integer(compute='_get_all_variant_data', store=True)
    dv_default_code = fields.Char(compute='_get_all_variant_data', store=True)
    dv_description_sale = fields.Text(compute='_get_all_variant_data', store=True)
    dv_image_src = fields.Char(compute='_get_all_variant_data', store=True)
    dv_name = fields.Char(compute='_get_all_variant_data', store=True)
    dv_ribbon = fields.Char(compute='_get_all_variant_data', store=True)


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

        for product in self.env['product.template'].search_read(domain, fields=['name', 'dv_ribbon','is_offer_product_reseller', 'is_offer_product_consumer','dv_image_src', 'product_variant_count'], limit=limit, order=order,offset=offset):
            # ~ _logger.warn('get_thumbnail_default_variant --------> %s' % (product))
            key_raw = 'thumbnail_default_variant %s %s %s %s' % (
                self.env.cr.dbname, 
                product['id'], 
                pricelist.id, 
                self.env.lang)   # db produkt prislista språk
                
            key,page_dict = self.env['website'].get_page_dict(key_raw)
            # ~ _logger.warn('get_thumbnail_default_variant --------> %s %s' % (key,page_dict))
            if not page_dict:
                render_start = timer()
                if not ribbon_limited:
                    ribbon_limited = request.env.ref('webshop_dermanord.image_limited')
                    ribbon_promo   = request.env.ref('website_sale.image_promo')

                page = THUMBNAIL.format(
                    details=_('DETAILS'),
                    product_id=product['id'],
                    # ~ product_image=self.env['website'].imagefield_hash('ir.attachment', 'datas', variant.image_main_id[0].id, 'snippet_dermanord.img_product') if variant.image_main_id else '',
                    product_image=product['dv_image_src'],
                    product_name=product['name'],
                    product_price = self.env['product.template'].browse(product['id']).get_pricelist_chart_line(pricelist).get_html_price_long(),
                    product_ribbon=product['dv_ribbon'],
                    # ~ product_ribbon=' '.join([c for c in self.env['product.style'].browse(ribbon_ids).mapped('html_class') if c]),
                    product_ribbon_offer  = '<div class="ribbon ribbon_offer   btn btn-primary">%s</div>' % _('Offer') if (product['is_offer_product_reseller'] and pricelist.for_reseller == True) or (product['is_offer_product_consumer'] and pricelist.for_reseller == False) else '',
                    product_ribbon_promo  = '<div class="ribbon ribbon_news    btn btn-primary">' + _('New') + '</div>' if (product['dv_ribbon'] and (ribbon_promo.html_class in product['dv_ribbon'])) else '',
                    product_ribbon_limited= '<div class="ribbon ribbon_limited btn btn-primary">' + _('Limited<br/>Edition') + '</div>' if (product['dv_ribbon'] and (ribbon_limited.html_class in product['dv_ribbon'])) else '',
                    
                    if_product_variants = 'style="visibility:visible;"' if (product['product_variant_count'] > 1) else 'style="visibility:hidden"',
                    lang_variants = _('Available in more variants'),
                    
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
        _logger.warning(f"thumbnail2 self: {self}, pricelist: {pricelist}, product_ids: {product_ids}")
        if isinstance(pricelist,int):
            pricelist = self.env['product.pricelist'].browse(pricelist)

        thumbnail = []
        flush_type = 'thumbnail_product'
        ribbon_promo = None
        ribbon_limited = None

        user = self.env.ref('base.public_user')

        _logger.warning('Notice get_thunmb2 --------> %s user %s %s %s ' % (self.env.ref('base.public_user'),self.env.user,self._uid,user))

        for product in product_ids:
            _logger.warn('get_thumbnail_default_variant --------> %s' % (product))
            # ~ key_raw = 'thumbnail_default_variant %s %s %s %s' % (
                # ~ self.env.cr.dbname, 
                # ~ product['id'], 
                # ~ pricelist.id, 
                # ~ self.env.lang)   # db produkt prislista språk
            # ~ key, page_dict = self.env['website'].get_page_dict(key_raw)
            # ~ _logger.warn('get_thumbnail_default_variant --------> %s %s' % (key,page_dict))
            if True: #not page_dict:
                render_start = timer()
                # ~ if not ribbon_limited:
                    # ~ ribbon_limited = request.env.ref('webshop_dermanord.image_limited')
                    # ~ ribbon_promo   = request.env.ref('website_sale.image_promo')
                _logger.warning(f"victor product_image: {product['dv_image_src']}")
                page = THUMBNAIL.format(
                    details=_('DETAILS'),
                    product_id=product.id,
                    # ~ product_image=self.env['website'].imagefield_hash('ir.attachment', 'datas', variant.image_main_id[0].id, 'snippet_dermanord.img_product') if variant.image_main_id else '',
                    product_image=product['dv_image_src'],
                    product_name=product['name'],
                    product_price = 42, #self.env['product.template'].browse(product['id']).price,
                    product_ribbon=product['dv_ribbon'],
                    # ~ product_ribbon=' '.join([c for c in self.env['product.style'].browse(ribbon_ids).mapped('html_class') if c]),
                    # ~ product_ribbon_offer  = '<div class="ribbon ribbon_offer   btn btn-primary">%s</div>' % _('Offer') if (product['is_offer_product_reseller'] and pricelist.for_reseller == True) or (product['is_offer_product_consumer'] and  pricelist.for_reseller == False) else '',
                    # ~ product_ribbon_promo  = '<div class="ribbon ribbon_news    btn btn-primary">' + _('New') + '</div>' if (product['dv_ribbon'] and (ribbon_promo.html_class in product['dv_ribbon'])) else '',
                    # ~ product_ribbon_limited= '<div class="ribbon ribbon_limited btn btn-primary">' + _('Limited<br/>Edition') + '</div>' if (product['dv_ribbon'] and (ribbon_limited.html_class in product['dv_ribbon'])) else '',
                    
                    if_product_variants = 'style="visibility:visible;"' if (product['product_variant_count'] > 1) else 'style="visibility:hidden"',
                    lang_variants = _('Available in more variants'),
                    
                    # ~ key_raw=key_raw,
                    # ~ key=key,
                    view_type='product',
                    render_time='%s' % (timer() - render_start),
                    price_from=_('Price From'),
                ).encode('utf-8')

                # ~ self.env['website'].put_page_dict(key_raw, flush_type, page, 'product.template,%s' % product['id'])
                # ~ page_dict['page'] = base64.b64encode(page)
            thumbnail.append(page)
        return thumbnail
        
    @api.model
    def get_thumbnail_variant(self, pricelist, variant_ids):
        if isinstance(pricelist,int):
            pricelist = self.env['product.pricelist'].browse(pricelist)

        thumbnail = []
        flush_type = 'thumbnail_variant'
        ribbon_promo = None
        ribbon_limited = None

        user = self.env.ref('base.public_user')

        _logger.warn('Notice get_thunmb2 --------> %s user %s %s %s ' % (self.env.ref('base.public_user'), self.env.user, self._uid,user))

        for variant in variant_ids:
            key_raw = 'thumbnail_variant %s %s %s %s' % (
                self.env.cr.dbname, 
                variant['id'], 
                pricelist.id, 
                self.env.lang)  # db produkt prislista språk

            key, page_dict = self.env['website'].get_page_dict(key_raw)

            if not page_dict:
                render_start = timer()
                if not ribbon_limited:
                    ribbon_limited = request.env.ref('webshop_dermanord.image_limited')
                    ribbon_promo   = request.env.ref('website_sale.image_promo')

                page = THUMBNAIL.format(
                    details=_('DETAILS'),
                    product_id=variant['id'],
                    # ~ product_image=self.env['website'].imagefield_hash('ir.attachment', 'datas', variant.image_main_id[0].id, 'snippet_dermanord.img_product') if variant.image_main_id else '',
                    product_image=variant['dv_image_src'],
                    product_name=variant['display_name'][0] == '[' and variant['display_name'].split('] ', 1)[1] or variant['display_name'],
                    product_price = self.env['product.product'].browse(variant['id']).get_pricelist_chart_line(pricelist).get_html_price_long(),
                    product_ribbon=variant['dv_ribbon'],
                    # ~ product_ribbon=' '.join([c for c in self.env['product.style'].browse(ribbon_ids).mapped('html_class') if c]),
                    product_ribbon_offer  = '<div class="ribbon ribbon_offer   btn btn-primary">%s</div>' % _('Offer') if (variant['is_offer_product_reseller'] and pricelist.for_reseller == True) or (variant['is_offer_product_consumer'] and pricelist.for_reseller == False) else '',
                    product_ribbon_promo  = '<div class="ribbon ribbon_news    btn btn-primary">' + _('New') + '</div>' if (variant['dv_ribbon'] and (ribbon_promo.html_class in variant['dv_ribbon'])) else '',
                    product_ribbon_limited= '<div class="ribbon ribbon_limited btn btn-primary">' + _('Limited<br/>Edition') + '</div>' if (variant['dv_ribbon'] and (ribbon_limited.html_class in variant['dv_ribbon'])) else '',
                    
                    if_product_variants = 'style="visibility:visible;"' if (variant['product_variant_count'] > 1) else 'style="visibility:hidden"',
                    lang_variants = _('Available in more variants'),
                    
                    key_raw=key_raw,
                    key=key,
                    view_type='variant',
                    render_time='%s' % (timer() - render_start),
                    price_from=_('Price From'),
                ).encode('utf-8')
                # ~ _logger.warn('get_thumbnail_default_variant --------> %s' % (page))
                self.env['website'].put_page_dict(key_raw, flush_type, page, 'product.variant,%s' % variant['id'])
                page_dict['page'] = base64.b64encode(page)
            thumbnail.append(page_dict.get('page', '').decode('base64'))
        return thumbnail



class Website(models.Model):
    _inherit = 'website'

    @api.model
    def get_page_dict(self, key_raw):
        # ~ _logger.warn('get_page_dict %s' % key_raw)
        key = str(memcached.MEMCACHED_HASH(key_raw.encode('latin-1', 'replace')))
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
            _logger.warn("MemcacheUnknownError %s key: %s path: %s" % (error, key, request.httprequest.path))
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
        key = str(memcached.MEMCACHED_HASH(key_raw.encode('latin-1', 'replace')))
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
        memcached.mc_save(key, page_dict, 60*60*24*7)  # One week

    @api.model
    def remove_page_dict(self, key_raw):
        key = str(memcached.MEMCACHED_HASH(key_raw.encode('latin-1', 'replace')))
        # ~ MEMCACHED.mc_save(key, page_dict,24 * 60 * 60 * 7)  # One week
        memcached.mc_delete(key)  # One week
