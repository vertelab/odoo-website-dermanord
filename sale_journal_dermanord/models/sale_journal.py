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
    _logger.warning("G"*999)

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


class stock_move(models.Model):
    _inherit = "stock.move"

    def action_confirm(self, cr, uid, ids, context=None):
        """
            Pass the invoice type to the picking from the sales order
            (Should also work in case of Phantom BoMs when on explosion the original move is deleted, similar to carrier_id on delivery)
        """
        procs_to_check = []
        for move in self.browse(cr, uid, ids, context=context):
            if move.procurement_id and move.procurement_id.sale_line_id and move.procurement_id.sale_line_id.order_id.invoice_type_id:
                procs_to_check += [move.procurement_id]
        res = super(stock_move, self).action_confirm(cr, uid, ids, context=context)
        pick_obj = self.pool.get("stock.picking")
        for proc in procs_to_check:
            pickings = list(set([x.picking_id.id for x in proc.move_ids if x.picking_id and not x.picking_id.invoice_type_id]))
            if pickings:
                pick_obj.write(cr, uid, pickings, {'invoice_type_id': proc.sale_line_id.order_id.invoice_type_id.id}, context=context)
        return res


class sale(models.Model):
    _inherit = "sale.order"

    invoice_type_id = fields.Many2one('sale_journal.invoice.type', 'Invoice Type', help="Generate invoice based on the selected option.")

    def onchange_partner_id(self, cr, uid, ids, part, context=None):
        result = super(sale, self).onchange_partner_id(cr, uid, ids, part, context=context)
        if part:
            itype = self.pool.get('res.partner').browse(cr, uid, part, context=context).property_invoice_type
            if itype:
                result['value']['invoice_type_id'] = itype.id
        return result
