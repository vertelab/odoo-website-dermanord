# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2016- Vertel AB (<http://vertel.se>).
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

import openerp.exceptions
from openerp.exceptions import except_orm, Warning, RedirectWarning,MissingError
from openerp import models, fields, api, _

import logging
_logger = logging.getLogger(__name__)


class invite_url_wizard(models.TransientModel):
    _name = "consumer.invite.url"
    
    invite_url_field = fields.Char(string='Invite URL, for consumers', compute='create_invite_url')

    # ~ [3859] ÅF sälja till slutkonsument - Länk för att addera kund till ÅF
    # ~ skogsrospa = #5522
    # ~ maria:8069/sv_SE/reseller/5522/consumer
    @api.one
    def create_invite_url(self):
        company_id = self._context.get('partner_id')

        if company_id.is_reseller:
            self.invite_url_field = '/reseller/%s/consumer/' % (company_id.id )
        else:
            self.invite_url_field = u'Hoppla! Sökbar ÅF på webbsidan ska vara markerad!'
