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

from openerp import models, fields, api, http, _
from openerp.http import request
import logging
_logger = logging.getLogger(__name__)

#~ class website(models.Model):
    #~ _inherit = 'website'

    #~ @api.model
    #~ def get_id_from_url(self, url):
        #~ _logger.warn('Haojun')
        #~ pass


class newsDermanord(http.Controller):

    @http.route(['/news', '/news/page/<model("blog.post"):page>','/news/tagg/<model("blog.tag"):tag>'], type='http', auth="public", website=True)
    def repord(self, **post,page=None,tag=None):
        return request.website.render("news_dermanord.page", {'tag': tag, 'page': page})
        
class BlogTag(models.Model):
    _inherit = 'blog.tag'

    background_image = fields.Binary(string='Background Image',)
