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
        for c in categories:
            category_list[c.id] = {
                'name': c.name,
                'image': c.image_medium,
            }
        return category_list
