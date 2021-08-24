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
    'name': 'Webshop From Price',
    'description': """
    Module that calculates and controls if from price should be rendered
    """,
    'category': 'Util/Vertel',
    'version': '1.0',
    'depends': [
        "sale",
        "product",
        "website_sale",
    ],
    'data': [
        "views/templates.xml",
    ],
    'qweb': [

    ],
    'installable': True,
    'application': True,
    'author': "Vertel AB",
    'website': "www.vertel.se",
}
