# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2004-2017 Vertel AB (<http://vertel.se>).
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
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp import models, fields, api, _
from openerp import http
from openerp.http import request
import werkzeug
import logging
_logger = logging.getLogger(__name__)

    
class product_action(models.Model):
    _inherit = 'product.action'
    action_type = fields.Selection(selection_add=[('show_on_startpage','Show on Startpage')])
    onoff_show_on_startpage = fields.Boolean(string="New state")

    @api.one
    def _action_str(self):
        if self.action_type == 'show_on_startpage':
            self.action_str = _('Show on Start Page') if self.onoff_show_on_startpage else _('Not on Start Page')
        else:
            super(product_action,self)._action_str()

    @api.one
    def do_action(self):
        if self.action_type == 'show_on_startpage':
            self.product_id.show_on_startpage = self.action.onoff_show_on_startpage
        else:
            super(product_action,self)._do_action()

class product_product(models.Model):
    _inherit = 'product.product'
    show_on_startpage = fields.Boolean(string="Show on Start Page")


class snippet(http.Controller):

    @http.route(['/blog_banner_snippet/blog_banner_change'], type='json', auth="public", website=True)
    def blog_banner_change(self, blog_id=None, **kw):
        posts = request.env['blog.post'].search([('blog_id', '=', int(blog_id)), ('website_published', '=', True)], order='write_date')
        posts_list = {}
        if len(posts) > 0:
            for p in posts:
                post_image_url = ''
                if p.background_image and '/ir.attachment/' in p.background_image:
                    start = str(p.background_image).index('/ir.attachment/') + len('/ir.attachment/')
                    end = str(p.background_image).index('/datas', start )
                    post_image_url = '/imagefield/ir.attachment/datas/%s/ref/%s' %(str(p.background_image)[start:end].split('_')[0], 'snippet_dermanord.img_blog_slide')
                posts_list[p.id] = {
                    'name': p.name,
                    'blog_id': p.blog_id.id,
                    'background_image': post_image_url,
                }
        return posts_list

    @http.route(['/get_sale_promotions'], type='json', auth="public", website=True)
    def get_sale_promotions(self, **kw):
        sps = request.env['sale.promotion'].sudo().search([('website_published', '=', True)], order='sequence')
        sp_list = []
        image = 'image_sv' if request.context.get('lang') == 'sv_SE' else 'image_en'
        if len(sps) > 0:
            for sp in sps.sorted(key=lambda s: s.sequence):
                sp_list.append(
                    {
                        'id': sp.id,
                        'name': sp.name,
                        'description': sp.description,
                        'url': sp.url,
                        'image': '/imagefield/sale.promotion/%s/%s/ref/%s' %(image, sp.id, 'snippet_dermanord.img_sale_promotions'),
                    }
                )
        return sp_list

    @http.route(['/category_snippet/get_p_categories'], type='json', auth="public", website=True)
    def get_p_categories(self, **kw):
        categories = request.env['product.public.category'].search([('website_published', '=', True)], order='sequence')
        category_list = []
        if len(categories) > 0:
            for c in categories:
                image_url = ''
                if c.image_medium:
                    image_url = '/imagefield/product.public.category/image/%s/ref/%s' %(c.id, 'snippet_dermanord.img_categories')
                category_list.append(
                    {
                        'id': c.id,
                        'name': c.name,
                        'image': image_url,
                    }
                )
        return category_list

    @http.route(['/product_hightlights_snippet/get_highlighted_products'], type='json', auth="public", website=True)
    def get_highlighted_products(self, campaign_date, **kw):
        def check_access(object):
            return request.env[object._name].sudo(request.env.ref('base.public_user').id).search([('id', '=', object.id)])
        date = fields.Date.today() if campaign_date == '' else campaign_date
        campaigns = request.env['crm.tracking.campaign'].sudo().search([
            ('state', '=', 'open'),
            ('website_published', '=', True),
            ('date_start', '<=', date),
            '|',
                ('date_stop', '>=', date),
                '&',
                    ('date_stop', '=', False),
                    '|',
                        ('country_id', '=', request.env.ref('base.se').id),
                        ('country_id', '=', False)
        ])
        object_list = []
        if campaigns:
            occs = request.env['crm.campaign.object'].browse([])
            for c in campaigns:
                if c.object_ids:
                    occs |= c.object_ids
            if occs:
                occs = occs.sorted(key=lambda o: o.sequence)
                for occ in occs:
                    url = ''
                    if occ.object_id._name == 'product.template':
                        if check_access(occ.object_id):
                            url = '/dn_shop/product/%s' %occ.object_id.id
                    elif occ.object_id._name == 'product.product':
                        if check_access(occ.object_id):
                            url = '/dn_shop/variant/%s' %(occ.object_id.id)
                    elif occ.object_id._name == 'product.public.category':
                        if check_access(occ.object_id):
                            url = '/dn_shop/category/%s' %occ.object_id.id
                    elif occ.object_id._name == 'blog.post':
                        if check_access(occ.object_id):
                            url = '/blog/%s/post/%s' %(occ.object_id.blog_id.id, occ.object_id.id)
                    if url:
                        object_list.append(
                            {
                                'id': occ.id,
                                'name': occ.name if occ.name else '',
                                'image': '/imagefield/crm.campaign.object/image/%s/ref/%s' %(occ.id, 'snippet_dermanord.img_product') if occ.image else '/web/static/src/img/placeholder.png',
                                'description': occ.description if occ.description else '',
                                'url': url,
                            }
                        )
        for product in request.env['product.product'].search([('show_on_startpage','=',True)]):
            object_list.append(
                {
                    'id': None,
                    'name': product.name,
                    'image': '/imagefield/product.product/image/%s/ref/%s' %(product.id, 'snippet_dermanord.img_product') if product.image else '/web/static/src/img/placeholder.png',
                    'description': product.public_desc,
                    'url': '/dn_shop/variant/%s' % product.id,
                }
            )
        return object_list
