# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2004-2018 Vertel AB (<http://vertel.se>).
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

from openerp import models, fields, api
from openerp.addons.website_sale.models.payment import PaymentTransaction as WebsiteSalePaymentTransaction
from openerp.tools import float_compare
import traceback

import logging
_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    @api.model
    def form_feedback(self, data, acquirer_name):
        tx = None
        # We need to skip the code that gets executed in website_sale.
        # This is accomplished by importing PaymentTransaction from website_sale and performing super on it.
        # The super below will jump straight the code from payment (as things stand today).
        # This might break in new and exciting ways if we add more modules that override form_feedback.
        res = super(WebsiteSalePaymentTransaction, self).form_feedback(data, acquirer_name)
        
        def log_outcome(order, message, subject=u"Order ej godkänd automatiskt"):
            order.message_post(body=message.replace('\n', '<br/>'), subject=subject, type='comment')
        
        def send_email(subject, body, email_to='sales@dermanord.se'):
            author = self.env.ref('base.partner_root').sudo()
            self.env['mail.mail'].sudo().create({
                'subject': subject,
                'body_html': body.replace('\n', '<br/>'),
                'author_id': author.id,
                'email_from': author.email,
                'type': 'email',
                'auto_delete': True,
                'email_to': email_to,
            })
        
        # fetch the tx, check its state, confirm the potential SO
        try:
            tx_find_method_name = '_%s_form_get_tx_from_data' % acquirer_name
            if hasattr(self, tx_find_method_name):
                tx = getattr(self, tx_find_method_name)(data)
            _logger.info('<%s> transaction processed: tx ref:%s, tx amount: %s', acquirer_name, tx.reference if tx else 'n/a', tx.amount if tx else 'n/a')
            if tx and tx.sale_order_id:
                order = tx.sale_order_id
                # verify SO/TX match, excluding tx.fees which are currently not included in SO
                amount_matches = (order.state in ['draft', 'sent'] and float_compare(tx.amount, order.amount_total, 2) == 0)
                if amount_matches:
                    if tx.state == 'done':
                        _logger.info('<%s> transaction completed, confirming order %s (ID %s)', acquirer_name, order.name, order.id)
                        prepay = self.env.ref('account:5246172e-b698-11e0-9d76-12313b063acc.account_payment_term-A8mv0J2HfLvs')
                        sale_team = self.env.ref('website.salesteam_website_sales')
                        msg = []
                        warnings = []
                        if order.payment_term == prepay:
                            msg.append(u"Betalningsvillkor är %s." % prepay.name)
                        if order.section_id != sale_team:
                            msg.append(u"Säljlag ej satt till %s." % sale_team.name)
                        if order.note:
                            msg.append(u"Ordern har en kommentar.")
                        if order.partner_id.sale_warn in ('warning', 'block'):
                            msg.append(u"Kunden har en varning:\n%s\n" % order.partner_id.sale_warn_msg)
                            warnings.append((order.partner_id.sale_warn_msg, u"Kunden har en varning"))
                        elif order.partner_id.commercial_partner_id.sale_warn in ('warning', 'block'):
                            msg.append(u"Kunden har en varning:\n%s\n" % order.partner_id.commercial_partner_id.sale_warn_msg)
                            warnings.append((order.partner_id.commercial_partner_id.sale_warn_msg, u"Kunden har en varning"))
                        for product in order.order_line.filtered(lambda l: l.product_id and l.product_id.sale_line_warn in ('warning', 'block')).mapped('product_id'):
                            msg.append(u"%s har en varning:\n%s\n" % (product.display_name, product.sale_line_warn_msg))
                            warnings.append((product.sale_line_warn_msg, u"%s har en varning" % product.display_name))
                        try:
                            order.check_order_stock()
                        except Exception as e:
                            msg.append('\n%s' % e.message)
                        if msg or warnings:
                            order.state = 'sent'
                            if msg:
                                log_outcome(order, u'\n'.join(msg))
                            for w in warnings:
                                log_outcome(order, *w)
                            return res
                        order.with_context(send_email=True).action_button_confirm()
                        for picking in order.picking_ids:
                            picking.action_assign()
          
                            if picking.state == 'assigned':
                               picking.ready4picking = True
                            else:
                                subject = u" %s är ej redo för leverans" % picking.name
                                action = self.env.ref('stock.action_picking_tree_waiting')
                                body = u"""<a href="%s/web#id=%s&view_type=form&model=stock.picking&action=%s&active_id=2">%s</a>""" % (self.env['ir.config_parameter'].get_param('web.base.url'), picking.id, action.id, picking.name)
                                send_email(subject, body)
                    elif tx.state != 'cancel' and order.state == 'draft':
                        _logger.info('<%s> transaction pending, sending quote email for order %s (ID %s)', acquirer_name, order.name, order.id)
                        log_outcome(order, u"Betalningstransaktionens status är inte 'done' eller 'cancel': '%s'." % tx.state)
                        order.sudo().force_quotation_send()
                    else:
                        log_outcome(order, u"Betalningstransaktionens status är inte 'done': '%s'." % tx.state)
                else:
                    msg = '<%s> transaction MISMATCH for order %s (ID %s)' % (acquirer_name, order.name, order.id)
                    _logger.warning(msg)
                    log_outcome(order, msg)
                    send_email(u"Fel vid ordererkännande", msg)
        except Exception:
            msg = u'Misslyckades att bekräfta order eller skicka orderbekräftelse%s. Kunden har meddelats att ordern är godkänd.\n\n%s' % (tx and u' för transaktionen %s' % tx.reference or '', traceback.format_exc())
            _logger.exception(msg)
            log_outcome(order, msg)
            send_email(u"Fel vid ordererkännande", msg)
        return res
