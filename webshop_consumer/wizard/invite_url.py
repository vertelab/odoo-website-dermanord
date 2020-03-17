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

    # ~ [3859] ÅF sälja till slutkonsument - Länk för att addera kund till ÅF
    # ~ kund_id = #5522
    # ~ maria:8069/sv_SE/reseller/5522/consumer
    @api.model
    def _invite_url(self):

        partner_id = self.env['res.partner'].browse( self._context.get('active_id', []) )
        _logger.warn("partner_id: %s" % partner_id)
        _logger.warn("partner_id.is_reseller: %s" % partner_id.is_reseller)
        _logger.warn("context.get: %s" % self._context.get('active_id', []))

        if partner_id.is_reseller:
            return '%s/reseller/%s/consumer/' % ( self.env['ir.config_parameter'].sudo().get_param('web.base.url'), partner_id.id )

        else:
            return u'Oj...! Rubriken \'Sökbar ÅF på webbsidan\' mmåste vara markerad!'

    invite_url_field = fields.Char(string='Invite URL', default=_invite_url, help='Invite URL, for consumers' )
