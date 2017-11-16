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


class Event(models.Model):
    _inherit = 'event.event'

    @api.multi
    def google_map_img(self, zoom=8, width=298, height=298):
        _logger.warn('google_map_img')
        if self.sudo().address_id:
            return self.sudo().address_id.google_map_img(
                zoom=zoom, width=width, height=height, marker={
                'icon': self.env['ir.config_parameter'].get_param(
                    'dermanord_map_marker',
                    'http://wiggum.vertel.se/dn_maps_marker.png'),
            })
        return None
