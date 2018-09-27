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
                        <div class="product_price">
                            <b class="text-muted">
                            <h5>{price_from}</h5>
                                <h4>
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
        for key in memcached.get_keys(path=[('%s,%s' % (p._model, p.id)) for p in self]):
            memcached.mc_delete(key)

    @api.multi
    @api.depends('name', 'list_price', 'taxes_id', 'default_code', 'description_sale', 'image', 'image_attachment_ids', 'image_attachment_ids.sequence', 'product_variant_ids.image_attachment_ids', 'product_variant_ids.image_medium', 'product_variant_ids.image_attachment_ids.sequence', 'website_style_ids', 'attribute_line_ids.value_ids')
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
                # ~ p.dv_image_src = '/imagefield/ir.attachment/datas/%s/ref/%s' %(variant['image_main_id'][0], 'snippet_dermanord.img_product') if variant['image_main_id'] else placeholder
                p.dv_image_src = self.env['website'].imagefield_hash('ir.attachment', 'datas', variant['image_main_id'][0], 'snippet_dermanord.img_product')
                p.dv_ribbon = website_style_ids_variant if website_style_ids_variant else ' '.join([c for c in p.website_style_ids.mapped('html_class') if c])
            except:
                e = sys.exc_info()
                tb = ''.join(traceback.format_exception(e[0], e[1], e[2]))
                _logger.error(tb)
                self.env['mail.message'].create({
                    'body': tb.replace('\n', '<br/>'),
                    'subject': 'Default variant recompute failed on %s' % p.name,
                    'author_id': self.env.ref('base.partner_root').id,
                    'res_id': p.id,
                    'model': p._name,
                    'type': 'notification',
                    'partner_ids': [(4, pid) for pid in p.message_follower_ids.mapped('id')],
                })
                p.dv_default_code = '%s' % 'error'
                p.dv_description_sale = u'%s' % e[1]
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
    def get_thumbnail_default_variant(self,domain,pricelist,limit=21,order='',offset=1):
        if isinstance(pricelist,int):
            pricelist = self.env['product.pricelist'].browse(pricelist)
        # ~ _logger.warn('get_thumbnail_default_variant --------> %s' % ('Start'))
        # ~ _logger.warn('get_thumbnail_default_variant --------> %s' % self.env['product.template'].search_read(domain, fields=['id','name', 'dv_ribbon' ,'is_offer_product_reseller', 'is_offer_product_consumer','dv_image_src',], limit=limit, order=order,offset=offset))
        thumbnail = []
        flush_type = 'thumbnail_product'
        ribbon_promo = None
        ribbon_limited = None
        for product in self.env['product.template'].search_read(domain, fields=['name', 'dv_ribbon','is_offer_product_reseller', 'is_offer_product_consumer','dv_image_src',], limit=limit, order=order,offset=offset):
            # ~ _logger.warn('get_thumbnail_default_variant --------> %s' % (product))
            key_raw = 'dn_shop %s %s %s %s %s %s %s %s' % (
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
                    price_from=_('Price From'),
                ).encode('utf-8')
                # ~ _logger.warn('get_thumbnail_default_variant --------> %s' % (page))
                self.env['website'].put_page_dict(key, flush_type, page, 'product.template,%s' % product['id'])
                page_dict['page'] = base64.b64encode(page)
            thumbnail.append(page_dict.get('page', '').decode('base64'))
        return thumbnail

class product_product(models.Model):
    _inherit = 'product.product'

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
                    price_from=_('Price From'),
                ).encode('utf-8')
                _logger.warn('get_thumbnail_default_variant --------> %s' % (page))
                self.env['website'].put_page_dict(key, flush_type, page, 'product.template,%s' % product['id'])
                page_dict['page'] = base64.b64encode(page)
            thumbnail.append(page_dict.get('page', '').decode('base64'))
            _logger.warn('get_thumbnail_default_variant (thiumnails)--------> %s' % (thumbnail))
        return thumbnail

    @api.model
    def get_packaging_info(self, product_id):
        product = self.env['product.product'].sudo().search_read([('id','=',product_id)],['packaging_ids'])[0]
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
    def get_stock_info(self,product_id):
        product = self.env['product.product'].sudo().search_read([('id','=',product_id)],['virtual_available_days','type'])[0]
        if product['type'] != 'product' or product['virtual_available_days'] > 5:
            state = 'in'
        elif product['virtual_available_days'] >= 1.0:
            state = 'few'
        else:
            state ='short'
        return (state in ['in','few'],state,{'in': _('In stock'),'few': _('Few in stock'),'short': _('Shortage')}[state].encode('utf-8'))  # in_stock,state,info

    @api.model
    def get_list_row(self,domain,pricelist,limit=21,order='',offset=0):
        if isinstance(pricelist,int):
            pricelist = self.env['product.pricelist'].browse(pricelist)
        rows = []
        flush_type = 'product_list_row'
        ribbon_promo = None
        ribbon_limited = None
        for product in self.env['product.product'].search_read(domain, fields=['id','fullname', 'default_code','type', 'is_offer_product_reseller', 'is_offer_product_consumer', 'product_tmpl_id', 'sale_ok','campaign_ids','website_style_ids_variant'], limit=limit, order=order,offset=offset):
            key_raw = 'dn_shop %s %s %s %s %s %s' % (self.env.cr.dbname,flush_type,product['id'],pricelist.id,self.env.lang,request.session.get('device_type','md'))  # db flush_type produkt prislista språk
            key,page_dict = self.env['website'].get_page_dict(key_raw)
            # ~ _logger.warn('get_thumbnail_default_variant --------> %s %s' % (key,page_dict))
            if not page_dict:
                render_start = timer()
                if not ribbon_limited:
                    ribbon_limited = request.env.ref('webshop_dermanord.image_limited')
                    ribbon_promo   = request.env.ref('website_sale.image_promo')
                campaign = self.env['crm.tracking.campaign'].browse(product['campaign_ids'][0] if product['campaign_ids'] else 0)
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
                                    <div class="{shop_widget}">
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
                    product_dfp=self.get_packaging_info(product['id']) or '',
                    shop_widget='{shop_widget}',
                    product_stock='{product_stock}',
                    product_name=product['fullname'],
                    product_price=self.env['product.product'].get_html_price_short(product['id'], pricelist),
                    product_ribbon_offer  = '<div class="ribbon ribbon_offer   btn btn-primary">%s</div>' % _('Offer') if (product['is_offer_product_reseller'] and pricelist.for_reseller == True) or (product['is_offer_product_consumer'] and  pricelist.for_reseller == False) else '',
                    product_ribbon_promo  = '<div class="ribbon ribbon_news    btn btn-primary">' + _('New') + '</div>' if ribbon_promo.id in product['website_style_ids_variant'] else '',
                    product_ribbon_limited= '<div class="ribbon ribbon_limited btn btn-primary">' + _('Limited<br/>Edition') + '</div>' if ribbon_limited.id in product['website_style_ids_variant'] else '',
                    key_raw=key_raw,
                    key=key,
                    render_time='%s' % (timer() - render_start),
                ).encode('utf-8')
                self.env['website'].put_page_dict(key, flush_type, page, 'product.product,%s' % product['id'])
                page_dict['page'] = base64.b64encode(page)
            stock_info = self.get_stock_info(product['id'])
            rows.append(page_dict.get('page', '').decode('base64').format(shop_widget='' if stock_info[0] else 'hidden', product_stock=stock_info[2]))
        return rows

    # Product detail view with all variants
    @api.model
    def get_product_detail(self, product, variant_id):

        # right side product.description, directly after stock_status
        def html_product_detail_desc( product, partner, pricelist):
            is_reseller = False
            if pricelist and pricelist.for_reseller:
                is_reseller = True
            category_html = ''
            category_value = ''
            for c in product.public_categ_ids:
                category_html += '<a href="/dn_shop/category/%s"><span style="color: #bbb;">%s</span></a>' %(c.id, c.name)
                category_value += '&amp;category_%s=%s' %(c.id, c.id)
            facet_html = ''
            for line in product.facet_line_ids:
                facet_html += '<div class="col-md-6"><h2 class="dn_uppercase">%s</h2>' %line.facet_id.name
                for idx, value in enumerate(line.value_ids):
                    facet_html += '<a href="/dn_shop/?facet_%s_%s=%s%s" class="text-muted"><span>%s</span></a>' %(line.facet_id.id, value.id, value.id, category_value, value.name)
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
                public_desc = '<p class="text-muted public_desc%s">%s</p>' %(' hidden' if not product.public_desc else '', product.public_desc if product.public_desc else ''),
                more_info = _('More info'),
                use_desc_title = '<h2 class="use_desc_title dn_uppercase%s">%s</h2>' %(' hidden' if not product.use_desc else '', _('Directions')),
                use_desc = '<p class="text-muted use_desc%s">%s</p>' %(' hidden' if not product.use_desc else '', product.use_desc if product.use_desc else ''),
                reseller_desc_title = '<h2 class="reseller_desc_title dn_uppercase%s">%s</h2>' %(' hidden' if not product.reseller_desc or not is_reseller else '', _('For Resellers')),
                reseller_desc = '<p class="text-muted reseller_desc%s">%s</p>' %(' hidden' if not product.reseller_desc or not is_reseller else '', product.reseller_desc if not product.reseller_desc or not is_reseller else ''),
                category_title = _('Categories'),
                category_html = category_html,
                facet_html = facet_html,
                less_info = _('Less info')
            )
            return page

        # left side product image with image nav bar, product ingredients with nav bar
        def html_product_detail_image( product, partner):
            ribbon_limited = self.env.ref('webshop_dermanord.image_limited')
            ribbon_promo = self.env.ref('website_sale.image_promo')
            ribbon_wrapper = ''
            if len(product.website_style_ids_variant) > 0:
                if product.website_style_ids_variant[0] == ribbon_promo:
                    ribbon_wrapper = '<div class="ribbon-wrapper"><div class="ribbon_news btn btn-primary">%s</div></div>' %_('News')
                elif product.website_style_ids_variant[0] == ribbon_limited:
                    ribbon_wrapper = '<div class="ribbon-wrapper"><div class="ribbon_news btn btn-primary">%s</div></div>' %_('Limited Edition')
            elif len(product.product_tmpl_id.website_style_ids) > 0:
                if product.product_tmpl_id.website_style_ids[0] == ribbon_promo:
                    ribbon_wrapper = '<div class="ribbon-wrapper"><div class="ribbon_news btn btn-primary">%s</div></div>' %_('News')
                elif product.product_tmpl_id.website_style_ids[0] == ribbon_limited:
                    ribbon_wrapper = '<div class="ribbon-wrapper"><div class="ribbon_news btn btn-primary">%s</div></div>' %_('Limited Edition')
            offer_wrapper = '<div class="offer-wrapper"><div class="ribbon ribbon_offer btn btn-primary">%s</div></div>' %_('Offer') if product.is_offer_product_reseller or product.is_offer_product_consumer else ''
            product_images = product.sudo().image_attachment_ids.sorted(key=lambda a: a.sequence)
            product_images_html = ''
            product_images_nav_html = ''
            if len(product_images) > 0:
                for idx, image in enumerate(product_images):
                    product_images_html += '<div id="%s" class="tab-pane fade%s">%s%s<img class="img img-responsive product_detail_img" style="margin: auto;" src="%s"/></div>' %(image.id, ' active in' if idx == 0 else '', offer_wrapper, ribbon_wrapper, self.env['website'].imagefield_hash('ir.attachment', 'datas', image[0].id, 'website_sale_product_gallery.img_product_detail'))
                    product_images_nav_html += '<li class="%s"><a data-toggle="tab" href="#%s"><img class="img img-responsive" src="%s"/></a></li>' %('active' if idx == 0 else '', image.id, self.env['website'].imagefield_hash('ir.attachment', 'datas', image[0].id, 'website_sale_product_gallery.img_product_thumbnail'))
            else:
                product_images_nav_html = '<li class="active"><a data-toggle="tab" href="#%s"><img class="img img-responsive" src="/web/static/src/img/placeholder.png"/></a></li>' %'0'
            ingredients_images_nav_html = ''
            product_ingredients = self.env['product.ingredient'].search([('product_ids', 'in', product.id)], order='sequence')
            if len(product_ingredients) > 0:
                for i in product_ingredients:
                    ingredients_images_nav_html += '<a href="/dn_shop/?current_ingredient=%s"><div class="col-md-3 col-sm-3 ingredient_desc" style="padding: 0px;"><img class="img img-responsive" style="margin: auto;" src="%s"/><h6 class="text-center" style="padding: 0px; margin-top: 0px;"><i>%s</i></h6></div></a>' %(i.id, self.env['website'].imagefield_hash('product.ingredient', 'image', i.id, 'product_ingredients.img_ingredients'), i.name)
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
<div id="ingredients_description {hide_ingredients_desc}" class="container hidden-xs">
    <div class="mt16">
        <p>
            <strong class="dn_uppercase">{ingredients} </strong>
            <span class="text-muted">
                {ingredients_desc}
            </span>
        </p>
    </div>
</div>""".format(
                product_images_html = product_images_html,
                product_images_nav_html = product_images_nav_html,
                ingredients_title = _('made from all-natural ingredients'),
                ingredients_images_nav_html = ingredients_images_nav_html,
                current_product_id = product.id,
                hide_ingredients_desc = '' if product.ingredients else 'hidden',
                ingredients = _('ingredients:'),
                ingredients_desc = product.ingredients if product.ingredients else ''
            )
            return page

        # product ingredients in mobile, directly after <section id="product_detail"></section>
        def html_product_ingredients_mobile(product, partner):
            ingredients_carousel_html = ''
            ingredients_carousel_nav_html = ''
            product_ingredients = self.env['product.ingredient'].search([('product_ids', 'in', product.id)], order='sequence')
            if len(product_ingredients) > 0:
                for idx, i in enumerate(product_ingredients):
                    ingredients_carousel_html += '<div class="item ingredient_desc%s"><a href="/dn_shop/?current_ingredient=%s"><img class="img img-responsive" style="margin: auto; display: block;" src="%s"/><h6 class="text-center" style="padding: 0px; margin-top: 0px;"><i>%s</i></h6></a></div>' %(' active' if idx == 0 else '', i.id, self.env['website'].imagefield_hash('product.ingredient', 'image', i.id, 'product_ingredients.img_ingredients'), i.name)
                    ingredients_carousel_nav_html += '<li class="%s" data-slide-to="%s" data-target="#ingredient_carousel"></li>' %(' active' if idx == 0 else '', idx)

            page = u"""<div id="ingredients_div_mobile">
    <div class="container mb16 hidden-lg hidden-md hidden-sm">
        <h4 class="text-center dn_uppercase">{ingredients_title}</h4>
        <div class="col-md-12">
            <div class="carousel slide" id="ingredient_carousel" data-ride="carousel">
                <div class="carousel-inner" style="width: 100%;">
                    {ingredients_carousel_html}
                </div>
                <div class="carousel-control left" data-slide="prev" data-target="#ingredient_carousel" href="#ingredient_carousel" style="width: 10%; left: 0px;"><i class="fa fa-chevron-left" style="right: 20%; color: #000;"></i></div>
                <div class="carousel-control right" data-slide="next" data-target="#ingredient_carousel" href="#ingredient_carousel" style="width: 10%; right: 0px;"><i class="fa fa-chevron-right" style="left: 20%; color: #000;"></i></div>
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
                ingredients_title = _('made from all-natural ingredients'),
                ingredients_carousel_html = ingredients_carousel_html,
                ingredients_carousel_nav_html = ingredients_carousel_nav_html,
                ingredients = _('ingredients:'),
                ingredients_desc = product.ingredients
            )
            return page

        partner = self.env.user.partner_id.commercial_partner_id
        pricelist = partner.property_product_pricelist
        flush_type = 'get_product_detail'
        key_raw = 'dn_shop %s %s %s %s %s %s %s %s' % (
            self.env.cr.dbname, flush_type, variant_id, pricelist.id, self.env.lang,
            request.session.get('device_type', 'md'),
            self.env.user in self.sudo().env.ref('base.group_website_publisher').users,
            ','.join([str(id) for id in sorted(self.env.user.commercial_partner_id.access_group_ids._ids)]))
        key, page_dict = self.env['website'].get_page_dict(key_raw)
        if not page_dict:
            render_start_tot = timer()
            page = ''
            attr_sel = ''
            if len(product.attribute_line_ids) > 0:
                attr_sel = '<select class="form-control js_variant_change attr_sel" name="attribute-%s-1">' %product.id
                for v in product.product_variant_ids:
                    attr_sel += '<option class="css_not_available" value="%s"%s>%s</option>' %(v.attribute_value_ids[0].id, ' selected="selected"' if v.id == variant_id else '', v.attribute_value_ids[0].name)
                attr_sel += '</select>'
            visible_attrs = set(l.attribute_id.id for l in product.attribute_line_ids if len(l.value_ids) > 1)
            decimal_precision = pricelist.currency_id.rounding
            for variant in product.product_variant_ids:
                render_start = timer()
                pricelist_line = variant.get_pricelist_chart_line(pricelist)
                campaign = variant.campaign_ids[0] if variant.campaign_ids else None
                page += u"""<section id="{attribute_value}" class="product_detail container mt8 oe_website_sale discount {hide_variant}">
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
    <div class="row">
        <div class="col-sm-7 col-md-7 col-lg-7">
            {html_product_detail_image}
        </div>
        <div class="col-sm-5 col-md-5 col-lg-4 col-lg-offset-1">
            <h1 itemprop="name">{product_name}</h1><h4 class="text-muted default_code">{default_code}</h4>
            <form action="/shop/cart/update" class="js_add_cart_variants" data-attribute_value_ids="{variant_ids}" method="POST">
                <div class="js_product">
                    <input class="product_id" name="product_id" value="{variant_id}" type="hidden">
                    <ul class="list-unstyled js_add_cart_variants nav-stacked" data-attribute_value_ids="{data_attribute_value_ids}">
                        <li>
                            <strong style="font-family: futura-pt-light, sans-serif; font-size: 18px;">{attributes}</strong>
                            {attr_sel}
                        </li>
                    </ul>
                    <div itemprop="offers" itemscope="itemscope" class="product_price mt16 mb16">
                        <p class="oe_price_h4 css_editable_mode_hidden decimal_precision" data-precision="{decimal_precision}">
                            {product_price}
                        </p>
                    </div>
                    <div class="css_quantity input-group oe_website_spinner {hide_add_to_cart}">
                        <span class="input-group-addon">
                            <a href="#" class="mb8 js_add_cart_json">
                                <i class="fa fa-minus"></i>
                            </a>
                        </span>
                        <input class="js_quantity form-control" data-min="1" name="add_qty" value="1" type="text"/>
                        <span class="input-group-addon">
                            <a href="#" class="mb8 float_left js_add_cart_json">
                                <i class="fa fa-plus"></i>
                            </a>
                        </span>
                    </div>
                    <a id="add_to_cart" href="#" class="dn_btn dn_primary mt8 js_check_product a-submit text-center {hide_add_to_cart}" groups="base.group_user,base.group_portal" disable="1">{add_to_cart}</a>
                    <!-- <input id="sale_ok" name="sale_ok" type="hidden" t-att-value="product.sale_ok" /> -->
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
<!-- key {key} key_raw {key_raw} render_time {render_time} -->
<!-- http:/mcpage/{key} http:/mcpage/{key}/delete  http:/mcmeta/{key} -->""".format(
                    attribute_value = variant.attribute_value_ids[0].id if len(product.attribute_line_ids) > 0 else '',
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
                    default_code = variant.default_code,
                    variant_ids = product.product_variant_ids.mapped('id'),
                    attributes = product.attribute_line_ids[0].attribute_id.name if len(product.attribute_line_ids) > 0 else '',
                    data_attribute_value_ids = [[p.id, [v.id for v in p.attribute_value_ids if v.attribute_id.id in visible_attrs], pricelist_line.price, pricelist_line.rec_price, '{%s_in_stock}' % p.id] for p in product.product_variant_ids],
                    attr_sel = attr_sel,
                    decimal_precision = decimal_precision,
                    product_price = variant.get_html_price_long(pricelist),
                    hide_add_to_cart = '{%s_hide_add_to_cart}' % variant.id,
                    add_to_cart = _('Add to cart'),
                    product_startdate = _('Available on %s') %campaign.date_start if campaign and campaign.date_start else '',
                    product_stopdate = _('to %s') %campaign.date_stop if campaign and campaign.date_stop else '',
                    stock_status = '{%s_stock_status}' % variant.id,
                    html_product_detail_desc = html_product_detail_desc(variant, partner, pricelist),
                    html_product_detail_image = html_product_detail_image(variant, partner),
                    html_product_ingredients_mobile = html_product_ingredients_mobile(variant, partner),
                    website_description = u'<div itemprop="description" class="oe_structure mt16" id="product_full_description">%s</div>' %variant.website_description if variant.website_description else '',
                    key_raw=key_raw,
                    key=key,
                    render_time='%s' % (timer() - render_start)
                ).encode('utf-8')
            page += "\n<!-- render_time_total %s -->\n" % (timer() - render_start_tot)
            self.env['website'].put_page_dict(key, flush_type, page, '%s,%s' % (product._model, product.id))
            page_dict['page'] = base64.b64encode(page)
        stock = {}
        for variant in product.product_variant_ids:
            stock['%s_in_stock' %variant.id],in_stock_state,stock['%s_stock_status' % variant.id] = self.get_stock_info(variant.id)
            if not pricelist.for_reseller:
                stock['%s_stock_status' % variant.id] = ''
                stock['%s_hide_add_to_cart' % variant.id] = 'hidden'
            else:
                stock['%s_hide_add_to_cart' % variant.id] = '' if (stock['%s_in_stock' %variant.id] and variant.sale_ok) else 'hidden'
        return page_dict.get('page','').decode('base64').format(**stock)


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
    def put_page_dict(self, key, flush_type, page, path):
        page_dict = {
            # ~ 'ETag':     '%s' % MEMCACHED_HASH(page),
            # ~ 'max-age':  max_age,
            # ~ 'cache-age':cache_age,
            # ~ 'private':  routing.get('private',False),
            # ~ 'key_raw':  key_raw,
            # ~ 'render_time': '%.3f sec' % (timer()-render_start),
            # ~ 'controller_time': '%.3f sec' % (render_start-controller_start),
            'path':     path,
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
