# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution, third party addon
#    Copyright (C) 2018- Vertel AB (<http://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning, AccessError
from openerp.addons.web import http
from openerp.http import request
import base64
import math
from openerp.addons.website_consumer_register.website import consumer_register

import logging
_logger = logging.getLogger(__name__)


class consumer_register(consumer_register):
   

    def get_address_type(self):
        res = super(consumer_register, self).get_address_type()
        
        return res + ['visit']
        _logger.warn('Haze dermanord res %s' % res)
        
        

    def consumer_fields(self):
        value = super(consumer_register, self).consumer_fields()
        
        return value + ['consumer_name'] + ['reseller_id']
        _logger.warn('Haze dermanord value %s' % value)

    def update_consumer_info(self, issue, post):
        super(consumer_register, self).update_consumer_info(issue, post)
        issue = request.env['project.issue'].sudo().browse(int(issue))
        commercial_partner = issue.partner_id.commercial_partner_id
        commercial_partner.geo_localize() # update geo location
        visit = commercial_partner.child_ids.filtered(lambda c: c.type == 'visit')
        if visit:
            visit[0].geo_localize() # update geo location
        if post.get('top_image'):
            commercial_partner.top_image = base64.encodestring(post.get('top_image').read())
        

    @http.route(['/consumer_register/information'], type='http', auth='public', website=True)
    def consumer_register_info(self, **post):
        return request.website.render('website_consumer_register_dermanord.consumer_register_info', {})

    #~ @http.route(['/reseller_register/contact/pw_reset'], type='json', auth='public', website=True)
    #~ def reseller_register_contact_pw_reset(self, user_id=0, partner_id=0, **kw):
        #~ _user = request.env['res.users'].sudo().browse(user_id)
        #~ company = _user.partner_id.commercial_partner_id
        #~ user = request.env['res.users'].sudo().search([('partner_id', '=', partner_id)])
        #~ try:
            #~ if not user:
                #~ raise Warning(_("Contact '%s' has no user.") % partner_id)
            #~ user.action_reset_password()
            #~ return _(u'Password reset has been sent to user %s by email') % user.name
        #~ except:
            #~ err = sys.exc_info()
            #~ error = ''.join(traceback.format_exception(err[0], err[1], err[2]))
            #~ _logger.exception(_('Cannot send mail to %s. Please check your mail server configuration.') % user.name)
            #~ return _('Cannot send mail to %s. Please check your mail server configuration.') % user.name
