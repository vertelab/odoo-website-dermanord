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
from datetime import datetime
from lxml import html
import werkzeug

import logging
_logger = logging.getLogger(__name__)

#~ class res_company(models.Model):
    #~ _inherit = 'res.company'

    #~ logo_website = fields.Binary(string='Logo For Website', help='This company logo shows only on website')

class website(models.Model):
    _inherit = 'website'

    def current_menu(self, path):
        return self.env['website.menu'].search([('url', '=', path)])

    def current_submenu(self, path):
        menu = self.env['website.menu'].search([('url', '=', path)])
        if menu.parent_id != self.env.ref('website.main_menu'):
            return menu.parent_id
        else:
            return menu

    def get_breadcrumb(self, path):
        breadcrumb = []
        if path.startswith('/blog/'): # url is a blog
            if '/post/' in path:
                home_menu = self.env.ref('website.menu_homepage')
                blog_id = path[(path.index('/blog/')+len('/blog/')):path.index('/post/')].split('-')[-1]
                post_id = path.split('/post/')[-1].split('-')[-1]
                if isinstance(blog_id, int) and isinstance(post_id, int):
                    blog = request.env['blog.blog'].browse(int(blog_id))
                    post = request.env['blog.post'].browse(int(post_id))
                    if blog and post:
                        breadcrumb.append('<li><a href="%s">%s</a></li><li><a href="/blog/%s">%s</a></li><li><a href="%s">%s</a></li>' %(home_menu.url, home_menu.name, blog.id, blog.name, post.id, post.name))
                        return '<ol class="breadcrumb">%s</ol>' %breadcrumb[0]
            else:
                home_menu = self.env.ref('website.menu_homepage')
                blog_id = path.split('/blog/')[-1].split('-')[-1]
                if isinstance(blog_id, int):
                    blog = request.env['blog.blog'].browse(int(blog_id))
                    if blog:
                        breadcrumb.append('<li><a href="%s">%s</a></li><li><a href="%s">%s</a></li>' %(home_menu.url, home_menu.name, blog.id, blog.name))
                        return '<ol class="breadcrumb">%s</ol>' %breadcrumb[0]
        else: # url is a normal menu or submenu
            menu = self.env['website.menu'].search([('url', '=', path)])
            while menu and menu != self.env.ref('website.main_menu') and menu != self.env.ref('website.menu_homepage'):
                breadcrumb.append('<li><a href="%s">%s</a></li>' %(menu.url, menu.name))
                menu = menu.parent_id
            home_menu = self.env.ref('website.menu_homepage')
            breadcrumb.append('<li><a href="%s">%s</a></li>' %(home_menu.url, home_menu.name))
            return '<ol class="breadcrumb">%s</ol>' %''.join(reversed(breadcrumb))


class website_menu(models.Model):
    _inherit = 'website.menu'

    page_title = fields.Char(default='Page Title')
    image = fields.Binary()


class ThemeDermanord(http.Controller):

    @http.route(['/page/dermanord_demo'], type='http', auth="public", website=True)
    def dermanord_demo(self):
        return request.website.render('theme_dermanord.dermanord_demo_page', {})

    @http.route(['/logo500.png'], type='http', auth="public", cors="*")
    def company_logo500(self):
        user = request.registry['res.users'].browse(request.cr, request.uid, request.uid)
        response = werkzeug.wrappers.Response()
        return request.registry['website']._image(request.cr, request.uid, 'res.company', user.company_id.id, 'logo',
                                                  response, max_width=500, max_height=None, )

    @http.route(['/logo1024.png'], type='http', auth="public", cors="*")
    def company_logo1024(self):
        user = request.registry['res.users'].browse(request.cr, request.uid, request.uid)
        response = werkzeug.wrappers.Response()
        return request.registry['website']._image(request.cr, request.uid, 'res.company', user.company_id.id, 'logo',
                                                  response, max_width=1024, max_height=None, )
