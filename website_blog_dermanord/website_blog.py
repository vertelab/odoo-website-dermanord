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
from openerp import SUPERUSER_ID
import werkzeug

import logging
_logger = logging.getLogger(__name__)


class website(models.Model):
    _inherit = 'website'

    @api.model
    def formatted_date(self, date):
        year = date[:4]
        month = date[5:7]
        day = date[8:]
        if month == '01':
            month = _('January')
        if month == '02':
            month = _('February')
        if month == '03':
            month = _('Mars')
        if month == '04':
            month = _('April')
        if month == '05':
            month = _('May')
        if month == '06':
            month = _('June')
        if month == '07':
            month = _('July')
        if month == '08':
            month = _('August')
        if month == '09':
            month = _('September')
        if month == '10':
            month = _('October')
        if month == '11':
            month = _('November')
        if month == '12':
            month = _('December')
        return '%s %s %s' %(day, month, year)


class blog_post_product(models.Model):
    _name = 'blog.post.product'
    _order = 'sequence'

    sequence = fields.Integer()
    blog_post_id = fields.Many2one(comodel_name="blog.post")
    product_id = fields.Many2one(comodel_name="product.template")
    name = fields.Char(related='product_id.name')
    default_code = fields.Char(related='product_id.default_code')
    type = fields.Selection(related='product_id.type')
    list_price = fields.Float(related='product_id.list_price')
    qty_available = fields.Float(related='product_id.qty_available')
    virtual_available = fields.Float(related='product_id.virtual_available')


class Blog(models.Model):
    _inherit = 'blog.blog'

    post_short = fields.Many2one(comodel_name='ir.ui.view', string='Post Short')
    post_complete = fields.Many2one(comodel_name='ir.ui.view', string='Post Complete')
    post_content = fields.Html(string='Post Content')


class BlogPost(models.Model):
    _inherit = 'blog.post'

    def check_access_rule(self, cr, uid, ids, operation, context=None):
        """Verifies that the operation given by ``operation`` is allowed for the user
           according to ir.rules.

           :param operation: one of ``write``, ``unlink``
           :raise except_orm: * if current ir.rules do not permit this operation.
           :return: None if the operation is allowed
        """
        if uid == SUPERUSER_ID:
            return

        if self.is_transient():
            # Only one single implicit access rule for transient models: owner only!
            # This is ok to hardcode because we assert that TransientModels always
            # have log_access enabled so that the create_uid column is always there.
            # And even with _inherits, these fields are always present in the local
            # table too, so no need for JOINs.
            cr.execute("""SELECT distinct create_uid
                          FROM %s
                          WHERE id IN %%s""" % self._table, (tuple(ids),))
            uids = [x[0] for x in cr.fetchall()]
            if len(uids) != 1 or uids[0] != uid:
                raise except_orm(_('Access Denied'),
                                 _('For this kind of document, you may only access records you created yourself.\n\n(Document type: %s)') % (self._description,))
        else:
            where_clause, where_params, tables = self.pool.get('ir.rule').domain_get(cr, uid, self._name, operation, context=context)
            if where_clause:
                where_clause = ' and ' + ' and '.join(where_clause)
                for sub_ids in cr.split_for_in_conditions(ids):
                    cr.execute('SELECT ' + self._table + '.id FROM ' + ','.join(tables) +
                               ' WHERE ' + self._table + '.id IN %s' + where_clause,
                               [sub_ids] + where_params)
                    res = cr.dictfetchall()
                    _logger.warn(res)
                    returned_ids = [x['id'] for x in res]
                    self._check_record_rules_result_count(cr, uid, sub_ids, returned_ids, operation, context=context)

    product_ids = fields.Many2many(comodel_name='product.template', relation="blog_post_product", column1='blog_post_id',column2='product_id', string='Products')
    blog_post_product_ids = fields.One2many(comodel_name='blog.post.product', inverse_name='blog_post_id', string='Products')
    object_ids = fields.One2many(comodel_name='blog.post.object', inverse_name='blog_post_id', string='Objects')
    related_posts = fields.Many2many(comodel_name='blog.post', compute='_related_posts')

    @api.one
    def _related_posts(self):
        blog_posts = self.browse()
        for post in self.search([('blog_id', '=', self.blog_id.id), ('id', '!=', self.id), ('website_published', '=', True)]):
            if post.tag_ids == self.tag_ids:
                blog_posts |= post
                _logger.warn(post.background_image)
        self.related_posts = blog_posts[:4] if len(blog_posts) > 4 else blog_posts

    @api.one
    def update_blog_post_product_ids(self):
        self.env['blog.post.product'].search([('blog_post_id', '=', self.id)]).unlink()
        for o in self.object_ids.sorted(lambda o: o.sequence):
            _logger.error(getattr(o, 'create_blog_post_product', False))
            if getattr(o, 'create_blog_post_product', False):
                o.create_blog_post_product(self)

    @api.model
    def create(self, vals):
        blog = self.env['blog.blog'].browse(int(vals.get('blog_id', 0)))
        if blog and blog.post_content:
            vals['content'] = blog.post_content
        return super(BlogPost, self).create(vals)


class product_template(models.Model):
    _inherit = 'product.template'

    blog_post_ids = fields.Many2many(comodel_name='blog.post', relation="blog_post_product", column1='product_id', column2='blog_post_id',string='Blog Posts')

    @api.multi
    def write(self, vals):
        res = super(product_template, self).write(vals)
        if 'access_group_ids' in vals:
            objects = self.env['blog.post.object'].search(['|' for i in range(len(self) - 1)] + [('object_id', '=', 'product.template,%s'% p.id) for p in self])
            if objects:
                objects.write({'access_group_ids': vals['access_group_ids']})
        return res

class product_product(models.Model):
    _inherit = 'product.product'

    @api.multi
    def write(self, vals):
        res = super(product_product, self).write(vals)
        if 'access_group_ids' in vals:
            objects = self.env['blog.post.object'].search(['|' for i in range(len(self) - 1)] + [('object_id', '=', 'product.product,%s'% p.id) for p in self])
            if objects:
                objects.write({'access_group_ids': vals['access_group_ids']})
        return res


class blog_post_object(models.Model):
    _name = 'blog.post.object'
    _order = 'blog_post_id, sequence, name'

    name = fields.Char(string='Name')
    description = fields.Text(string='Description')
    image = fields.Binary(string='Image')
    sequence = fields.Integer()
    color = fields.Integer('Color Index')
    blog_post_id = fields.Many2one(comodel_name='blog.post', string='Blog Posts')
    object_id = fields.Reference(selection=[('product.template', 'Product Template'), ('product.product', 'Product Variant')],no_open=True,no_create=1, no_create_edit=1)
    access_group_ids = fields.Many2many(comodel_name='res.groups', string='Access Groups', help='Allowed groups to access this object')

    @api.one
    @api.onchange('object_id')
    def get_object_value(self):
        _logger.warn('fuelds: %s | %s' % (self.object_id.__dict__.keys(),self.object_id._search))
        if self.object_id:
            if self.object_id._name == 'product.template' or self.object_id._name == 'product.product':
                self.name = self.object_id.name
                self.description = self.object_id.description_sale
                self.image = self.object_id.image
                self.access_group_ids = self.object_id.access_group_ids

    @api.one
    def create_blog_post_product(self, post):
        if self.object_id._name == 'product.template':
            self.env['blog.post.product'].create({
                'blog_post_id': post.id,
                'product_id': self.object_id.id,
                'sequence': len(post.product_ids) + 1,
            })
        elif self.object_id._name == 'product.product':
            self.env['blog.post.product'].create({
                'blog_post_id': post.id,
                'product_id': self.object_id.product_tmpl_id.id,
                'sequence': len(post.product_ids) + 1,
            })
        #~ elif self.object_id._name == 'product.public.category':
            #~ for product in self.env['product.template'].search([('public_categ_ids', 'in', self.object_id.id)]):
                #~ self.env['blog.post.product'].create({
                    #~ 'blog_post_id': post.id,
                    #~ 'product_id': product.id,
                    #~ 'sequence': len(post.product_ids) + 1,
                #~ })
        else:
            pass


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
            domain += [('tag_ids', '=', tag.id)]
        if date_begin and date_end:
            domain += [("create_date", ">=", date_begin), ("create_date", "<=", date_end)]

        blog_url = QueryURL('', ['blog', 'tag'], blog=blog, tag=tag, date_begin=date_begin, date_end=date_end)
        post_url = QueryURL('', ['blogpost'], tag_id=tag and tag.id or None, date_begin=date_begin, date_end=date_end)
        _logger.warn(domain)
        blog_post_ids = blog_post_obj.search(cr, uid, domain, order="create_date desc", context=context)
        _logger.warn(blog_post_ids)
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
        _logger.warn(blog_posts)
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
            #~ try:
            return request.website.render(blog.post_complete.id, values)
            #~ except:
                #~ _logger.error('Cannot reder template %s' %blog.post_complete.name)
                
        else:
            #~ if (blog_post.security_type == 'private' and request.env['res.users'].browse(uid) in blog_post.group_ids.mapped('users')) or blog_post.security_type == 'public':
            return request.website.render("website_blog.blog_post_complete", values)
            #~ else:
                #~ return request.website.render('website.403')
