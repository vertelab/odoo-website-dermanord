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

{
    'name': 'Dermanord: Theme Maria Åkerberg',
    'version': '14.0.0.0.0',
    # Version ledger: 14.0 = Odoo version. 1 = Major. Non regressionable code. 2 = Minor. New features that are regressionable. 3 = Bug fixes
    'summary': 'Website theme for Maria Åkerberg.',
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Website',
    'description': """
    Website theme for Maria Åkerberg.
    """,
    #'sequence': '1',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-website-dermanord/theme_maria_akerberg',
    'images': ['static/description/banner.png'], # 560x280 px.
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-website-dermanord',
    # Any module necessary for this one to work correctly
    "depends": [
        "website",
        "website_sale",
        "website_imagemagick",
        "sale_commission",
        "product_ma_fields",
        "currency_decimal_options"
    ],
    "data": [
        "security/base_security.xml",
        "views/assets.xml",
        "views/variant_template.xml",
        "views/templates.xml",
        "views/recipe.xml",
        "views/customizations.xml",
        "views/product_views.xml",
        "views/portal_templates.xml",
        "views/home_portal.xml",
    ],
    "demo": [],
    "installable": True,
    "application": False,
    "author": "Vertel AB",
    "website": "www.vertel.se",
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
