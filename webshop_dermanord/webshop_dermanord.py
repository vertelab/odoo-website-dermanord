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

class blog_post(models.Model):
    _inherit = 'blog.post'

    product_public_categ_ids = fields.Many2many(comodel_name='product.public.category', string='Product Public Categories')
    product_tmpl_ids = fields.Many2many(comodel_name='product.template', string='Product Templates')


class product_template(models.Model):
    _inherit = 'product.template'

    @api.one
    def _blog_post_ids(self):
        if type(self.id) is int:
            blog_posts = self.env['blog.post'].search_read(['&', ('website_published', '=', True),'|', ('product_tmpl_ids', 'in', self.id), ('product_public_categ_ids', 'in', self.public_categ_ids.mapped('id'))],['id'])
            self.blog_post_ids = [(6, 0, [p['id'] for p in blog_posts])]
            #~ self.blog_post_ids = [(6, 0, blog_posts.filtered(lambda b: b.website_published == True).mapped('id'))]
    blog_post_ids = fields.Many2many(comodel_name='blog.post', string='Posts', compute='_blog_post_ids')
