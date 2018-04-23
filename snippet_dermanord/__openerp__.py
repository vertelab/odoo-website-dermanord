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
    'name': 'Snippet Dermanord',
    'version': '1.0',
    'category': 'Theme',
    'summary': 'A Snippet Library',
    'description': """
Extra snippets for Dermanord.
=============================
""",
    'author': 'Vertel AB',
    'license': 'AGPL-3',
    'website': 'http://www.vertel.se',
    'depends': [
        'webshop_dermanord',
        'website_imagemagick',
        'sale_promotions',
        'crm_campaign_product',
        'crm_campaign_blog',
        'crm_campaign_phase',
        'product_private',
        'website_blog_private',
    ],
    'data': [
        'snippets_css_js.xml',
        'snippets.xml',
        'snippets_data.xml',
    ],
    'qweb': ['static/src/xml/snippets.xml'],
    'application': True,
}
