# -*- coding: utf-8 -*-
{
    'name': "res_users_link",

    'summary': """
        links from user to partner
    """,

    'description': """
        links from user to partner \n
        v14.0.0.0.1: initial version
    """,

    'author': "Vertel AB",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '14.0.0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        'views/views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
}
