# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2004-2015 Vertel AB (<http://vertel.se>).
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

import werkzeug
import werkzeug.urls

from openerp import http
from openerp.http import request
from openerp.tools.translate import _

import logging
_logger = logging.getLogger(__name__)


class ContactUs(http.Controller):

    @http.route(['/project_contact_form'], method='POST', auth='public', website=True)
    def send_mail(self, **post):
        subject = ""
        body = ""
        mail = ""

        # To make sure the site does not crash while trying to editing theme_dermanord.contactus_response
        if not post.get('case'):
            values = {}
            return request.website.render("theme_dermanord.contactus_response", values)

        project_id = int(post.get('case'))
        _logger.warn('Project_id: %s post: %s' %(project_id, post))
        project = request.env['project.project'].sudo().browse(project_id)

        partner = request.env['res.partner'].search([('email', '=', post.get('email_from'))], limit=1)
        if not partner:
            partner = request.env['res.partner'].create({
                'name':post.get('contact_name'),
                'email':post.get('email_from'),
                'phone':post.get('phone')
                })

        request.env[project.alias_model].create({
            'project_id': project.id,
            'partner_id':partner.id,
            'name': post.get('name'), 
            'description': post.get('description'),
            'message_follower_ids':[(4,partner.id)]
        })
        
        values = {}
        return request.website.render("theme_dermanord.contactus_response", values)









        
