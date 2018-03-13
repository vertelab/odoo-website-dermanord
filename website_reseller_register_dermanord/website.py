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
from openerp.addons.web import http
from openerp.http import request
from openerp.addons.website_reseller_register.website import reseller_register

import logging
_logger = logging.getLogger(__name__)


class reseller_register(reseller_register):

    def company_fileds(self):
        value = super(reseller_register, self).company_fileds()
        return value + ['brand_name', 'street', 'street2', 'zip', 'city', 'phone', 'email', 'is_reseller']

    def get_company_post(self, post):
        value = super(reseller_register, self).get_company_post(post)
        _logger.warn(post.get('company_is_reseller'))
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
        return value

    @http.route(['/reseller_register/information'], type='http', auth='public', website=True)
    def reseller_register_info(self, **post):
        return request.website.render('website_reseller_register_dermanord.reseller_register_info', {})
