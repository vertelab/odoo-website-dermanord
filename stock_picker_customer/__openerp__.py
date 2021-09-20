# -*- coding: utf-8 -*-
{
    'name': "stock_picker_customer",

    'summary': """
        Module to display for_reseller button within the stock picking view
        and printable document
    """,

    'description': """
        Long description of module's purpose
    """,

    'author': "Vertel AB",
    'website': "https://vertel.se/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'stock',
    'version': '8.0.0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'stock', 'stock_dermanord'],

    # always loaded
    'data': [
        'views/views.xml',
        'views/template.xml'
    ],
}
