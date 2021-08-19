# -*- coding: utf-8 -*-

from openerp import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class mail_compose_message(models.Model):
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail(self):
        context = self._context
        if context.get('default_model') == 'account.invoice' and \
                context.get('default_res_id') and context.get('mark_invoice_as_sent'):
            # Hopefully no customer has WSSO in their name...
            if 'WSSO' not in invoice.name:
                invoice = self.env['account.invoice'].browse(context['default_res_id'])
                invoice = invoice.with_context(mail_post_autofollow=True)
                invoice.write({'sent': True})
                invoice.message_post(body=_("Invoice sent"))
        return super(mail_compose_message, self).send_mail()