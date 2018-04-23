# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution, third party addon
#    Copyright (C) 2004-2015 Vertel AB (<http://vertel.se>).
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
from openerp import fields, api, models, _
import logging
_logger = logging.getLogger(__name__)

class website_config_settings(models.TransientModel):
    _inherit = 'website.config.settings'

    find_reseller_top_img = fields.Binary(string='Image for "Find Reseller Page"')

    @api.multi
    def set_default_parameters(self):
        img = self.env.ref('reseller_dermanord.find_reseller_top_img')
        img.write({'datas': self.find_reseller_top_img})

    @api.model
    def get_default_parameters(self, fields=None):
        return {
            'find_reseller_top_img': self.env.ref('reseller_dermanord.find_reseller_top_img').datas or None,
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
