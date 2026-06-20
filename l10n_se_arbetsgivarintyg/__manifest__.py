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
    'version': '1.0',
    'summary': 'Digital employer certificate (arbetsgivarintyg) for Swedish a-kassa, '
               'SOAP API integration with arbetsgivarintyg.nu.',
    'category': 'Payroll Localization',
    'author': 'Vertel AB',
    'website': 'https://vertel.se',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n_se_payroll',
    'description': """
Swedish Employer Certificate (Arbetsgivarintyg)
===============================================

Digital hantering av arbetsgivarintyg enligt Sveriges a-kassors specifikation.

Features:
---------
* Create and manage employer certificates for employees
* Auto-populate data from employee, contract, and payslip records
* Track employment details, salary, worked time, leave of absence
* Send certificates via SOAP API to arbetsgivarintyg.nu
* Test and production endpoint support
* Full workflow: draft → populated → sent → signed → done

API Integration:
----------------
* SOAP web service (arbetsgivarintyg.nu)
* ApiNyckel + ArbetsgivarId authentication
* ResultCode/ResultMessage response handling

Specifikation:
--------------
Baseras på "Teknisk specifikation arbetsgivarintyg.nu" från Sveriges a-kassor.
https://stsakassa.se/sites/default/files/2018-11/Teknisk%20specifikation%20arbetsgivarintyg.nu_.pdf
    """,
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

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
