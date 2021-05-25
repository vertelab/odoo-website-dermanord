# -*- coding: utf-8 -*-
{
    'name': "product_packaging_dermanord",

    'summary': """
        Added the odoo 8 way of handing adding and changing package types
    """,

    'description': """
        Added the odoo 8 way of handing adding and changing package types
    """,

    'author': "Vertelab",
    'website': "vertel.se",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Product',
    'version': '14.0.0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','product','website_sale'],

    # always loaded
    'data': [
        'data/data.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
    ],

}
