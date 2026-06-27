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
    'name': 'l10n_se_payroll_agd: Arbetsgivardeklaration',
    'version': '18.0.1.0.0',
    'summary': 'Swedish employer declaration (arbetsgivardeklaration) on individual level',
    'category': 'Payroll Localization',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se_payroll/l10n_se_payroll_agd',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n_se_payroll',
    'description': """
Swedish Employer Declaration (Arbetsgivardeklaration)
=====================================================

Monthly tax declaration for employers. Aggregates payroll data per employee
and submits to Skatteverket via the eSKD API.

Features:
---------
* Aggregate salary lines from hr.payslip per employee per month
* Map salary rule codes to SKV form fields (ruta 50-88)
* Automatic age-based employer contribution rates (31,42% / 16,36% / 6,15%)
* Generate eSKD XML (same DTD 6.0 as VAT declarations)
* Submit to Skatteverket via API with certificate authentication
* Auto-create monthly declarations via cron
* Calendar integration for declaration deadlines

Dependencies:
-------------
* l10n_se_hr_payroll — Swedish payroll rules
* l10n_se_tax_report — Declaration base class + SKV API infrastructure
* l10n_se_tax_account — Skatteverket partner configuration
    """,
    'depends': [
        'l10n_se_hr_payroll',
        'l10n_se_tax_report',
        'l10n_se_tax_account',
        'payroll',
        'hr',
    ],
    'external_dependencies': {
        'python': ['lxml', 'requests'],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/agd_declaration_views.xml',
        'data/agd_cron_data.xml',
    ],
    'demo': [
        'demo/agd_demo.xml',
    ],
    'auto_install': False,
    'installable': True,
}
