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
    'name': 'Dermanord: Webshop Dermanord',
    'version': '14.0.0.0.0',
    # Version ledger: 14.0 = Odoo version. 1 = Major. Non regressionable code. 2 = Minor. New features that are regressionable. 3 = Bug fixes
    'summary': 'Special layout for Dermanord AB webshop.',
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Website',
    'description': """
    Special layout for Dermanord AB webshop
    ====================
    """,
    #'sequence': '1',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-website-dermanord/webshop_dermanord',
    'images': ['static/description/banner.png'], # 560x280 px.
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-website-dermanord',
    # Any module necessary for this one to work correctly
    'website': 'http://www.vertel.se',
    'depends': [
        'portal',
        'product_multi_image_attachment',
        'website_sale_product_gallery',
        'website_blog',
        'product_dermanord',
        'product_private',
        'website_sale_previous_products',
        'website_sale_terms',
        'website_sale_comment',
        'website_product_pcategory',
        'website_imagemagick',
        'product_ingredients',
        'product_facets',
        'website_bootstrap_select2',
        'website_fts_product',
        'website_fts_popular',
        'product_attribute_value_image',
        'website_sale_instock',
        'website_sale_lang_pricelist',
        'crm_campaign_phase_default_variant',
        'website_sale_delivery',
        'website_sale_minimum_order_value',
        'website_sale_price_chart',
        'calc_orderpoint',
        'reseller_dermanord',
        'mrp_dermanord',
        'website_translate_extra_modules',
        'product_pricelist_dermanord',
        'delivery',
        ],
    'data': [
        'views/webshop_dermanord_view.xml',
        'views/website_sale_view.xml',
        'views/template_checkout.xml',
        'views/filter_sort_modal.xml',
        'data/webshop_dermanord_data.xml',
        'views/product_view.xml',
        'security/dn_security.xml',
        'security/ir.model.access.csv',
        'views/stock_notification_view.xml',
        # ~ 'data/warehouse_data.xml',
    ],
    'qweb': ['static/src/xml/product.xml'],
    'application': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
