################################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2019 N-Development (<https://n-development.com>).
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
################################################################################

{
    'name': 'MA webshop extra product fields',
    'description': """
    Adds additional product fields.
    """,
    'category': 'Util/Vertel',
    'version': '14.0.1.2.0',
    'depends': [
        "sale",
        "website_sale",
        "emipro_theme_product_label"
    ],
    'data': [
        "views/product_product_views.xml",
        "views/product_template_views.xml",
    ],
    'qweb': [
    ],
    'installable': True,
    'application': False,
    'author': "Vertel AB",
    'website': "www.vertel.se",
}
