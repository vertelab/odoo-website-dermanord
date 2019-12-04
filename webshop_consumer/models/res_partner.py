# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2017- Vertel AB (<http://vertel.se>).
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


class res_partner(models.Model):
    _inherit = 'res.partner'
    
    customer_ids = fields.One2many(comodel_name='res.partner', string='Customer', inverse_name='reseller_id')
    reseller_id = fields.Many2one(comodel_name='res.partner', string='Reseller')
    
    customer_ids_count = fields.Integer(compute='reseller_clients_count')
    
    @api.multi
    def reseller_clients_count(self):
        for partner in self:
            partner.customer_ids_count = len(partner.customer_ids)

    @api.multi
    def action_consumer_list(self):
        return {
            'name': 'Kundernas kunder / %s' % self.name ,
            'res_model': 'res.partner',
            'type': 'ir.actions.act_window',
            'view_mode': 'kanban,tree,form',
            'view_type': 'kanban,tree,form',
            'domain': [('id', 'in', self.customer_ids.mapped('id'))],
            'context': {'default_reseller_id': self.id },
        }
