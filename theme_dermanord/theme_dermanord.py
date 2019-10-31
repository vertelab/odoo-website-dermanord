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
from openerp.tools.misc import file_open
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
        _logger.warn('path: %s' %path)
        _logger.warn('url: %s' %url)
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
        try:
            breadcrumb = []
            if path.startswith('/dn_shop/product/') or path.startswith('/dn_shop/variant/'): # url is a product
                product = params.get('product')
                if product:
                    breadcrumb.append('<li>%s</li>' % product.name)
                menu = self.env.ref('webshop_dermanord.menu_dn_shop')
                home_menu = self.env.ref('website.menu_homepage')
                breadcrumb.append('<li><a href="%s">%s</a></li>' %(menu.url, menu.name))
                breadcrumb.append('<li><a href="%s">%s</a></li>' %(home_menu.url, home_menu.name))
                return ''.join(reversed(breadcrumb))
            elif path.startswith('/event'): # url is an event
                home_menu = self.env.ref('website.menu_homepage')
                breadcrumb.append('<li><a href="%s">%s</a></li>' %(home_menu.url, home_menu.name))
                breadcrumb.append('<li><a href="%s">%s</a></li>' %('/event/', self.env.ref('website_event.menu_events').name))
                path = path.split('/')
                if len(path)>2:
                    if path[2] == 'type':
                        if len(path) > 3:
                            event_type_id = path[3].split('?')[0].split('-')[-1]
                            event_type = self.env['event.type'].search_read([('id', '=', int(event_type_id))], ['name'])
                            event_type = event_type and event_type[0]
                            if event_type:
                                breadcrumb.append('<li><a href="/event/type/%s">%s</a></li>' %(event_type['id'], event_type['name']))
                    else:
                        event_id = path[2].split('?')[0].split('-')[-1]
                        event = self.env['event.event'].search_read([('id', '=', int(event_id))], ['name'])
                        event = event and event[0]
                        if event:
                            breadcrumb.append('<li><a href="/event/%s">%s</a></li>' %(event['id'], event['name']))
                return ''.join(breadcrumb)
            elif path.startswith('/jobs/detail'): # url is a job
                home_menu = self.env.ref('website.menu_homepage')
                breadcrumb.append('<li><a href="%s">%s</a></li>' %(home_menu.url, home_menu.name))
                breadcrumb.append('<li><a href="%s">%s</a></li>' %('/jobs/start/', self.env.ref('website_hr_recruitment_dermanord.jobs_start_menu').name))
                breadcrumb.append('<li><a href="%s">%s</a></li>' %('/jobs/', self.env.ref('website_hr_recruitment.menu_jobs').name))
                breadcrumb.append('<li>%s</li>' %params.get('job').name)
                return ''.join(breadcrumb)
            elif path.startswith('/home'): # url is on the user home page
                path = path.split('/')[1:]
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
                menu = None
                path = path.split('/')
                for i in range(len(path)):
                    nr = path[i].split('-')[-1]
                    if nr.isdigit():
                        path[i] = nr
                # Check if this is the path to a blog post
                if len(path) > 3 and path[1] == 'blog' and path[3] == 'post':
                    blog = params.get('blog')
                    blog_post = params.get('blog_post')
                    if blog and blog_post:
                        for tag in blog_post.tag_ids:
                            menu = self.env['website.menu'].search([('url', '=', '/blog/%s/tag/%s' % (blog.id, tag.id))])
                            if menu:
                                breadcrumb.append('<li>%s</li>' % blog_post.name)
                                break
                path = '/'.join(path)
                skipped = self.env.ref('theme_dermanord.footer_menu')
                menu = menu or self.env['website.menu'].search([('url', '=', path)])
                while menu and menu != self.env.ref('website.main_menu') and menu != self.env.ref('website.menu_homepage'):
                    if menu not in skipped:
                        breadcrumb.append('<li><a href="%s">%s</a></li>' %(menu.url, menu.name))
                    menu = menu.parent_id
                home_menu = self.env.ref('website.menu_homepage')
                breadcrumb.append('<li><a href="%s">%s</a></li>' %(home_menu.url, home_menu.name))
                return ''.join(reversed(breadcrumb))
        except:
            return '<li><a href="/">Home</a></li>'

    def enumerate_pages(self, cr, uid, ids, query_string=None, context=None):
        """ Available pages in the website/CMS. This is mostly used for links
        generation and can be overridden by modules setting up new HTML
        controllers for dynamic pages (e.g. blog).

        By default, returns template views marked as pages.

        :param str query_string: a (user-provided) string, fetches pages
                                 matching the string
        :returns: a list of mappings with two keys: ``name`` is the displayable
                  name of the resource (page), ``url`` is the absolute URL
                  of the same.
        :rtype: list({name: str, url: str})
        """
        router = request.httprequest.app.get_db_router(request.db)
        # Force enumeration to be performed as public user
        url_set = set()
        for rule in router.iter_rules():
            if not self.rule_is_enumerable(rule):
                continue

            converters = rule._converters or {}
            if query_string and not converters and (query_string not in rule.build([{}], append_unknown=False)[1]):
                continue
            if rule.rule == '/imagemagick/<model("ir.attachment"):image>/id/<model("image.recipe"):recipe>':
                continue
            values = [{}]
            convitems = converters.items()
            # converters with a domain are processed after the other ones
            gd = lambda x: hasattr(x[1], 'domain') and (x[1].domain <> '[]')
            convitems.sort(lambda x, y: cmp(gd(x), gd(y)))
            for (i,(name, converter)) in enumerate(convitems):
                newval = []
                for val in values:
                    query = i==(len(convitems)-1) and query_string
                    for v in converter.generate(request.cr, uid, query=query, args=val, context=context):
                        newval.append( val.copy() )
                        v[name] = v['loc']
                        del v['loc']
                        newval[-1].update(v)
                values = newval

            for value in values:
                domain_part, url = rule.build(value, append_unknown=False)
                page = {'loc': url}
                for key,val in value.items():
                    if key.startswith('__'):
                        page[key[2:]] = val
                if url in ('/sitemap.xml',):
                    continue
                if url in url_set:
                    continue
                url_set.add(url)

                yield page

class website_config_settings(models.TransientModel):
    _inherit = 'website.config.settings'

    social_instagram = fields.Char(related='website_id.social_instagram', string='Instagram Account')
    social_snapchat = fields.Char(related='website_id.social_snapchat', string='Snapchat Account')

class website_menu(models.Model):
    _inherit = 'website.menu'

    page_title = fields.Char(default='Page Title')
    image = fields.Binary()


class ThemeDermanord(http.Controller):
    
    @http.route(['/theme_dermanord/is_agent'], type='json', auth="public", website=True)
    def is_agent(self):
        return request.env.user.commercial_partner_id.agent
    
    # ~ @http.route(['/get_parent_menu'], type='json', auth="public", website=True)
    # ~ def get_parent_menu(self, url):
        # ~ return request.website.current_menu(url).parent_id.url

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

    @http.route(['/favicon.ico'], type='http', auth='public', cors="*")
    def favicon_ico(self):
        favicon = file_open('theme_dermanord/static/ico/favicon.ico')
        favicon_mimetype = 'image/x-icon'
        return http.request.make_response(
            favicon.read(), [('Content-Type', favicon_mimetype)])

    @http.route(['/apple-touch-icon.png', '/apple-touch-icon-precomposed.png'], type='http', auth='public', cors="*")
    def apple_touch_icon(self):
        icon = file_open('theme_dermanord/static/ico/apple-touch-icon.png')
        icon_mimetype = 'image/x-icon'
        return http.request.make_response(
            icon.read(), [('Content-Type', icon_mimetype)])

    @http.route(['/apple-touch-icon-120x120.png', '/apple-touch-icon-120x120-precomposed.png'], type='http', auth='public', cors="*")
    def apple_touch_icon_120x120(self):
        icon = file_open('theme_dermanord/static/ico/apple-touch-icon-120x120.png')
        icon_mimetype = 'image/x-icon'
        return http.request.make_response(
            icon.read(), [('Content-Type', icon_mimetype)])

    @http.route(['/apple-touch-icon-152x152.png', '/apple-touch-icon-152x152-precomposed.png'], type='http', auth='public', cors="*")
    def apple_touch_icon_152x152(self):
        icon = file_open('theme_dermanord/static/ico/apple-touch-icon-152x152.png')
        icon_mimetype = 'image/x-icon'
        return http.request.make_response(
            icon.read(), [('Content-Type', icon_mimetype)])


class ResCompany(models.Model):
    _inherit = 'res.company'

    def google_map_img(self, cr, uid, ids, zoom=8, width=298, height=298, marker=None, context=None):
        env = api.Environment(cr, uid, context)
        return super(ResCompany, self).google_map_img(cr, uid, ids,
            zoom=zoom, width=width, height=height, marker=marker or {
                'icon': env['ir.config_parameter'].get_param(
                    'dermanord_map_marker',
                    'http://wiggum.vertel.se/dn_maps_marker.png')
            }, context=context)
