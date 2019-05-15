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
from openerp.addons.website.models.website import slug

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
            translations = {'en_US': 'en'}
            for p in products:
				# ~ EXAMPLE PRODUCT:
				# ~ https://mariaakerberg.com/sv_SE/dn_shop/product/24-7-plus-set-8781
				# ~ IN GOOGLE, ABOUT LANGUAGES:
				# ~ https://support.google.com/webmasters/answer/189077?hl=en
                res = {
					'loc': '/sv_SE/dn_shop/product/%s' %slug(p.with_context(lang='sv_SE')),
					'alternates': {}
				}
                for lang, google_lang in translations.iteritems():
					res['alternates'][google_lang] = '/%s/dn_shop/product/%s' %(lang, slug(p.with_context(lang=lang)))
                yield res
                
            for p in blog_posts:
				# ~ p = p.with_context(lang='en_US')
                # ~ yield {'loc': '/blog/%s/post/%s' %(slug(p.blog_id), slug(p))}
                
                res = {
					'loc': '/sv_SE/blog/%s/post/%s' %(slug(p.blog_id), slug(p.with_context(lang='sv_SE')) ),
					'alternates': {}
				}
                for lang, google_lang in translations.iteritems():
					res['alternates'][google_lang] = '/%s/blog/post/%s' %(lang, slug(p.with_context(lang=lang)))
                yield res
                
            for m in menus:
                # ~ yield {'loc': m.url}
                res = {
					# ~ 'loc': '/sv_SE/page/%s' %(slug(m.with_context(lang='en_US')) ),
					'loc': '/sv_SE%s' %(m.url),
					'alternates': {}
				}
                for lang, google_lang in translations.iteritems():
					res['alternates'][google_lang] = '/%s%s' %(lang, m.url)
                yield res

        locs = get_locs()
        # ~ _logger.warn('------------> sitemap %s ' % [l for l in locs])
        content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">
"""
        for locs in get_locs():
            content += """<url>
    <loc>{host}{loc}</loc>
    <xhtml:link 
		   rel="alternate"
		   hreflang="en"
		   href="{host}{alternates_en}"/>
    </url>""".format( host = 'https://mariaakerberg.com', loc = locs['loc'], alternates_en = locs.get('alternates', {'en':''})['en'] )
			
			
        # ~ while True:
            # ~ values = {
                # ~ 'locs': islice(locs, 0, LOC_PER_SITEMAP),
                # ~ 'url_root': router,
            # ~ }
            # ~ urls = iuv.render(cr, uid, 'website.sitemap_locs', values, context=context)
            # ~ if urls.strip():
                # ~ page = iuv.render(cr, uid, 'website.sitemap_xml', dict(content=urls), context=context)
                # ~ if not first_page:
                    # ~ first_page = page
                # ~ pages += 1
            # ~ else:
                # ~ break
        # ~ if not pages:
            # ~ return request.not_found()
        # ~ elif pages == 1:
            # ~ content = first_page
        # ~ else:
            # ~ content = iuv.render(cr, uid, 'website.sitemap_index_xml', dict(
                # ~ pages=range(1, pages + 1),
                # ~ url_root=request.httprequest.url_root,
            # ~ ), context=context)

        return request.make_response(content + '</urlset>', [('Content-Type', mimetype)])
    
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
        

    # ~ @http.route('/test.xml', type='http', auth="public", website=True)
    # ~ def sitemap_xml_index_product(self):
            # ~ return request.make_response('someting', [('Content-Type', 'application/xml;charset=utf-8')])
        
    @http.route('/sitemap_product_SE.xml', type='http', auth="public", website=True)
    def sitemap_xml_index_product_SE(self):
        content = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">"""
        for product in request.env['product.template'].sudo(user=request.website.user_id.id).search([('sale_ok', '=', True)]):
            # ~ _logger.warn('CONTENT : %s', product)
            content += """<url><loc>{loc}</loc>
            <lastmod>{lastmod}</lastmod>
            <changefreq>{changefreq}</changefreq>
            <priority>{priority}</priority>
            </url>""".format(loc='%s/sv_SE/dn_shop/product/%s' % (request.env['ir.config_parameter'].get_param('web.base.url'), slug(product)), lastmod='%s' % product.create_date[:10] , changefreq='monthly', priority='0.7')
     
        content += "</urlset>"
        return request.make_response(content, [('Content-Type', 'application/xml;charset=utf-8')])

    @http.route('/sitemap_blog_SE.xml', type='http', auth="public", website=True)
    def sitemap_xml_index_blog_SE(self):
        # ~ blog_posts = request.env['blog.post'].sudo(user=request.website.user_id.id).search([('website_published', '=', True)])
        content = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">"""
        for blog in request.env['blog.post'].sudo(user=request.website.user_id.id).search([('website_published', '=', True)]):
            # ~ _logger.warn('CONTENT : %s', content)
            content += """<url><loc>{loc}</loc>
            <lastmod>{lastmod}</lastmod>
            <changefreq>{changefreq}</changefreq>
            <priority>{priority}</priority>
            </url>""".format(loc='%s/sv_SE/blog/%s/post/%s' % (request.env['ir.config_parameter'].get_param('web.base.url'), slug(blog.blog_id), slug(blog)), lastmod='%s' % blog.write_date[:10] , changefreq='monthly', priority='0.7')

        content += "</urlset>"
        
        # ~ _logger.debug('CONTENT : %s', content)
        return request.make_response(content, [('Content-Type', 'application/xml;charset=utf-8')])

    @http.route('/sitemap_page_SE.xml', type='http', auth="public", website=True)
    def sitemap_xml_index_page_SE(self):
        # ~ menus = request.env['website.menu'].sudo(user=request.website.user_id.id).search([('url', 'ilike', '/page/')])
        content = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">"""
        for menu in request.env['website.menu'].sudo(user=request.website.user_id.id).search([('url', 'ilike', '/page/')]):
            # ~ _logger.warn('CONTENT : %s', content)
            content += """<url><loc>{loc}</loc>
            <lastmod>{lastmod}</lastmod>
            <changefreq>{changefreq}</changefreq>
            <priority>{priority}</priority>
            </url>""".format(loc='%s/sv_SE/page/%s' % (request.env['ir.config_parameter'].get_param('web.base.url'), slug(name)), lastmod='%s' % menu.write_date[:10] , changefreq='yearly', priority='0.7')

        content += "</urlset>"
        
        # ~ _logger.debug('CONTENT : %s', content)
        return request.make_response(content, [('Content-Type', 'application/xml;charset=utf-8')])

    # ~ @http.route('/sitemap_reseller_SE.xml', type='http', auth="public", website=True)
    # ~ def sitemap_xml_index_reseller_SE(self):
        # ~ menus = request.env['website.menu'].sudo(user=request.website.user_id.id).search([('url', 'ilike', '/page/')])
        # ~ content = """<?xml version="1.0" encoding="UTF-8"?>
        # ~ <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">"""
        # ~ for reseller in request.env['res.partner'].sudo().search([('is_reseller', '=', True), ('is_company', '=', True)]):
            # ~ _logger.warn('CONTENT : %s', content)
            # ~ content += """<url><loc>{loc}</loc>
            # ~ <lastmod>{lastmod}</lastmod>
            # ~ <changefreq>{changefreq}</changefreq>
            # ~ <priority>{priority}</priority>
            # ~ </url>""".format(
                # ~ loc='%s/sv_SE/reseller/%s' % (request.env['ir.config_parameter'].get_param('web.base.url'), reseller.id),
                # ~ lastmod='%s' % reseller.write_date[:10],
                # ~ changefreq='yearly',
                # ~ priority='0.7')

        # ~ content += "</urlset>"
        
        # ~ _logger.debug('CONTENT : %s', content)
        # ~ return request.make_response(content, [('Content-Type', 'application/xml;charset=utf-8')])


