# -*- coding: utf-8 -*-

from openerp import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def invoice_validate(self):
        # fetch the partner's id and subscribe the partner to the invoice
        res = super(AccountInvoice, self).invoice_validate()
        for invoice in self:
            if invoice.invoice_type_id == self.env.ref("invoice_type.invoice_webshop") and invoice.move_lines:
                invoice.move_lines.write({'blocked': True})
        return res


class mail_compose_message(models.Model):
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail(self):
        context = self._context
        if context.get('default_model') == 'account.invoice' and \
                context.get('default_res_id') and context.get('mark_invoice_as_sent'):
            # Hopefully no customer has WSSO in their name...
            invoice = self.env['account.invoice'].browse(context['default_res_id'])
            if invoice.invoice_type_id == self.env.ref("invoice_type.invoice_webshop"):
                return
            invoice = invoice.with_context(mail_post_autofollow=True)
            invoice.write({'sent': True})
            invoice.message_post(body=_("Invoice sent"))
        return super(mail_compose_message, self).send_mail()
