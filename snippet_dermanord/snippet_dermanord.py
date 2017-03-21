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


class snippet(http.Controller):

    @http.route(['/blog_banner_snippet/blog_banner_change'], type='json', auth="user", website=True)
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

    @http.route(['/get_sale_promotions'], type='json', auth="user", website=True)
    def get_sale_promotions(self, **kw):
        sps = request.env['sale.promotion'].sudo().search([('website_published', '=', True)], order='sequence')
        sp_list = []
        if len(sps) > 0:
            for sp in sps.sorted(key=lambda s: s.sequence):
                sp_list.append(
                    {
                        'id': sp.id,
                        'name': sp.name,
                        'description': sp.description,
                        'url': sp.url,
                        'image': '/imagefield/sale.promotion/image/%s/ref/%s' %(sp.id, 'snippet_dermanord.img_sale_promotions'),
                    }
                )
        return sp_list

    @http.route(['/category_snippet/get_p_categories'], type='json', auth="user", website=True)
    def get_p_categories(self, **kw):
        categories = request.env['product.public.category'].search([('website_published', '=', True)], order='sequence')
        category_list = []
        if len(categories) > 0:
            for c in categories:
                image_url = ''
                if c.image_medium:
                    image_url = '/imagefield/product.public.category/image_medium/%s/ref/%s' %(c.id, 'snippet_dermanord.img_categories')
                category_list.append(
                    {
                        'id': c.id,
                        'name': c.name,
                        'image': image_url,
                    }
                )
        return category_list

    @http.route(['/product_hightlights_snippet/get_highlighted_products'], type='json', auth="user", website=True)
    def get_highlighted_products(self, **kw):
        campaigns = request.env['crm.tracking.campaign'].sudo().search([('date_start', '<=', fields.Date.today()), ('date_stop', '>=', fields.Date.today())])
        object_list = []
        if len(campaigns) > 0:
            occs = request.env['object.crm.campaign'].browse([])
            for c in campaigns:
                if len(c.object_ids) > 0:
                    for occ in c.object_ids:
                        occs |= occ
            if len(occs) > 0:
                occs = occs.sorted(key=lambda o: o.sequence)
                for occ in occs:
                    url = ''
                    if occ.object_id._name == 'product.template':
                        url = '/shop/product/%s' %occ.object_id.id
                    elif occ.object_id._name == 'product.product':
                        url = '/shop/variant/%s' %(occ.object_id.id)
                    elif occ.object_id._name == 'product.public.category':
                        url = '/shop/category/%s' %occ.object_id.id
                    elif occ.object_id._name == 'blog.post':
                        url = '/blog/%s/post/%s' %(occ.object_id.blog_id.id, occ.object_id.id)
                    object_list.append(
                        {
                            'id': occ.id,
                            'name': occ.name if occ.name else '',
                            'image': '/imagefield/object.crm.campaign/image/%s/ref/%s' %(occ.id, 'snippet_dermanord.img_product') if occ.image else '',
                            'description': occ.description if occ.description else '',
                            'url': url,
                        }
                    )
        return object_list
