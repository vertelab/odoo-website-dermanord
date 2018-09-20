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

from openerp import models, fields, api, _
from datetime import datetime, date, timedelta
from openerp.addons.website_memcached import memcached
import base64

from openerp import http
from openerp.http import request

from timeit import default_timer as timer

import logging
_logger = logging.getLogger(__name__)


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
                                <a itemprop="name" href="dn_shop/{view_type}/{product_id}">{product_name}</a>
                            </strong>
                        </h4>
                        {product_price}
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

    product_variant_count = fields.Integer(string='# of Product Variants', compute='_compute_product_variant_count', store=True)

    @api.model
    def get_thumbnail_default_variant(self,domain,limit,order,pricelist):
        thumbnail = []
        flush_type = 'thumbnaile_product'
        # ~ _logger.warn('get_thumbnail_default_variant ------> %s %s %s %s' % (domain,limit,order,pricelist))
        # ~ products = request.env['product.template'].with_context(pricelist=pricelist.id).search_read(domain, fields=['id', 'name', 'use_tmpl_name', 'default_code', 'access_group_ids', 'dv_ribbon', 'is_offer_product_reseller', 'is_offer_product_consumer', 'dv_id', 'dv_image_src', 'dv_name', 'dv_default_code', 'dv_price_45', 'dv_price_20', 'dv_price_en', 'dv_price_eu', 'dv_recommended_price', 'dv_recommended_price_en', 'dv_recommended_price_eu', 'website_style_ids_variant', 'dv_description_sale'], limit=PPG, order=current_order)
        for product in self.env['product.template'].search_read(domain, fields=['id','name', 'use_tmpl_name','dv_ribbon','dv_id' ,'is_offer_product_reseller', 'is_offer_product_consumer','dv_image_src','website_style_ids_variant'], limit=limit, order=order):
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
                    # ~ product_price=self.env['product.product'].browse(product['dv_id']).get_html_price_long(pricelist),
                    product_price=self.env['product.template'].browse(product['id']).get_html_price_long(product['id'], pricelist),
                    product_ribbon=product['dv_ribbon'],
                    # ~ product_ribbon=' '.join([c for c in self.env['product.style'].browse(ribbon_ids).mapped('html_class') if c]),
                    product_ribbon_offer  = '<div class="ribbon ribbon_offer   btn btn-primary">%s</div>' % _('Offer') if (product['is_offer_product_reseller'] and pricelist.for_reseller == True) or (product['is_offer_product_consumer'] and  pricelist.for_reseller == False) else '',
                    product_ribbon_promo  = '<div class="ribbon ribbon_news    btn btn-primary">' + _('New') + '</div>' if ribbon_promo.html_class in product['dv_ribbon'] else '',
                    product_ribbon_limited= '<div class="ribbon ribbon_limited btn btn-primary">' + _('Limited<br/>Edition') + '</div>' if ribbon_limited.html_class in product['dv_ribbon'] else '',
                    key_raw=key_raw,
                    key=key,
                    view_type='product',
                    render_time='%s' % (timer() - render_start),
                ).encode('utf-8')
                # ~ _logger.warn('get_thumbnail_default_variant --------> %s' % (page))
                self.env['website'].put_page_dict(key,flush_type,page)
                page_dict['page'] = base64.b64encode(page)
            thumbnail.append(page_dict.get('page','').decode('base64'))
        return thumbnail

    @api.model
    def get_thumbnail_default_variant2(self,domain,limit,order,pricelist):
        thumbnail = []
        flush_type = 'thumbnaile_product'
        # ~ _logger.warn('------> %s %s %s %s' % (domain,limit,order,pricelist))
        for pid in self.env['product.template'].search_read(domain,['name'], limit=limit, order=order):
        # ~ for product in self.env['product.template'].search(domain,limit=limit,order=order):
            # ~ product = self.env['product.template'].browse(pid['id'])
            # ~ variant = product.product_variant_ids[0]
            # ~ variant = product.get_default_variant()
            _logger.warn('------> %s %s ' % (pid,pid))
            key_raw = 'dn_shop %s %s %s %s %s' % (self.env.cr.dbname,flush_type,pid['id'],pricelist,self.env.lang)  # db flush_type produkt prislista språk
            key,page_dict = self.env['website'].get_page_dict(key_raw)
            _logger.warn('------> %s %s ' % (key,page_dict))
        return thumbnail


class product_product(models.Model):
    _inherit = 'product.product'

    @api.model
    def get_thumbnail_variant(self,domain,limit,order,pricelist_id):
        thumbnail = []

    @api.model
    def get_list_row(self,domain,limit,order,pricelist_id):
        thumbnail = []


class Website(models.Model):
    _inherit = 'website'

    @api.model
    def get_page_dict(self,key_raw):
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
    def put_page_dict(self,key,flush_type,page):
        page_dict = {
            # ~ 'ETag':     '%s' % MEMCACHED_HASH(page),
            # ~ 'max-age':  max_age,
            # ~ 'cache-age':cache_age,
            # ~ 'private':  routing.get('private',False),
            # ~ 'key_raw':  key_raw,
            # ~ 'render_time': '%.3f sec' % (timer()-render_start),
            # ~ 'controller_time': '%.3f sec' % (render_start-controller_start),
            'path':     'none',
            'db':       self.env.cr.dbname,
            'page':     base64.b64encode(page),
            # ~ 'date':     http_date(),
            'module':   'webshop_dermanord',
            'status_code': '200 ok',
            'flush_type': flush_type,
            # ~ 'headers': [],
            }
        # ~ MEMCACHED.mc_save(key, page_dict,24 * 60 * 60 * 7)  # One week
        memcached.mc_save(key, page_dict,60*60)  # One minute

