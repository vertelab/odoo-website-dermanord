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
                posts_list[p.id] = {
                    'name': p.name,
                    'blog_id': p.blog_id.id,
                    'background_image': p.background_image,
                }
        return posts_list

    @http.route(['/category_snippet/get_p_categories'], type='json', auth="user", website=True)
    def get_p_categories(self, **kw):
        categories = request.env['product.public.category'].search([('website_published', '=', True)], order='sequence')
        category_list = {}
        if len(categories) > 0:
            for c in categories:
                category_list[c.id] = {
                    'name': c.name,
                    'image': c.image_medium,
                }
        return category_list

    @http.route(['/product_hightlights_snippet/get_highlighted_products'], type='json', auth="user", website=True)
    def get_highlighted_products(self, **kw):
        products = request.env['product.template'].search([('active', '=', True), ('sale_ok', '=', True), ('highlight', '=', True)])
        product_list = {}
        if len(products) > 0:
            for p in products:
                product_image_url = '';
                if len(p.image_ids) > 0:
                    product_image_url = '/imagefield/base_multi_image.image/file_db_store/%s/ref/%s' %(p.image_ids[0].id, 'snippet_dermanord.product_highlight')
                product_list[p.id] = {
                    'name': p.name,
                    'image': product_image_url,
                    'description_sale': p.description_sale,
                }
        return product_list
