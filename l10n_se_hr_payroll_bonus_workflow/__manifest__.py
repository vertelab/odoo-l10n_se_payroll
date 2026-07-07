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
    'name': 'l10n_se_payroll: Bonus Workflow',
    'version': '0.1',
    'summary': 'Bonus request approval workflow integrated with Swedish payroll.',
    'category': 'Payroll Localization',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/',
    'license': 'AGPL-3',
    'depends': [
        'l10n_se_hr_payroll',
        'account',
        'mail',
    ],
    'data': [
        'data/ir_sequence_data.xml',
        'security/ir.model.access.csv',
        'views/bonus_request_views.xml',
        'views/bonus_reason_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
