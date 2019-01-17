# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2017 Vertel AB (<http://vertel.se>).
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

import logging
_logger = logging.getLogger(__name__)

class WebsiteErrorLog(models.Model):
    _inherit = 'website.error.log'

    access_group_ids = fields.Many2many(comodel_name='res.groups', string='Groups')

    @api.model
    def get_error_values(self, request, response, code, values, website):
        res = super(WebsiteErrorLog, self).get_error_values(request, response, code, values, website)
        res['access_group_ids'] =  [(6, 0, [g.id for g in request.env.user.commercial_partner_id.access_group_ids])]
        return res
