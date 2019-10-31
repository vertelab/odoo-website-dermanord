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

from openerp import models, fields, api, _
# ~ from openerp1.exceptions import except_orm, Warning, RedirectWarning

import logging
_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    my_customer = fields.Boolean(string='My Customer', compute='_compute_my_customer', search='_search_my_customer')
    
    @api.multi
    def _compute_my_customer(self):
        pass
        # ~ parent = self.env.user.commercial_partner_id
        # ~ for partner in self:
            # ~ partner.my_customer = self.search_count([('id', '=', partner.id), ('commercial_partner_id.agents', 'child_of', parent.id)]) > 0
    
    @api.model
    def _search_my_customer(self, op, value):
        _logger.warn('op: %s\nvalue: %s\n%s\n%s' % (op, value, self.env.uid, self.env.context))
        # ~ assert value in (True, False, None), "Search for my_customer is only implemented for True, False and None values."
        # ~ assert op in ('=', '!='), "Search for my_customer is only implemented for '=' and '!=' operators."
        if op == '!=':
            value = not value
        domain = [('commercial_partner_id.agents.id', 'child_of', self.env.user.commercial_partner_id.id)]
        if not value:
            domain.insert(0, '!')
        _logger.warn(domain)
        return domain
    
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        if self.env.user.has_group('base.group_portal'):
            super(ResPartner, self.with_context(
                form_view_ref='sale_commission_dermanord.view_res_partner_form_agents',
                tree_view_ref='sale_commission_dermanord.view_res_partner_tree_agents',
                kanban_view_ref='sale_commission_dermanord.view_res_partner_kanban_agents'
            )).fields_view_get(view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        return super(ResPartner, self).fields_view_get(view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

# ~ class SaleOrder(models.Model):
    # ~ _inherit = 'sale.order'
    
    # ~ @api.model
    # ~ def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        # ~ if self.env.user.has_group('base.group_portal'):
            # ~ super(SaleOrder, self.with_context(
                # ~ form_view_ref='sale_commission_dermanord.view_res_partner_form_agents',
                # ~ tree_view_ref='sale_commission_dermanord.view_res_partner_tree_agents',
                # ~ kanban_view_ref='sale_commission_dermanord.view_res_partner_kanban_agents'
            # ~ )).fields_view_get(view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        # ~ super(SaleOrder, self).fields_view_get(view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
    
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        if self.env.user.has_group('base.group_portal'):
            super(AccountInvoice, self.with_context(
                form_view_ref='sale_commission_dermanord.invoice_form',
                tree_view_ref='sale_commission_dermanord.invoice_tree'
            )).fields_view_get(view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        return super(AccountInvoice, self).fields_view_get(view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        
