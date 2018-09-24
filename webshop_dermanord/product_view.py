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
        flush_type = 'thumbnail_product'
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

class product_product(models.Model):
    _inherit = 'product.product'

    @api.model
    def get_thumbnail_variant(self,domain,limit,order,pricelist):
        thumbnail = []
        flush_type = 'thumbnail_variant'
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
                    view_type='variant',
                    render_time='%s' % (timer() - render_start),
                ).encode('utf-8')
                # ~ _logger.warn('get_thumbnail_default_variant --------> %s' % (page))
                self.env['website'].put_page_dict(key,flush_type,page)
                page_dict['page'] = base64.b64encode(page)
            thumbnail.append(page_dict.get('page','').decode('base64'))
        return thumbnail

    @api.model
    def get_packaging_info(self,packaging):
        # ~ prod_packs = request.env['product.product'].sudo().search_read([('id', 'in', [p['id'] for p in products])], ['packaging_ids'], order=current_order)
        # ~ packagings = request.env['product.packaging'].sudo().search_read([('id', 'in', sum([p['packaging_ids'] for p in prod_packs], []))], ['ul', 'name', 'ean', 'qty', 'ul_container', 'ul_qty', 'rows'])
        # ~ for ul in request.env['product.ul'].sudo().search_read(
            # ~ [('id', 'in', [p['ul_container'][0] for p in packagings if p['ul_container']] + [p['ul'][0] for p in packagings if p['ul']])],
            # ~ ['width', 'length', 'height', 'name']):
            # ~ for p in packagings:
                # ~ if type(p['ul']) == tuple and p['ul'][0] == ul['id']:
                    # ~ p['ul'] = ul
                # ~ if type(p['ul_container']) == tuple and p['ul_container'][0] == ul['id']:
                    # ~ p['ul_container'] = ul
        # ~ packagings = {d['id']: d for d in packagings}
        
        return u"""<div class="dn-tooltip text-centered"><i class="fa fa-cube"></i>
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
                            ul_name=packaging['ul']['name'],
                            qty="""<b>%s</b> %s %s<br/>""" % (_('Quantity:') ,packaging['qty'],_('pcs / box')) if packaging['qty'] else '',
                            ean="""<b>%s</b> %s %s<br/>""" % (_('EAN:') ,packaging['ean'],_('pcs / box')) if packaging['ean'] else '',
                            width="""<b>%s</b> %s mm<br/>""" % (_('Width:') ,packaging['width']) if packaging['width'] else '',
                            length="""<b>%s</b> %s mm<br/>""" % (_('Length:') ,packaging['length']) if packaging['length'] else '',
                            height="""<b>%s</b> %s mm<br/>""" % (_('Height:') ,packaging['height']) if packaging['height'] else '',
                            ul_container_name="""<b>%s<br/>""" % packaging['ul_container']['name'] if packaging['ul_container'] else '',
                            ul_qty="""<b>Quantity (DFP):</b> %s %s<br/>""" % (_('Quantity (DFP):') ,packaging['ul_qty'] * packaging['rows'],_('boxes / pallet')) if packaging['ul_container'] else '',
                            kfp="""<b>Quantity (KFP):</b> <t %s %s<br/>""" % (_('Quantity (KFP):') ,packaging['qty'] * packaging['ul_qty'] * packaging['rows'],_('pcs / pallet')) if packaging['ul_container'] else '',
                        )
    @api.model
    def get_stock_info(self,type,variant_available_days):
        if type != 'product' or product['virtual_available_days'] > 5:
            state = 'in'
        elif product['virtual_available_days'] >= 1.0:
            state = 'few'
        else:
            state ='short'
        return {'in': _('In stock'),'few': _('Few in stock'),'short': _('Shortage')}[state]
                    
    
    @api.model
    def get_list_row(self,domain,limit,order,pricelist):
        rows = []
        flush_type = 'product_list_row'
        # ~ _logger.warn('get_thumbnail_default_variant ------> %s %s %s %s' % (domain,limit,order,pricelist))
        # ~ products = request.env['product.template'].with_context(pricelist=pricelist.id).search_read(domain, fields=['id', 'name', 'use_tmpl_name', 'default_code', 'access_group_ids', 'dv_ribbon', 'is_offer_product_reseller', 'is_offer_product_consumer', 'dv_id', 'dv_image_src', 'dv_name', 'dv_default_code', 'dv_price_45', 'dv_price_20', 'dv_price_en', 'dv_price_eu', 'dv_recommended_price', 'dv_recommended_price_en', 'dv_recommended_price_eu', 'website_style_ids_variant', 'dv_description_sale'], limit=PPG, order=current_order)
        for product in self.env['product.template'].search_read(domain, fields=['id','name', 'use_tmpl_name','dv_ribbon','dv_id' ,       'default_code','virtual_available_days','type', 'packaging_ids',                'is_offer_product_reseller', 'is_offer_product_consumer', 'website_style_ids_variant', 'product_tmpl_id', 'sale_ok'], limit=limit, order=order):
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
                campaign = request.env['crm.tracking.campaign'].browse(product['campaign_ids'][0])
                page = """<tr class="tr_lst ">
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
                                                <a href="/sv_SE/dn_shop/variant/{product_id}" title="{product_name}">
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
                                    <div>
                                        <form action="/shop/cart/update" class="oe_dn_list" data-attribute_value_ids="{product_id}" method="POST">
                                            <div class="product_shop" style="margin: 0px;">
                                                <input class="product_id" name="product_id" value="{product_id}" type="hidden">
                                                <input name="return_url" value="{return_url}" type="hidden">
                                                <div class="css_quantity input-group oe_website_spinner">
                                                    <span class="input-group-addon">
                                                        <a href="#" class="mb8 js_add_cart_json">
                                                            <i class="fa fa-minus"></i>
                                                        </a>
                                                    </span>
                                                    <input class="js_quantity form-control" data-min="1" name="add_qty" value="1" type="text">
                                                    <span class="input-group-addon">
                                                        <a href="#" class="mb8 float_left js_add_cart_json">
                                                            <i class="fa fa-plus"></i>
                                                        </a>
                                                    </span>
                                                </div>
                                                <a id="add_to_cart" class="btn btn-default dn_list_add_to_cart" href="javascript:void(0);">
                                                    <i class="fa fa-shopping-cart" style="color: #CB683F;"></i>
                                                </a>
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
                    product_dfp=self.get_packaging_info(product['packaging_ids']) or '',
                    product_stock=self.get_stock_info(product['type'],product['virtual_available_days']),
                    product_name=product['name'],
                    product_price=self.env['product.product'].get_html_price_short(product['id'], pricelist),
                    product_ribbon_offer  = '<div class="ribbon ribbon_offer   btn btn-primary">%s</div>' % _('Offer') if (product['is_offer_product_reseller'] and pricelist.for_reseller == True) or (product['is_offer_product_consumer'] and  pricelist.for_reseller == False) else '',
                    product_ribbon_promo  = '<div class="ribbon ribbon_news    btn btn-primary">' + _('New') + '</div>' if ribbon_promo.html_class in product['dv_ribbon'] else '',
                    product_ribbon_limited= '<div class="ribbon ribbon_limited btn btn-primary">' + _('Limited<br/>Edition') + '</div>' if ribbon_limited.html_class in product['dv_ribbon'] else '',
                    key_raw=key_raw,
                    key=key,
                    render_time='%s' % (timer() - render_start),
                ).encode('utf-8')
                self.env['website'].put_page_dict(key,flush_type,page)
                page_dict['page'] = base64.b64encode(page)
            rows.append(page_dict.get('page','').decode('base64'))
        return rows

    @api.model
    def product_detail_desc(self,product):
        thumbnail = []
        flush_type = 'product_detail_desc'
        # ~ _logger.warn('get_thumbnail_default_variant ------> %s %s %s %s' % (domain,limit,order,pricelist))
        # ~ products = request.env['product.template'].with_context(pricelist=pricelist.id).search_read(domain, fields=['id', 'name', 'use_tmpl_name', 'default_code', 'access_group_ids', 'dv_ribbon', 'is_offer_product_reseller', 'is_offer_product_consumer', 'dv_id', 'dv_image_src', 'dv_name', 'dv_default_code', 'dv_price_45', 'dv_price_20', 'dv_price_en', 'dv_price_eu', 'dv_recommended_price', 'dv_recommended_price_en', 'dv_recommended_price_eu', 'website_style_ids_variant', 'dv_description_sale'], limit=PPG, order=current_order)
        key_raw = 'dn_shop %s %s %s %s %s %s' % (self.env.cr.dbname,flush_type,product.id,pricelist.id,self.env.lang,request.session.get('device_type','md'))  # db flush_type produkt prislista språk
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

            page = u"""<div>
            <p class="text-muted hidden" data-oe-model="product.template" data-oe-id="3900" data-oe-field="description_sale" data-oe-type="text" data-oe-expression="product.description_sale" data-oe-translate="1"></p>
            
<p class="text-muted">
  
    
  
</p>
<p class="text-muted public_desc" data-oe-id="5922" data-oe-source-id="5442" data-oe-xpath="/data/xpath[7]/p[2]" data-oe-model="ir.ui.view" data-oe-field="arch">Body Lotion Energy är en uppmjukande och välgörande lotion med en uppiggande doft som passar både honom och henne.<br><br>Kombinationen av växtoljor, vitaminer och Mjölksyra (AHA) hjälper huden att hålla en bra fukt- och fettbalans. Vi använder Mjölksyra från sockerbetor och Sheasmör från vildväxande sheaträd.<br><br>Eteriska oljor av Rosmarin, Lavendel, Citrongräs och Enbär adderar både uppfriskande doft och andra välgörande egenskaper. Rosmarin verkar uppfriskande. Lavendel är milt och lugnande. Citrongräs stärker bindväven och verkar uppiggande. Enbär är utrensande och stärkande.<br><br>Självkonserverande system.</p>
            <h4 class="show_more_facet text-center hidden-lg hidden-md hidden-sm" style="text-decoration: underline;" data-oe-id="5922" data-oe-source-id="5442" data-oe-xpath="/data/xpath[7]/h4[1]" data-oe-model="ir.ui.view" data-oe-field="arch">
                Mer information
                <i class="fa fa-angle-down"></i>
            </h4>
            <div class="container facet_container hidden-xs">
                <div class="col-md-12 no_padding_div">
                    <h2 class="use_desc_title dn_uppercase" data-oe-source-id="5442" data-oe-id="5922" data-oe-model="ir.ui.view" data-oe-field="arch" data-oe-xpath="/data/xpath[7]/div/div[1]/h2[1]">Användning</h2>
                    <p class="text-muted use_desc" data-oe-source-id="5442" data-oe-id="5922" data-oe-model="ir.ui.view" data-oe-field="arch" data-oe-xpath="/data/xpath[7]/div/div[1]/p[1]">Använd gärna Body Lotion Energy varje dag, speciellt under vintern eller efter solbad. Kombinera gärna med Body &amp; Massage Oil Energy, för bästa resultat.</p>
                    
                </div>
                <div class="col-md-12 no_padding_div">
                    <h2 class="category_title dn_uppercase" data-oe-source-id="5442" data-oe-id="5922" data-oe-model="ir.ui.view" data-oe-field="arch" data-oe-xpath="/data/xpath[7]/div/div[2]/h2[1]">Kategorier</h2>
                    
                        <a href="/sv_SE/dn_shop/category/9" data-oe-source-id="5442" data-oe-id="5922" data-oe-model="ir.ui.view" data-oe-field="arch" data-oe-xpath="/data/xpath[7]/div/div[2]/t[1]/a[1]">
                            <span style="color: #bbb;" data-oe-model="product.public.category" data-oe-id="9" data-oe-field="name" data-oe-type="char" data-oe-expression="pc.name" data-oe-translate="1">Kropp</span>
                        </a>
                    
                </div>
                <div class="col-md-12 facet_div"><div class="col-md-6"><h2 class="dn_uppercase">Formula</h2><a href="/dn_shop/?facet_6_67=67&amp;category_9=9" class="text-muted"><span>Creme</span></a></div><div class="col-md-6"><h2 class="dn_uppercase">Produkttyp</h2><a href="/dn_shop/?facet_8_78=78&amp;category_9=9" class="text-muted"><span>Creme</span></a><span>, </span><a href="/dn_shop/?facet_8_164=164&amp;category_9=9" class="text-muted"><span>Massage</span></a></div><div class="col-md-6"><h2 class="dn_uppercase">Hudtillstånd</h2><a href="/dn_shop/?facet_7_61=61&amp;category_9=9" class="text-muted"><span>Normal</span></a><span>, </span><a href="/dn_shop/?facet_7_63=63&amp;category_9=9" class="text-muted"><span>Torr</span></a></div><div class="col-md-6"><h2 class="dn_uppercase">Egenskaper</h2><a href="/dn_shop/?facet_5_74=74&amp;category_9=9" class="text-muted"><span>Återfuktande</span></a><span>, </span><a href="/dn_shop/?facet_5_75=75&amp;category_9=9" class="text-muted"><span>Mjukgörande</span></a><span>, </span><a href="/dn_shop/?facet_5_98=98&amp;category_9=9" class="text-muted"><span>Skyddande</span></a><span>, </span><a href="/dn_shop/?facet_5_103=103&amp;category_9=9" class="text-muted"><span>Veganvänlig</span></a><span>, </span><a href="/dn_shop/?facet_5_197=197&amp;category_9=9" class="text-muted"><span>Energigivande</span></a></div></div>
            </div>
            <h4 class="hide_more_facet text-center hidden-lg hidden-md hidden-sm hidden" style="text-decoration: underline;" data-oe-id="5922" data-oe-source-id="5442" data-oe-xpath="/data/xpath[7]/h4[2]" data-oe-model="ir.ui.view" data-oe-field="arch">
                Mindre info
                <i class="fa fa-angle-up"></i>
            </h4>
        </div>""".format(public_descr='',category='',formula='').encode('utf-8')
            # ~ _logger.warn('get_thumbnail_default_variant --------> %s' % (page))
            self.env['website'].put_page_dict(key,flush_type,page)
            page_dict['page'] = base64.b64encode(page)
        return page_dict.get('page','').decode('base64')

    @api.model
    def product_detail_image(self,product):
        thumbnail = []
        flush_type = 'product_detail_image'
        # ~ _logger.warn('get_thumbnail_default_variant ------> %s %s %s %s' % (domain,limit,order,pricelist))
        # ~ products = request.env['product.template'].with_context(pricelist=pricelist.id).search_read(domain, fields=['id', 'name', 'use_tmpl_name', 'default_code', 'access_group_ids', 'dv_ribbon', 'is_offer_product_reseller', 'is_offer_product_consumer', 'dv_id', 'dv_image_src', 'dv_name', 'dv_default_code', 'dv_price_45', 'dv_price_20', 'dv_price_en', 'dv_price_eu', 'dv_recommended_price', 'dv_recommended_price_en', 'dv_recommended_price_eu', 'website_style_ids_variant', 'dv_description_sale'], limit=PPG, order=current_order)
        key_raw = 'dn_shop %s %s %s %s %s %s' % (self.env.cr.dbname,flush_type,product.id,pricelist.id,self.env.lang,request.session.get('device_type','md'))  # db flush_type produkt prislista språk
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

            page = """<div class="col-sm-7 col-md-7 col-lg-7">
                    <div class="image_zoom" data-oe-source-id="5442" data-oe-id="5894" data-oe-model="ir.ui.view" data-oe-field="arch" data-oe-xpath="/data/xpath/div/div[1]"></div>
                    <div id="image_big" class="tab-content"><div id="104531" class="tab-pane fade active in"><img class="img img-responsive product_detail_img" style="margin: auto;" src="/imagefield/ir.attachment/datas/104531/ref/website_sale_product_gallery.img_product_detail"></div></div>
                    <ul id="image_nav" class="nav nav-pills"><li class="active "><a data-toggle="tab" href="#104531"><img class="img img-responsive" src="/imagefield/ir.attachment/datas/104531/ref/website_sale_product_gallery.img_product_thumbnail"></a></li></ul>
                <div id="ingredients_div"><div class="container mb16 hidden-xs"><h2 class="mt64 mb32 text-center dn_uppercase">made from all-natural ingredients</h2><a href="/dn_shop/?current_ingredient=61"><div class="col-md-3 col-sm-3 ingredient_desc" style="padding: 0px;"><img class="img img-responsive" style="margin: auto;" src="/imagefield/product.ingredient/image/61/ref/product_ingredients.img_ingredients"><h6 class="text-center" style="padding: 0px; margin-top: 0px;"><i>Lemongrass</i></h6></div></a><i><a href="/dn_shop/?current_ingredient=32"><div class="col-md-3 col-sm-3 ingredient_desc" style="padding: 0px;"><img class="img img-responsive" style="margin: auto;" src="/imagefield/product.ingredient/image/32/ref/product_ingredients.img_ingredients"><h6 class="text-center" style="padding: 0px; margin-top: 0px;"><i>Juniper</i></h6></div></a><i><a href="/dn_shop/?current_ingredient=12"><div class="col-md-3 col-sm-3 ingredient_desc" style="padding: 0px;"><img class="img img-responsive" style="margin: auto;" src="/imagefield/product.ingredient/image/12/ref/product_ingredients.img_ingredients"><h6 class="text-center" style="padding: 0px; margin-top: 0px;"><i>Lavender</i></h6></div></a><i><a href="/dn_shop/?current_ingredient=62"><div class="col-md-3 col-sm-3 ingredient_desc" style="padding: 0px;"><img class="img img-responsive" style="margin: auto;" src="/imagefield/product.ingredient/image/62/ref/product_ingredients.img_ingredients"><h6 class="text-center" style="padding: 0px; margin-top: 0px;"><i>Rosemary</i></h6></div></a></i></i></i></div></div>
            <p id="current_product_id" data-value="3900" class="hidden" data-oe-id="6100" data-oe-source-id="5442" data-oe-xpath="/data/xpath[2]/p" data-oe-model="ir.ui.view" data-oe-field="arch"></p>
            <div id="ingredients_description" class="container hidden-xs">
                <div class="mt16">
                    
                        <p data-oe-source-id="5442" data-oe-id="6100" data-oe-model="ir.ui.view" data-oe-field="arch" data-oe-xpath="/data/xpath[2]/div[2]/div[1]/t[1]/p[1]"><strong class="dn_uppercase">ingredients: </strong><span class="text-muted" data-oe-model="product.product" data-oe-id="3900" data-oe-field="ingredients" data-oe-type="text" data-oe-expression="product_product.ingredients" data-oe-translate="1">Aqua Purificata/Water, Simondsia Chinensis (Jojoba) Seed Oil, Caprylic/Capric Triglyceride, Squalane (Vegetable), Glycerin (Vegetable), Butyrospermum Parkii (Shea) Butter, Glyceryl Stearate Citrate, Cetearyl Alcohol, Glyceryl Caprylate,  Sodium Levulinate, Sodium Anisate, Sodium Lactate, Lactic Acid, Xanthan Gum, Rosmarinus Officinalis (Rosemary) Leaf Oil, Cymbopogon Citratus (Lemongrass) Oil, Juniperus Communis (Juniper) Oil, Lavandula Angustifolia (Lavender) Oil, Helianthus Annuus (Sunflower) Seed Oli, Rosmarinus Officinalis (Rosemary) Leaf Extract, Limonene*, Linalool*, Geraniol*, Citronellol*, Citral*. *Components naturally present in essential oils.</span></p>
                    
                </div>
            </div>
        </div>""".format(public_descr='',category='',formula='',).encode('utf-8')
            # ~ _logger.warn('get_thumbnail_default_variant --------> %s' % (page))
            self.env['website'].put_page_dict(key,flush_type,page)
            page_dict['page'] = base64.b64encode(page)
        return page_dict.get('page','').decode('base64')


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
        memcached.mc_save(key, page_dict,60*60*24*7)  # One week

