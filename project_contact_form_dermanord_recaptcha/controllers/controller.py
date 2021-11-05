# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2004-2021 Vertel AB (<http://vertel.se>).
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

from openerp import http
from openerp.http import request
from openerp.tools.translate import _
from openerp.exceptions import ValidationError
from openerp.addons.website_form_recaptcha.controllers.main import WebsiteForm

from openerp.addons.project_contact_form_dermanord.controllers.controller import ContactUs

import logging
_logger = logging.getLogger(__name__)


class ContactUsReCaptcha(ContactUs,WebsiteForm):
    @http.route(['/project_contact_form'], method='POST', auth='public', website=True)
    def send_mail(self, **kwargs):
        '''Append reCAPTCHA test on the project_contact_us_form'''
        # Try except modified from OCA's website_crm_recaptcha
        try:
            self.extract_data(**kwargs)
            # Test to more easily test failures
            # Note: Validation failure otherwise never happen with the test key
            captcha_obj = request.env['website.form.recaptcha']
            if not kwargs.get(captcha_obj.RESPONSE_ATTR):
                _logger.warn("reCAPTCHA validation token of length 0")
                raise ValidationError("reCAPTCHA validation token of length 0")
        except ValidationError as e:
            # Mock super() to make it fail by removing a required field
            kwargs.pop("description", None)
            #bad = True
            # Note: Failure never happen with the test key
            _logger.warn("reCAPTCHA verification unsuccessful")
            # TODO: Change to appropriate response and message
            values = {}
            return request.website.render("theme_dermanord.contactus_response", values)

        # TODO: Don't super if reCAPTCHA fail
        # TODO: Make a failure page
        return super(ContactUsReCaptcha, self).send_mail(**kwargs)
