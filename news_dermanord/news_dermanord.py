# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2017- Vertel AB (<http://vertel.se>).
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

from openerp import models, fields, api, http, _
from openerp.http import request
from openerp.addons.website_blog.controllers.main import WebsiteBlog

import logging
_logger = logging.getLogger(__name__)

BPG = 8

class newsDermanord(http.Controller):

    @http.route(['/news', '/news/page/<model("blog.post"):page>','/news/tagg/<model("blog.tag"):tag>'], type='http', auth="public", website=True)
    def repord(self, page=None, tag=None, **post):
        return request.website.render("news_dermanord.page", {'tag': tag, 'page': page})

class BlogTag(models.Model):
    _inherit = 'blog.tag'

    background_image = fields.Binary(string='Background Image')

class WebsiteBlog(WebsiteBlog):

    @http.route(['/website_blog_json_list'], type='json', auth='public', website=True)
    def website_blog_json_list(self, page=0, **kw):
        blog_post_list = []
        if request.session.get('blog_domain'):
            str_read_more = u'Läs mer' if request.context.get('lang') == 'sv_SE' else 'Read more'
            str_tags = 'Etiketter:' if request.context.get('lang') == 'sv_SE' else 'Tags:'
            blog_posts = request.env['blog.post'].search(request.session['blog_domain']['domain'], order=request.session['blog_domain']['order'], limit=BPG, offset=(int(page)+1)*BPG)
            if len(blog_posts) > 0:
                for p in blog_posts:
                    background_image_css = ''
                    if p.background_image and '/ir.attachment/' in p.background_image:
                        background_image_css = "background-image: url('%s');" % env['website'].imagefield_hash('ir.attachment', 'datas', p.background_image[(p.background_image.index('ir.attachment/')+len('ir.attachment/')):p.background_image.index('/datas')].split('_')[0], 'theme_dermanord.dn_header_img')
                    tags_html = ''
                    if len(p.tag_ids) > 0:
                        for t in p.tag_ids:
                            tags_html += '<a href="' + '/blog/' + str(p.blog_id.id) + '/tag/' + str(t.id) + '"><span class="post_tag dn_uppercase" style="background: #000; padding: 10px; color: #fff; margin: 0px 10px 0px 0px;">' + t.name + '</span></a>'
                    blog_post_list.append({
                        'background_image_css': background_image_css,
                        'post_name': p.name,
                        'post_subtitle': p.subtitle,
                        'write_date': request.website.formatted_date(str(p.write_date)[:10]),
                        #~ 'main_object': p.blog_id.id,
                        'tags_html': tags_html,
                        #~ 'nav_list': self.nav_list(),
                        'post_url': '/blog/%s/post/%s' %(p.blog_id.id, p.id),
                        'str_read_more': str_read_more,
                        'str_tags': str_tags,
                    })
        return {'blog_posts': blog_post_list, 'page': page,}
