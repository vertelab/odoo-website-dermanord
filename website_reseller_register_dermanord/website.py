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
        if post.get('top_image'):
            issue.partner_id.top_image = base64.encodestring(post.get('top_image').read())
        if post.get('remove_img') and post.get('remove_img') == '1':
            issue.partner_id.top_image = None
        if post.get('monday_open_time'):
            monday = issue.partner_id.sudo().opening_hours_ids.filtered(lambda o: o.dayofweek == 'monday')
            if not monday:
                monday = request.env['opening.hours'].sudo().create({'partner_id': issue.partner_id.id, 'dayofweek': 'monday'})
            monday.open_time = self.get_time_float(post.get('monday_open_time') or '0.0')
            monday.close_time = self.get_time_float(post.get('monday_close_time') or '0.0')
            monday.break_start = self.get_time_float(post.get('monday_break_start') or '0.0')
            monday.break_stop = self.get_time_float(post.get('monday_break_stop') or '0.0')
            monday.close = True if post.get('monday_close') == '1' else False

            tuesday = issue.partner_id.sudo().opening_hours_ids.filtered(lambda o: o.dayofweek == 'tuesday')
            if not tuesday:
                tuesday = request.env['opening.hours'].sudo().create({'partner_id': issue.partner_id.id, 'dayofweek': 'tuesday'})
            tuesday.open_time = self.get_time_float(post.get('tuesday_open_time') or '0.0')
            tuesday.close_time = self.get_time_float(post.get('tuesday_close_time') or '0.0')
            tuesday.break_start = self.get_time_float(post.get('tuesday_break_start') or '0.0')
            tuesday.break_stop = self.get_time_float(post.get('tuesday_break_stop') or '0.0')
            tuesday.close = True if post.get('tuesday_close') == '1' else False

            wednesday = issue.partner_id.sudo().opening_hours_ids.filtered(lambda o: o.dayofweek == 'wednesday')
            if not wednesday:
                wednesday = request.env['opening.hours'].sudo().create({'partner_id': issue.partner_id.id, 'dayofweek': 'wednesday'})
            wednesday.open_time = self.get_time_float(post.get('wednesday_open_time') or '0.0')
            wednesday.close_time = self.get_time_float(post.get('wednesday_close_time') or '0.0')
            wednesday.break_start = self.get_time_float(post.get('wednesday_break_start') or '0.0')
            wednesday.break_stop = self.get_time_float(post.get('wednesday_break_stop') or '0.0')
            wednesday.close = True if post.get('wednesday_close') == '1' else False

            thursday = issue.partner_id.sudo().opening_hours_ids.filtered(lambda o: o.dayofweek == 'thursday')
            if not thursday:
                thursday = request.env['opening.hours'].sudo().create({'partner_id': issue.partner_id.id, 'dayofweek': 'thursday'})
            thursday.open_time = self.get_time_float(post.get('thursday_open_time') or '0.0')
            thursday.close_time = self.get_time_float(post.get('thursday_close_time') or '0.0')
            thursday.break_start = self.get_time_float(post.get('thursday_break_start') or '0.0')
            thursday.break_stop = self.get_time_float(post.get('thursday_break_stop') or '0.0')
            thursday.close = True if post.get('thursday_close') == '1' else False

            friday = issue.partner_id.sudo().opening_hours_ids.filtered(lambda o: o.dayofweek == 'friday')
            if not friday:
                friday = request.env['opening.hours'].sudo().create({'partner_id': issue.partner_id.id, 'dayofweek': 'friday'})
            friday.open_time = self.get_time_float(post.get('friday_open_time') or '0.0')
            friday.close_time = self.get_time_float(post.get('friday_close_time') or '0.0')
            friday.break_start = self.get_time_float(post.get('friday_break_start') or '0.0')
            friday.break_stop = self.get_time_float(post.get('friday_break_stop') or '0.0')
            friday.close = True if post.get('friday_close') == '1' else False

            saturday = issue.partner_id.sudo().opening_hours_ids.filtered(lambda o: o.dayofweek == 'saturday')
            if not saturday:
                saturday = request.env['opening.hours'].sudo().create({'partner_id': issue.partner_id.id, 'dayofweek': 'saturday'})
            saturday.open_time = self.get_time_float(post.get('saturday_open_time') or '0.0')
            saturday.close_time = self.get_time_float(post.get('saturday_close_time') or '0.0')
            saturday.break_start = self.get_time_float(post.get('saturday_break_start') or '0.0')
            saturday.break_stop = self.get_time_float(post.get('saturday_break_stop') or '0.0')
            saturday.close = True if post.get('saturday_close') == '1' else False

            sunday = issue.partner_id.sudo().opening_hours_ids.filtered(lambda o: o.dayofweek == 'sunday')
            if not sunday:
                sunday = request.env['opening.hours'].sudo().create({'partner_id': issue.partner_id.id, 'dayofweek': 'sunday'})
            sunday.open_time = self.get_time_float(post.get('sunday_open_time') or '0.0')
            sunday.close_time = self.get_time_float(post.get('sunday_close_time') or '0.0')
            sunday.break_start = self.get_time_float(post.get('sunday_break_start') or '0.0')
            sunday.break_stop = self.get_time_float(post.get('sunday_break_stop') or '0.0')
            sunday.close = True if post.get('sunday_close') == '1' else False
        if post.get('opening_hours_exceptions') != None and post.get('opening_hours_exceptions') != issue.partner_id.sudo().opening_hours_exceptions:
            issue.partner_id.sudo().opening_hours_exceptions = post.get('opening_hours_exceptions')

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
        value['help_visit_street'] = _('')
        value['help_visit_street2'] = _('')
        value['help_visit_zip'] = _('')
        value['help_visit_city'] = _('')
        value['help_visit_phone'] = _('')
        value['help_visit_email'] = _('')
        return value

    @http.route(['/reseller_register/information'], type='http', auth='public', website=True)
    def reseller_register_info(self, **post):
        return request.website.render('website_reseller_register_dermanord.reseller_register_info', {})

    @http.route(['/reseller_register/remove_img',], type='json', auth="public", website=True)
    def reseller_register_remove_img(self, partner_id='0', **post):
        partner = request.env['res.partner'].browse(int(partner_id))
        if partner:
            partner.write({'top_image': None})
            return True
        return False

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
