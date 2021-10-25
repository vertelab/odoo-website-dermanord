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
import base64

from openerp import http
from openerp.http import request
from openerp.tools.translate import _

from odoo.addons.project_contact_form_dermanord.controllers.controller import ContactUs

import logging
_logger = logging.getLogger(__name__)

@http.route()
class ContactUsReCaptcha(ContactUs):
    @route()
    def _verify_recaptcha(self):
        _logger.warn("MyTag: Got Here!!!")
        return super(Extension, self).handler()
