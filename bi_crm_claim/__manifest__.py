# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2022- Vertel AB (<https://vertel.se>).
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
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Dermanord: CRM Claim Management',
    'version': '14.0.0.0.0',
    # Version ledger: 14.0 = Odoo version. 1 = Major. Non regressionable code. 2 = Minor. New features that are regressionable. 3 = Bug fixes
    'summary': 'This plugin helps to manage after sales services as claim management',
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Website',
    'description': """
    Claim system for your product, claim management, submit claim, claim form, Ticket claim, 
    support ticket, issue, website project issue, crm management, ticket handling,support management, 
    project support, crm support, online support management, online claim, claim product, claim 
    services, issue claim, fix claim, raise ticket, raise issue, view claim, display claim, list claim on website.
    """,
    'sequence': '5',
    'author': 'BrowseInfo',
    ##### 'website': 'https://www.browseinfo.in',
    'website': 'https://vertel.se/apps/odoo-website-dermanord/bi_crm_claim',
    'images': ['static/description/banner.png'], # 560x280 px.
    'license':'OPL-1',
    'contributor': '',
    'maintainer': 'Vertel AB',
    # Any module necessary for this one to work correctly
    'repository': 'https://github.com/vertelab/odoo-website-dermanord',

    'depends': ['crm','sale','sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/crm_claim_menu.xml',
        'views/crm_claim_data.xml',
        'views/res_partner_view.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'live_test_url':'https://youtu.be/zPG8PS4H_FE',
    "images":["static/description/Banner.png"],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
