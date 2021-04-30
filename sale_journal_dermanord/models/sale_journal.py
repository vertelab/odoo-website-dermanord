# -*- coding: utf-8 -*-

from odoo import models, fields, api, http
from odoo.addons.website_sale_stock.controllers.variant import WebsiteSaleStockVariantController
import logging
_logger = logging.getLogger(__name__)


class sale_journal_invoice_type(models.Model):
    _name = 'sale_journal.invoice.type'
    _description = 'Invoice Types'

    name = fields.Char('Invoice Type', required=True)
    active = fields.Boolean('Active', help="If the active field is set to False, it will allow you to hide the invoice type without removing it.", default=True)
    note = fields.Text('Note')
    invoicing_method = fields.Selection([('simple', 'Non grouped'), ('grouped', 'Grouped')], 'Invoicing method', required=True, default='simple')

class res_partner(models.Model):
    _inherit = 'res.partner'

    property_invoice_type = fields.Many2one(
            comodel_name = 'sale_journal.invoice.type',
            string = "Invoicing Type",
            group_name = "Accounting Properties",
            company_dependent=True,
            help = "This invoicing type will be used, by default, to invoice the current partner.")

    def _commercial_fields(self, cr, uid, context=None):
        return super(res_partner, self)._commercial_fields(cr, uid, context=context) + ['property_invoice_type']


class picking(models.Model):
    _inherit = "stock.picking"

    invoice_type_id = fields.Many2one('sale_journal.invoice.type', 'Invoice Type', readonly=True)


# ~ class stock_move(models.Model):
    # ~ _inherit = "stock.move"

    # ~ def _action_confirm(self):
        # ~ """
            # ~ Pass the invoice type to the picking from the sales order
            # ~ (Should also work in case of Phantom BoMs when on explosion the original move is deleted, similar to carrier_id on delivery)
        # ~ """
        # ~ procs_to_check = []
        # ~ for move in self:
            # ~ _logger.warning(f"move: {move.read()}")
            # ~ if move.procurement_id and move.procurement_id.sale_line_id and move.procurement_id.sale_line_id.order_id.invoice_type_id:
                # ~ procs_to_check.append(move.procurement_id)
        # ~ res = super(stock_move, self)._action_confirm()
        # ~ pick_obj = self.env["stock.picking"]
        # ~ for proc in procs_to_check:
            # ~ pickings = list(set([x.picking_id.id for x in proc.move_ids if x.picking_id and not x.picking_id.invoice_type_id]))
            # ~ if pickings:
                # ~ pick_obj.write(pickings, {'invoice_type_id': proc.sale_line_id.order_id.invoice_type_id.id})
        # ~ return res


class sale(models.Model):
    _inherit = "sale.order"

    invoice_type_id = fields.Many2one('sale_journal.invoice.type', 'Invoice Type', help="Generate invoice based on the selected option.")

    def onchange_partner_id(self):
        result = super(sale, self).onchange_partner_id()
        if self.partner_id:
            itype = self.partner_id.property_invoice_type
            if itype:
                result['value']['invoice_type_id'] = itype.id
        return result
