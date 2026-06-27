# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2026- Vertel AB (<https://vertel.se>).
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
    'name': 'l10n_se_payroll_growth_support: Växa-stöd',
    'version': '18.0.1.0.0',
    'summary': 'Swedish growth support (växa-stöd) — reimbursement application for employer contributions',
    'category': 'Payroll Localization',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se_payroll/l10n_se_payroll_growth_support',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n_se_payroll',
    'description': """
Swedish Growth Support (Växa-stöd)
==================================

From January 2026, employers pay full employer contributions (31.42%) and apply
separately for reimbursement of the difference (31.42% - 10.21% = 21.21%) for
their first and second employees.

Features:
---------
* Calculate växa-stöd reimbursement per employee per month
* Link to payslip runs and AGD declarations for salary data
* Auto-determine salary cap (25 000 or 35 000 SEK) based on hire date
* Track 24-month limit per employee
* EU de minimis aid tracking (max €300 000 in 3 years)
* Generate downloadable summary for Skatteverket e-service
* Ready for Skatteverket API submission when available
* Auto-create monthly applications via cron
* Calendar integration for application deadlines

Dependencies:
-------------
* l10n_se_hr_payroll — Swedish payroll rules
* l10n_se_tax_report — Declaration base class + SKV API infrastructure
* l10n_se_payroll_agd — Employer declaration for salary data
* payroll — Core payroll (hr.payslip, hr.payslip.run)
* hr — HR module (hr.employee, hr.contract)
    """,
    'depends': [
        'l10n_se_hr_payroll',
        'l10n_se_tax_report',
        'l10n_se_payroll_agd',
        'payroll',
        'hr',
    ],
    'external_dependencies': {
        'python': ['lxml', 'requests'],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/vaxa_support_views.xml',
        'data/vaxa_cron_data.xml',
    ],
    'demo': [
        'demo/vaxa_demo.xml',
    ],
    'auto_install': False,
    'installable': True,
}
