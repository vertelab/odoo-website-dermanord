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

    social_instagram = fields.Char(string='Instagram')
    social_snapchat = fields.Char(string='Snapchat')

    def current_menu(self, path):
        menu = self.env['website.menu'].search([('url', '=', path)])
        url = [x.split('-')[-1] if x.split('-')[-1].isdigit() else x for x in path.split('/')]
        while not menu and url:
            _logger.warn('/'.join(url))
            menu = self.env['website.menu'].search([('url', '=', '/'.join(url))])
            url = url[:-1]
        return menu

    def current_submenu(self, path):
        menu = self.current_menu(path)
        if menu.parent_id != self.env.ref('website.main_menu') and menu.parent_id != self.env.ref('theme_dermanord.footer_menu'):
            return menu.parent_id
        else:
            return menu

    def get_breadcrumb(self, path, **params):
        breadcrumb = []
        if path.startswith('/dn_shop/product/'): # url is a product
            product = params.get('product')
            if product:
                breadcrumb.append('<li>%s</li>' % product.name)
            menu = self.env.ref('webshop_dermanord.menu_dn_shop')
            home_menu = self.env.ref('website.menu_homepage')
            breadcrumb.append('<li><a href="%s">%s</a></li>' %(menu.url, menu.name))
            breadcrumb.append('<li><a href="%s">%s</a></li>' %(home_menu.url, home_menu.name))
            return ''.join(reversed(breadcrumb))
        elif path.startswith('/event'): # url is an event
            breadcrumb.append('<li><a href="%s">%s</a></li>' %('/', 'Home'))
            breadcrumb.append('<li><a href="%s">%s</a></li>' %('/event/', 'Event'))
            if len(path.split('/'))>2:
                event_id = path.split('/')[2].split('-')[-1]
                event = self.env['event.event'].browse(int(event_id))
                if event:
                    breadcrumb.append('<li><a href="/event/%s">%s</a></li>' %(event.id, event.name))
            #~ menu = self.env.ref('webshop_dermanord.menu_dn_shop')
            #~ home_menu = self.env.ref('website.menu_homepage')
            #~ breadcrumb.append('<li><a href="%s">%s</a></li>' %(menu.url, menu.name))
            #~ breadcrumb.append('<li><a href="%s">%s</a></li>' %(home_menu.url, home_menu.name))
            return ''.join(breadcrumb)
        elif path.startswith('/home'): # url is on the user home page
            path = path.split('/')[1:]
            _logger.warn(path)
            home_menu = self.env.ref('website.menu_homepage')
            breadcrumb = ['<li><a href="%s">%s</a></li>' %(home_menu.url, home_menu.name)]
            if len(path) > 1:
                user = self.env['res.users'].browse(int(path[1].split('-')[-1]))
            else:
                user = self.env.user
            breadcrumb.append('<li><a href="/home/%s">%s</a></li>' % (path[1], user.name))
            if len(path) > 3:
                if path[2] == 'order':
                    order = self.env['sale.order'].browse(int(path[3].split('-')[-1]))
                    breadcrumb.append('<li><a href="/home/%s?tab=orders">%s</a></li>' % (path[1], _('Orders')))
                    breadcrumb.append('<li><a href="/home/%s/order/%s">%s</a></li>' % (path[1], path[3], order.name))
                if path[2] == 'claim':
                    claim = self.env['crm.claim'].browse(int(path[3].split('-')[-1]))
                    breadcrumb.append('<li><a href="/home/%s?tab=claims">%s</a></li>' % (path[1], _('Claims')))
                    breadcrumb.append('<li><a href="/home/%s/claim/%s">%s</a></li>' % (path[1], path[3], claim.name))
                if path[2] == 'line':
                    order = self.env['sale.order'].search([('order_line', '=', int(path[3].split('-')[-1]))])
                    breadcrumb.append('<li><a href="/home/%s?tab=orders">%s</a></li>' % (path[1], _('Orders')))
                    breadcrumb.append('<li><a href="/home/%s/order/%s">%s</a></li>' % (path[1], order.id, order.name))
                    breadcrumb.append('<li><a href="/%s">%s</a></li>' % ('/'.join(path), _('File Claim')))
            return ''.join(breadcrumb)
        else: # url is a normal menu or submenu
            path = path.split('/')
            for i in range(len(path)):
                nr = path[i].split('-')[-1]
                if nr.isdigit():
                    path[i] = nr
            path = '/'.join(path)
            skipped = self.env.ref('theme_dermanord.footer_menu')
            menu = self.env['website.menu'].search([('url', '=', path)])
            while menu and menu != self.env.ref('website.main_menu') and menu != self.env.ref('website.menu_homepage'):
                if menu not in skipped:
                    breadcrumb.append('<li><a href="%s">%s</a></li>' %(menu.url, menu.name))
                menu = menu.parent_id
            home_menu = self.env.ref('website.menu_homepage')
            breadcrumb.append('<li><a href="%s">%s</a></li>' %(home_menu.url, home_menu.name))
            return ''.join(reversed(breadcrumb))

class website_config_settings(models.TransientModel):
    _inherit = 'website.config.settings'

    social_instagram = fields.Char(related='website_id.social_instagram', string='Instagram Account')
    social_snapchat = fields.Char(related='website_id.social_snapchat', string='Snapchat Account')

class website_menu(models.Model):
    _inherit = 'website.menu'

    page_title = fields.Char(default='Page Title')
    image = fields.Binary()


class ThemeDermanord(http.Controller):

    @http.route(['/get_parent_menu'], type='json', auth="public", website=True)
    def get_parent_menu(self, url):
        return request.website.current_menu(url).parent_id.url

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
