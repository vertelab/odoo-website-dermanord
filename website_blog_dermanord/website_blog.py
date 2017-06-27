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
from openerp.addons.website_blog.controllers.main import WebsiteBlog
from openerp.addons.website.models.website import slug
from openerp.osv.orm import browse_record
import werkzeug

import logging
_logger = logging.getLogger(__name__)

class Blog(models.Model):
    _inherit = 'blog.blog'

    post_short = fields.Many2one(comodel_name='ir.ui.view', string='Post Short')
    post_complete = fields.Many2one(comodel_name='ir.ui.view', string='Post Complete')


class QueryURL(object):
    def __init__(self, path='', path_args=None, **args):
        self.path = path
        self.args = args
        self.path_args = set(path_args or [])

    def __call__(self, path=None, path_args=None, **kw):
        path = path or self.path
        for k, v in self.args.items():
            kw.setdefault(k, v)
        path_args = set(path_args or []).union(self.path_args)
        paths, fragments = [], []
        for key, value in kw.items():
            if value and key in path_args:
                if isinstance(value, browse_record):
                    paths.append((key, slug(value)))
                else:
                    paths.append((key, value))
            elif value:
                if isinstance(value, list) or isinstance(value, set):
                    fragments.append(werkzeug.url_encode([(key, item) for item in value]))
                else:
                    fragments.append(werkzeug.url_encode([(key, value)]))
        for key, value in paths:
            path += '/' + key + '/%s' % value
        if fragments:
            path += '?' + '&'.join(fragments)
        return path


class WebsiteBlog(WebsiteBlog):

    @http.route([
        '/blog/<model("blog.blog"):blog>',
        '/blog/<model("blog.blog"):blog>/page/<int:page>',
        '/blog/<model("blog.blog"):blog>/tag/<model("blog.tag"):tag>',
        '/blog/<model("blog.blog"):blog>/tag/<model("blog.tag"):tag>/page/<int:page>',
    ], type='http', auth="public", website=True)
    def blog(self, blog=None, tag=None, page=1, **opt):
        date_begin, date_end = opt.get('date_begin'), opt.get('date_end')

        cr, uid, context = request.cr, request.uid, request.context
        blog_post_obj = request.registry['blog.post']

        blog_obj = request.registry['blog.blog']
        blog_ids = blog_obj.search(cr, uid, [], order="create_date asc", context=context)
        blogs = blog_obj.browse(cr, uid, blog_ids, context=context)

        domain = []
        if blog:
            domain += [('blog_id', '=', blog.id)]
        if tag:
            domain += [('tag_ids', 'in', tag.id)]
        if date_begin and date_end:
            domain += [("create_date", ">=", date_begin), ("create_date", "<=", date_end)]

        blog_url = QueryURL('', ['blog', 'tag'], blog=blog, tag=tag, date_begin=date_begin, date_end=date_end)
        post_url = QueryURL('', ['blogpost'], tag_id=tag and tag.id or None, date_begin=date_begin, date_end=date_end)

        blog_post_ids = blog_post_obj.search(cr, uid, domain, order="create_date desc", context=context)
        blog_posts = blog_post_obj.browse(cr, uid, blog_post_ids, context=context)

        pager = request.website.pager(
            url=request.httprequest.path.partition('/page/')[0],
            total=len(blog_posts),
            page=page,
            step=self._blog_post_per_page,
            url_args=opt,
        )
        pager_begin = (page - 1) * self._blog_post_per_page
        pager_end = page * self._blog_post_per_page
        blog_posts = blog_posts[pager_begin:pager_end]

        tags = blog.all_tags()[blog.id]

        values = {
            'blog': blog,
            'blogs': blogs,
            'main_object': blog,
            'tags': tags,
            'tag': tag,
            'blog_posts': blog_posts,
            'pager': pager,
            'nav_list': self.nav_list(),
            'blog_url': blog_url,
            'post_url': post_url,
            'date': date_begin,
        }
        if blog.post_short:
            try:
                return request.website.render(blog.post_short.id, values)
            except:
                _logger.error('Cannot reder template %s' %blog.post_short.name)
        else:
            return request.website.render("website_blog.blog_post_short", values)


    @http.route([
            '''/blog/<model("blog.blog"):blog>/post/<model("blog.post", "[('blog_id','=',blog[0])]"):blog_post>''',
    ], type='http', auth="public", website=True)
    def blog_post(self, blog, blog_post, tag_id=None, page=1, enable_editor=None, **post):
        cr, uid, context = request.cr, request.uid, request.context
        tag_obj = request.registry['blog.tag']
        blog_post_obj = request.registry['blog.post']
        date_begin, date_end = post.get('date_begin'), post.get('date_end')

        pager_url = "/blogpost/%s" % blog_post.id

        pager = request.website.pager(
            url=pager_url,
            total=len(blog_post.website_message_ids),
            page=page,
            step=self._post_comment_per_page,
            scope=7
        )
        pager_begin = (page - 1) * self._post_comment_per_page
        pager_end = page * self._post_comment_per_page
        comments = blog_post.website_message_ids[pager_begin:pager_end]

        tag = None
        if tag_id:
            tag = request.registry['blog.tag'].browse(request.cr, request.uid, int(tag_id), context=request.context)
        post_url = QueryURL('', ['blogpost'], blogpost=blog_post, tag_id=tag_id, date_begin=date_begin, date_end=date_end)
        blog_url = QueryURL('', ['blog', 'tag'], blog=blog_post.blog_id, tag=tag, date_begin=date_begin, date_end=date_end)

        if not blog_post.blog_id.id == blog.id:
            return request.redirect("/blog/%s/post/%s" % (slug(blog_post.blog_id), slug(blog_post)))

        tags = tag_obj.browse(cr, uid, tag_obj.search(cr, uid, [], context=context), context=context)

        all_post_ids = blog_post_obj.search(cr, uid, [('blog_id', '=', blog.id)], context=context)
        current_blog_post_index = all_post_ids.index(blog_post.id)
        next_post_id = all_post_ids[0 if current_blog_post_index == len(all_post_ids) - 1 \
                            else current_blog_post_index + 1]
        next_post = next_post_id and blog_post_obj.browse(cr, uid, next_post_id, context=context) or False

        values = {
            'tags': tags,
            'tag': tag,
            'blog': blog,
            'blog_post': blog_post,
            'main_object': blog_post,
            'nav_list': self.nav_list(),
            'enable_editor': enable_editor,
            'next_post': next_post,
            'date': date_begin,
            'post_url': post_url,
            'blog_url': blog_url,
            'pager': pager,
            'comments': comments,
        }

        request.session[request.session_id] = request.session.get(request.session_id, [])
        if not (blog_post.id in request.session[request.session_id]):
            request.session[request.session_id].append(blog_post.id)
            # Increase counter
            blog_post_obj.write(cr, SUPERUSER_ID, [blog_post.id], {
                'visits': blog_post.visits+1,
            },context=context)
        if blog.post_complete:
            try:
                return request.website.render(blog.post_complete.id, values)
            except:
                _logger.error('Cannot reder template %s' %blog.post_complete.name)
        else:
            return request.website.render("website_blog.blog_post_complete", values)
