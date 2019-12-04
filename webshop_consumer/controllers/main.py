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
from openerp import api, models, fields, _

import logging

_logger = logging.getLogger(__name__)


# ~ http://maria:8069/sv_SE/reseller/5522/consumer
# todo: rimlighetskontroll av reseller.
# todo: använd sign-up
# todo: knyt användaren till åf. reseller_id 
# todo: specifik template-användare (avvakta)

class Main(http.Controller):
    @http.route(['/reseller/edit/consumer_page'], type='http', auth='user', website=True)
    def edit_consumer_page(self, **post):
        return http.request.render('webshop_consumer.insert_consumer')
        
    @http.route(['/reseller/<int:reseller_id>/consumer'], type='http', auth='public', website=True)
    def add_consumer(self, reseller_id, **post):
        reseller = request.env['res.partner'].sudo().browse(reseller_id)
        countries = request.env['res.country'].sudo().search([('code', 'in', ['SE','NL','NO'])])
        if request.httprequest.method == 'GET':
            if reseller and reseller.is_reseller:
                _logger.warn('\n\n\n\n\n\n\n\n RESELLER ID: %s' % reseller)
                # ~ return http.request.render('webshop_consumer.add_consumer', {'help':{}, 'validate':{}, 'reseller':{request.env['res.partner'].sudo().browse('reseller')} })
                return http.request.render('webshop_consumer.add_consumer', {'help':{}, 'validate':{}, 'reseller':request.env['res.partner'].sudo().browse(reseller_id), 'countries': countries })
            else:
                return http.request.render('webshop_consumer.error',  {'help':{}, 'validate':{}, 'reseller':request.env['res.partner'].sudo().browse(reseller_id) })
        else:
            _logger.warn('\n\n\n\n\n\n\n\n FIRST NAME: %s' % post.get('city'))
            _logger.warn('\n\n\n\n\n\n\n\n reseller_id: %s' % reseller_id)
            if post.get('firstname') and post.get('lastname')  and post.get('street') and post.get('zip') and post.get('city') and post.get('country_id') and post.get('email'):
                ## INSERT NEW USER
                try:
                    partner = request.env['res.partner'].sudo().create({
                        'name': post.get('firstname', '') + ' ' + post.get('lastname', ''),
                        'login': post.get('email', ''),
                        'email': post.get('email', ''),
                        'reseller_id': reseller_id,
                    })
                    request.env['res.users'].sudo().signup({
                        'name': post.get('firstname', '') + ' ' + post.get('lastname', ''),
                        'street': post.get('street', ''),
                        'zip': post.get('zip', ''),
                        'city': post.get('city', ''),
                        'country_id': post.get('country_id', ''),
                        'login': post.get('email', ''),
                        'email': post.get('email', ''),
                        'phone': post.get('phone', ''),
                        'reseller_id': reseller_id,
                        'partner_id': partner.id,
                    })
                    return http.request.render('webshop_consumer.insert_consumer', {'help':{}, 'validate':{}, 'reseller':reseller })
                except Exception, e:
                    # copy may failed if asked login is not available.
                    # raise SignupError(ustr(e))
                    return http.request.render('webshop_consumer.error', {'error':ustr(e) })
            else:
                ## ELSE RETURN TO PAGE FOR REGISTER
                return http.request.render('webshop_consumer.add_consumer', {'help':{}, 'validate':{}, 'reseller':reseller, 'countries':countries })
            

    
    
