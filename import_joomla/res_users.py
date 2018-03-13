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
import base64
from cStringIO import StringIO

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

    user_file = fields.Binary(string='Order file')
    mime = fields.Selection([('url','url'),('text','text/plain'),('pdf','application/pdf'),('xlsx','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),('xls','application/vnd.ms-excel'),('xlm','application/vnd.ms-office')])
    info = fields.Text(string='Info')
    tmp_file = fields.Char(string='Tmp File')
    file_name = fields.Char(string='File Name')

    @api.multi
    def import_files(self):
        f = csv.reader(StringIO(base64.b64decode(self.user_file)))
        for row in f:
            if row[0]:
                #~ _logger.warn(row)
                # Check blocked
                if row[4] == '0':
                    contact = None
                # Check kundnummer
                    partner = self.env['res.partner'].search([('customer_no','=',row[0].strip())])
                # Check given/family name
                    if partner:
                        contact = partner.child_ids.filtered(lambda c: c.name.lower() in '%s %s'.lower() % (row[1].strip(),row[2].strip()) or c.email.strip().lower() == row[3].strip().lower())
                    else:
                        partner = self.env['res.partner'].search(['|',('name','ilike','%s %s' % (row[1].strip(),row[2].strip())),('email','ilike',row[3].strip())])
                        if partner:
                            contact = partner.child_ids.filtered(lambda c: c.name.lower() in '%s %s'.lower() % (row[1].strip(),row[2].strip()) or c.email.strip().lower() == row[3].strip().lower())
                    if contact:
                        pass
                        # If found res.partner (check res.users to) send invitation mail 
                    elif partner:    
                        # If not found create and send invitation mail
                        contact  = self.env['res.users'].with_context(no_reset_password=True).create({
                            'name': '%s %s' % (row[1].strip(),row[2].strip()),
                            'email': row[3].strip(),
                            'login': row[3].strip(),
                            'groups_id': [(6,0,[])]
                        })
                        contact.parent_id.id = partner.id
                        #~ contact.action_reset_password()
                    else:
                        contact = None
                        _logger.error('no partner found %s ' % row)

                        
                # Check e-mail
                
                
                

        
        
        
        


        return {'type': 'ir.actions.act_window',
                'res_model': 'res.users',
                'view_type': 'form',
                'view_mode': 'form',
                 'view_id': self.env.ref('base.view_users_tree').id,
                 'res_id': contact.id if contact else None,
                 'target': 'current',
                 'context': {},
                 }



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
