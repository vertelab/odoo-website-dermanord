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

import logging
_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    # /addons/website/models/website.py
    #~ def google_map_img(self, cr, uid, ids, zoom=8, width=298, height=298, context=None):
        #~ partner = self.browse(cr, uid, ids[0], context=context)
        #~ params = {
            #~ 'center': '%s, %s %s, %s' % (partner.street or '', partner.city or '', partner.zip or '', partner.country_id and partner.country_id.name_get()[0][1] or ''),
            #~ 'size': "%sx%s" % (height, width),
            #~ 'zoom': zoom,
            #~ 'sensor': 'false',
        #~ }
        #~ return urlplus('//maps.googleapis.com/maps/api/staticmap' , params)
