# -*- coding: utf-8 -*-

from openerp import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class stock_picking(models.Model):
    _inherit = 'stock.picking'

    @api.one
    def _compute_is_reseller(self):
        if self.partner_id and self.partner_id.commercial_partner_id.access_group_ids.filtered(lambda r: r.id == self.env.ref("__export__.res_groups_283").id):
            self.is_reseller = True
        else:
            self.is_reseller = False

    is_reseller = fields.Boolean(
        string="For Reseller", help="Displays if the end customer is a reseller or not", compute='_compute_is_reseller')
