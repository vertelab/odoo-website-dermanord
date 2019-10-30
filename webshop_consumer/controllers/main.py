# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2019- Vertel AB (<http://vertel.se>).
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
import logging
_logger = logging.getLogger(__name__)


class Main(http.Controller):
    @http.route(['/reseller/<int:reseller>/consumer'], type='http', auth='public', website=True)
    def add_consumer(self, reseller):
        return http.request.render('webshop_consumer.add_consumer', {'help':{}, 'validate':{}, 'reseller':request.env['res.partner'].sudo().browse(reseller) })

    @http.route('/consumer/detail', type='http', auth='public', website=True)
    def navigate_to_detail_page(self):
        # This will get all company details (in case of multicompany this are multiple records)
        companies = http.request.env['res.company'].sudo().search([])
        return http.request.render('webshop_consumer.detail_page', {
            # pass company details to the webpage in a variable
            'companies': companies})





