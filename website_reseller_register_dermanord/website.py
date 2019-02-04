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
from openerp.addons.website_reseller_register.website import reseller_register

import logging
_logger = logging.getLogger(__name__)


class reseller_register(reseller_register):

    def get_address_type(self):
        res = super(reseller_register, self).get_address_type()
        return res + ['visit']

    def company_fields(self):
        value = super(reseller_register, self).company_fields()
        return value + ['brand_name', 'street', 'street2', 'zip', 'city', 'country_id', 'phone', 'email', 'is_reseller']

    def update_partner_info(self, issue, post):
        super(reseller_register, self).update_partner_info(issue, post)
        issue = request.env['project.issue'].sudo().browse(int(issue))
        commercial_partner = issue.partner_id.commercial_partner_id
        commercial_partner.geo_localize() # update geo location
        visit = commercial_partner.child_ids.filtered(lambda c: c.type == 'visit')
        if visit:
            visit[0].geo_localize() # update geo location
        if post.get('top_image'):
            commercial_partner.top_image = base64.encodestring(post.get('top_image').read())
        for weekday in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
            self.update_opening_weekday(commercial_partner, weekday, post)
        if post.get('opening_hours_exceptions') != None and post.get('opening_hours_exceptions') != issue.partner_id.sudo().opening_hours_exceptions:
            commercial_partner.sudo().opening_hours_exceptions = post.get('opening_hours_exceptions')

    def update_opening_weekday(self, partner, weekday, post):
        day = partner.opening_hours_ids.filtered(lambda o: o.dayofweek == weekday)
        if not day:
            day = request.env['opening.hours'].sudo().create({'partner_id': partner.id, 'dayofweek': weekday})
        day.open_time = self.get_time_float(post.get('%s_open_time' %weekday) or '0.0')
        day.close_time = self.get_time_float(post.get('%s_close_time' %weekday) or '0.0')
        day.break_start = self.get_time_float(post.get('%s_break_start' %weekday) or '0.0')
        day.break_stop = self.get_time_float(post.get('%s_break_stop' %weekday) or '0.0')
        day.close = True if post.get('%s_close' %weekday) == '1' else False

    def get_time_float(self, time):
        return (math.floor(float(time)) + (float(time)%1)/0.6) if time else 0.0

    def get_company_post(self, post):
        value = super(reseller_register, self).get_company_post(post)
        value.update({
            'brand_name': post.get('company_brand_name'),
            'phone': post.get('company_phone'),
            'email': post.get('company_email'),
            'website': post.get('company_website'),
            'street': post.get('company_street'),
            'street2': post.get('company_street2'),
            'zip': post.get('company_zip'),
            'city': post.get('company_city'),
            'is_reseller': True if post.get('company_is_reseller') else False,
        })
        return value

    def get_help(self):
        value = super(reseller_register, self).get_help()
        value['help_company_brand_name'] = _('')
        value['help_company_phone'] = _('')
        value['help_company_email'] = _('')
        value['help_company_website'] = _('')
        value['help_company_street'] = _('')
        value['help_company_street2'] = _('')
        value['help_company_zip'] = _('')
        value['help_company_city'] = _('')
        value['help_visit_street'] = _("If the street is not filled in, your salon will not appear in reseller searching.")
        value['help_visit_street2'] = _('')
        value['help_visit_zip'] = _('')
        value['help_visit_city'] = _('')
        value['help_visit_phone'] = _('')
        value['help_visit_email'] = _('')
        value['help_top_image'] = _('This image will be shown for end consumers on our list of resellers')
        value['help_top_image_size'] = _('Notice: This image will be cut to 1366x450 px.')
        return value

    @http.route(['/reseller_register/information'], type='http', auth='public', website=True)
    def reseller_register_info(self, **post):
        return request.website.render('website_reseller_register_dermanord.reseller_register_info', {})

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
