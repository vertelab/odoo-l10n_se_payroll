# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2024- Vertel AB (<https://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
##############################################################################

{
    'name': 'HR Leave Dashboard',
    'version': '0.1',
    'summary': 'Manager dashboard for leave — subordinates, absentees, approvals.',
    'category': 'Human Resources',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/',
    'license': 'AGPL-3',
    'depends': ['hr_holidays'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_leave_dashboard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hr_leave_dashboard/static/src/css/hr_leave_dashboard.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}
