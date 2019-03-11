# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution, third party addon
#    Copyright (C) 2018 Vertel AB (<http://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import openerp
import datetime
from itertools import islice
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp import models, fields, api, _
from openerp import http
from openerp.http import request
from openerp.addons.website.controllers.main import Website
from openerp.addons.website_memcached import memcached

import logging
_logger = logging.getLogger(__name__)

LOC_PER_SITEMAP = 45000 # https://www.sitemaps.org/faq.html says: Sitemaps should be no larger than 50MB (52,428,800 bytes) and can contain a maximum of 50,000 URLs.
SITEMAP_CACHE_TIME = datetime.timedelta(hours=12)

class Website(Website):

    @memcached.route(key=lambda kw:'db: {db} path: sitemap.xml', flush_type=lambda kw: 'sitemap', no_cache=True, cache_age=31536000, max_age=31536000, s_maxage=43200)
    def sitemap_xml_index(self):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        iuv = request.registry['ir.ui.view']
        mimetype ='application/xml;charset=utf-8'
        content = None

        pages = 0
        first_page = None
        router = request.env['ir.config_parameter'].get_param('web.base.url')

        def get_locs():
            products = request.env['product.product'].sudo(user=request.website.user_id.id).search([('sale_ok', '=', True)])
            blog_posts = request.env['blog.post'].sudo(user=request.website.user_id.id).search([('website_published', '=', True)])
            menus = request.env['website.menu'].sudo(user=request.website.user_id.id).search([('url', 'ilike', '/page/')])
            for p in products:
                yield {'loc': '/dn_shop/variant/%s' %(p.id)}
            for p in blog_posts:
                yield {'loc': '/blog/%s/post/%s' %(p.blog_id.id, p.id)}
            for m in menus:
                yield {'loc': m.url}

        locs = get_locs()

        while True:
            values = {
                'locs': islice(locs, 0, LOC_PER_SITEMAP),
                'url_root': router,
            }
            urls = iuv.render(cr, uid, 'website.sitemap_locs', values, context=context)
            if urls.strip():
                page = iuv.render(cr, uid, 'website.sitemap_xml', dict(content=urls), context=context)
                if not first_page:
                    first_page = page
                pages += 1
            else:
                break
        if not pages:
            return request.not_found()
        elif pages == 1:
            content = first_page
        else:
            content = iuv.render(cr, uid, 'website.sitemap_index_xml', dict(
                pages=range(1, pages + 1),
                url_root=request.httprequest.url_root,
            ), context=context)

        return request.make_response(content, [('Content-Type', mimetype)])
    
    # 2019-03-06 multiple sitemaps.
    # Blogg, News Room, Press, Page
    @http.route('/sitemap_blog.xml', type='http', auth="public", website=True)
    def sitemap_xml_index_blog(self):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        ira = request.registry['ir.attachment']
        iuv = request.registry['ir.ui.view']
        mimetype ='application/xml;charset=utf-8'
        content = None

        def create_sitemap(url, content):
            ira.create(cr, uid, dict(
                datas=content.encode('base64'),
                mimetype=mimetype,
                type='binary',
                name=url,
                url=url,
            ), context=context)

        sitemap = ira.search_read(cr, uid, [('url', '=' , '/sitemap_blog.xml'), ('type', '=', 'binary')], ('datas', 'create_date'), context=context)
        if sitemap:
            # Check if stored version is still valid
            server_format = openerp.tools.misc.DEFAULT_SERVER_DATETIME_FORMAT
            create_date = datetime.datetime.strptime(sitemap[0]['create_date'], server_format)
            delta = datetime.datetime.now() - create_date
            if delta < SITEMAP_CACHE_TIME:
                content = sitemap[0]['datas'].decode('base64')

        if not content:
            # Remove all sitemaps in ir.attachments as we're going to regenerated them
            sitemap_ids = ira.search(cr, uid, [('url', '=like' , '/sitemap%.xml'), ('type', '=', 'binary')], context=context)
            if sitemap_ids:
                ira.unlink(cr, uid, sitemap_ids, context=context)

            pages = 0
            first_page = None
            locs = request.website.sudo(user=request.website.user_id.id).enumerate_pages()
            while True:
                values = {
                    'locs': islice(locs, 0, LOC_PER_SITEMAP),
                    'url_root': request.httprequest.url_root[:-1],
                }
                urls = iuv.render(cr, uid, 'website.sitemap_locs', values, context=context)
                if urls.strip():
                    page = iuv.render(cr, uid, 'website.sitemap_xml', dict(content=urls), context=context)
                    if not first_page:
                        first_page = page
                    pages += 1
                    create_sitemap('/sitemap-%d.xml' % pages, page)
                else:
                    break
            if not pages:
                return request.not_found()
            elif pages == 1:
                content = first_page
            else:
                # Sitemaps must be split in several smaller files with a sitemap index
                content = iuv.render(cr, uid, 'website.sitemap_index_xml', dict(
                    pages=range(1, pages + 1),
                    url_root=request.httprequest.url_root,
                ), context=context)
            create_sitemap('/sitemap.xml', content)

        return request.make_response(content, [('Content-Type', mimetype)])
