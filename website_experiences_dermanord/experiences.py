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

from openerp import models, fields, api, _
from openerp import http
from openerp.http import request

import logging
_logger = logging.getLogger(__name__)

class BlogTag(models.Model):
    _inherit = 'blog.tag'
    
    experience = fields.Boolean(string='Is Experience', help="Show blog posts with this tag as an experience on the website.")
    sequence = fields.Integer('Sequence')

class ExperiencesController(http.Controller):
    
    @http.route('/experiences', auth="public", website=True)
    def experiences(self, **post):
        return http.request.render('website_experiences_dermanord.experiences', {})
    
    @http.route('/experiences/<model("blog.post"):blog_post>', auth="public") #????
    def experiences(self, **post):
        pass
    
    @http.route('/experiences/json/get_experiences', type='json', auth="public", website=True)
    def experiences(self, **post):    
        tags = env['blog.tag'].search([('experience', '=', True)], order="sequence")
        res = []
        exp_blog = env.ref('website_experience_dermanord')
        for tag in tags:
            blog_posts = env['blog.post'].search([('tag_ids', '=', tag.id), ('blog_id', '=', exp_blog.id), ('website_published', '=', True)])
            res.append({
                'id': tag.id,
                'name': tag.name,
                'posts': [{'id': p.id, 'name': p.name, 'image': p.background_image} for p in blog_posts]
            })
    
    
    
    
        
        
