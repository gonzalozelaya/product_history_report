# -*- coding: utf-8 -*-
{
    'name': "Product History Report",

    'summary': """
        This custom Odoo module provides an insightful report on inventory movement over the last year. It offers a comprehensive view of stock changes, enabling better inventory management and decision-making.
    """,

    'description': """
        This custom Odoo module provides an insightful report on inventory movement over the last year. It offers a comprehensive view of stock changes, enabling better inventory management and decision-making.
    """,

    'author': "Doodex",
    'company': "Doodex",
    'website': "https://www.doodex.net/",

    'category': 'Warehouse',
    'version': '17.0.1.0.0',

    'depends': ['base', 'stock'],

    'data': [
        'security/ir.model.access.csv',
        'views/stock_history_view.xml',
        'views/views.xml',
    ],
    'application': False,
    'images': ['static/description/banner.png'],
    'license': 'LGPL-3',
}
