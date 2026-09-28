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
    'name': 'Swedish Payroll — Arbetsgivarintyg (Employer Certificate)',
    'version': '18.0.1.0.0',
    'summary': 'Digital employer certificate (arbetsgivarintyg) for Swedish a-kassa, SOAP API integration with arbetsgivarintyg.nu.'
               'SOAP API integration with arbetsgivarintyg.nu.',
    'category': 'Payroll Localization',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se_payroll/l10n_se_arbetsgivarintyg',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n_se_payroll',
    'description': '''
Swedish Payroll — Arbetsgivarintyg (Employer Certificate)
=========================================================

    Digital handling of employer certificates according to the specification of
the Swedish unemployment funds (a-kassor).
    ''',
    'depends': [
        'l10n_se_hr_payroll',
        'hr',
        'hr_contract',
        'hr_holidays',
        'mail',
    ],
    'external_dependencies': {
        'python': ['zeep'],
    },
    'data': [
        'security/ir.model.access.csv',
        'data/arbetsgivarintyg_data.xml',
        'views/api_config_views.xml',
        'views/arbetsgivarintyg_views.xml',
        'views/arbetsgivarintyg_menu.xml',
        'views/wizard_send_views.xml',
    ],
    'auto_install': False,
    'installable': True,
}
