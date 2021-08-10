# -*- coding: utf-8 -*-
{
    'name': "barcode_dermanord",

    'summary': """
        a new field for barcodes which allows for usage of duplicate barcodes""",

    'description': """
        a new field for barcodes which allows for usage of duplicate barcodes
    """,

    'author': "vertel AB",
    'website': "vertel.se",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'product',
    'version': '14.0.0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'product'],

    # always loaded
    'data': [
        'views/views.xml',
    ],
}
