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
    'name': 'Webshop Image Filter',
    'version': '14.0.0.0.1',
    'category': 'website',
    'summary': 'ImageMagick thumbnails for the product-view',
    'description': """
        Displays the thumbnails in the product-view with ImageMagick using a provided recipe
""",
    'author': "Vertel AB",
    'license': "AGPL-3",
    'website': 'https://www.vertel.se',
    'depends': [
        'website_sale','website_imagemagick',
    ],
    'data': [
        'views/templates.xml',
        'views/recipe.xml',
    ],
    'qweb': [

    ],
    'application': False,
}
