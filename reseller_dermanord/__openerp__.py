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

{
    'name': 'Reseller Dermanord',
    'version': '1.0',
    'category': '',
    'summary': '',
    'description': """
Resellers Page
==============
""",
    'author': 'Vertel AB',
    'license': 'AGPL-3',
    'website': 'http://www.vertel.se',
    'depends': [
        'partner_token',
        'website_partner',
        'website_partner_google_maps',
        'website_masonry',
        'child_catagory_tags',
        'postgres_geo_fields',
        'event_participant_dermanord',
        'website_sale_home',
        'website_partner_opening_hours',
    ],
    'data': [
        'data.xml',
        'res_config_view.xml',
        'security/ir.model.access.csv',
        'res_partner_view.xml',
        'templates.xml',
        #~ 'filter_sort_modal.xml',
    ],
    'application': False,
}

