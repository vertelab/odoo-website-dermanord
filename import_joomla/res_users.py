# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution, third party addon
#    Copyright (C) 2004-2017 Vertel AB (<http://vertel.se>).
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
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp.tools import safe_eval
import base64
from cStringIO import StringIO
from difflib import SequenceMatcher

from subprocess import Popen, PIPE
import os
import tempfile
try:
    from xlrd import open_workbook, XLRDError
    from xlrd.book import Book
    from xlrd.sheet import Sheet
except:
    _logger.info('xlrd not installed. sudo pip install xlrd')

from lxml import html
import requests

import re

import logging
_logger = logging.getLogger(__name__)

try:
    import unicodecsv as csv
except:
    _logger.info('Missing unicodecsv. sudo pip install unicodecsv')


class DermanordImport(models.TransientModel):
    _name = 'user.dermanord.import.wizard'

    def _default_filter_name(self):
        return 'Import %s' % fields.Datetime.to_string(fields.Datetime.context_timestamp(self, fields.Datetime.from_string(fields.Datetime.now())))

    def _default_group_ids(self):
        return self.env.ref('__export__.res_groups_283', False)

    user_file = fields.Binary(string='Order file')
    mime = fields.Selection([('url','url'),('text','text/plain'),('pdf','application/pdf'),('xlsx','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),('xls','application/vnd.ms-excel'),('xlm','application/vnd.ms-office')])
    file_name = fields.Char(string='File Name')
    filter_name = fields.Char(string='Filternamn', help="Kommer generera filter med detta namn för att hitta skapade partners och användare.", default=_default_filter_name)
    messages = fields.Html(string='Meddelanden', readonly=True)
    group_ids = fields.Many2many(string='Grupper', comodel_name='res.groups', default=_default_group_ids, help="Grupper utöver de som är definierade på template-användaren.")
    users = fields.Char()

    @api.multi
    def goto_users(self):
        ids = safe_eval(self.users or '[]')
        action = self.env['ir.actions.act_window'].for_xml_id('base', 'action_res_users')
        action.update({
            'domain': [('id', 'in', ids)],
            'context': {},
        })
        return action
        

    @api.multi
    def import_files(self):
        f = csv.reader(StringIO(base64.b64decode(self.user_file)))
        partners = self.env['res.partner'].browse()
        users = self.env['res.users'].browse()
        imported = self.env.ref('import_joomla.category_imported')
        #~ unmatched = self.env.ref('import_joomla.category_unmatched')
        warnings, info = [], []

        for row in f:
            if row[0]:
                customer_no = row[0].strip()
                email = row[3].strip().lower()
                name = ' '.join([row[1].strip(), row[2].strip()])
                # Check blocked
                if row[4] == '0':
                    # Check for contact
                    contact = None
                    for partner in self.env['res.partner'].search([('customer_no', '=', customer_no), ('email', '=ilike', email), ('type', '=', 'contact'), ('is_company', '=', False)]):
                        _logger.warn('matching partner %s (%s)' % (partner.name, partner.id))
                        if not contact:
                            contact = partner
                        else:
                            # Multiple hits. Compare names and find best match
                            if SequenceMatcher(None, name, partner.name).ratio() > SequenceMatcher(None, name, contact.name).ratio():
                                _logger.warn('replaced %s with %s' % (contact.id, partner.id))
                                contact = partner
                    
                    # Check for parent and create new contact
                    if not contact:
                        parent = self.env['res.partner'].search([('customer_no', '=', customer_no), ('parent_id', '=', False)])
                        if parent:
                            contact = self.env['res.partner'].create({
                                'name': name,
                                'use_parent_address': True,
                                'email': email,
                                'parent_id': parent.id,
                                'type': 'contact',
                                'category_id': [(6, 0, [imported.id])],
                            })
                    
                    #Check for user and create if needed
                    if contact:
                        partners |= contact
                        user = self.env['res.users'].search([('partner_id', '=', contact.id)])
                        if not user:
                            user = self.env['res.users'].browse(self.env['res.users']._signup_create_user({
                                'name': name,
                                'email': email,
                                'login': email,
                                'partner_id': contact.id,
                            }))
                        user.groups_id |= self.group_ids
                        users |= user
                    else:
                        # No partner found.
                        warnings.append(u"Kunde ej matcha %s (%s, %s) mot en befintlig kund!" % (name, customer_no, email))
                        #~ contact = self.env['res.partner'].create({
                            #~ 'email': email,
                            #~ 'name': name,
                            #~ 'parent_id': parent.id,
                            #~ 'type': 'contact',
                            #~ 'category_id': [(6, 0, [unmatched.id])],
                        #~ })
                elif row[4] == '1':
                    # ~ _logger.warn('\n\n%s\n%s\n%s\n' % (name, customer_no, email))
                    info.append(u"Hoppade över %s (%s, %s). Joomla-användaren inaktiverad." % (name, customer_no, email))

        messages = ''
        if warnings:
            messages += '<h2>Varningar</h2>\n\t<ul>\n'
            for warning in warnings:
                messages += '\t\t<li>%s</li>\n' % warning
            messages += '\t</ul>\n'
        if info:
            messages += '<h2>Info</h2>\n\t<ul>\n'
            for inf in info:
                messages += '\t\t<li>%s</li>\n' % inf
            messages += '\t</ul>\n'
        self.messages = messages
        if self.filter_name:
            self.env['ir.filters'].create({
                'name': self.filter_name,
                'model_id': 'res.partner',
                'user_id': False,
                'domain': [('id', 'in', [p.id for p in partners])],
            })
            self.env['ir.filters'].create({
                'name': self.filter_name,
                'model_id': 'res.users',
                'user_id': False,
                'domain': [('id', 'in', [u.id for u in users])],
            })
        _logger.warn('imported joomla users\nfilters: %s\partners: %s\nusers: %s' % (self.filter_name, [p.id for p in partners], [u.id for u in users]))
        self.users = str([u.id for u in users])
        if self.messages:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'user.dermanord.import.wizard',
                'view_type': 'form',
                'view_mode': 'form',
                'res_id': self.id,
                'target': 'new',
                'context': {},
            }
        return self.goto_users()

    def get_label(self, name):
        label = self.env['res.partner.category'].search([('name', '=', name)])
        if not label:
            label = self.env['res.partner.category'].create({'name': name})
        return label

    def get_selection_text(self,field,value):
        for type,text in self.fields_get([field])[field]['selection']:
            if text == value:
                return type
        return None

    def get_selection_value(self,field,value):
        for type,text in self.fields_get([field])[field]['selection']:
            if type == value:
                return text
        return None
