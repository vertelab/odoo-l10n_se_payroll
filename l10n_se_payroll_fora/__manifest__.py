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
    'name': 'l10n_se_payroll_fora: FORA Premium Reporting',
    'version': '18.0.1.0.0',
    'summary': 'FORA — Swedish collective insurance & pension premium reporting',
    'category': 'Payroll Localization',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se_payroll/l10n_se_payroll_fora',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n-se-payroll',
    'description': """
FORA — Collective Insurance & Pension Premium Reporting
=======================================================

FORA (Försäkringsbranschens Arbetsgivarorganisation) is the central
administrator for collective agreement insurance and pension in Sweden.

This module enables monthly/quarterly reporting of wage data to FORA
for calculation of insurance and pension premiums.

Features:
---------
* Aggregate payroll data per employee per collective agreement per period
* Map salary rule codes to FORA premium categories:
  - TGL (Group Life Insurance) basis
  - TFA (Work Injury Insurance) basis
  - AGS (Sick Pay Insurance) basis
  - Avtalspension basis (ITP1, ITP2, SAF-LO, AKAP-KL)
* Compute FORA premiums per employee per insurance type
* Age-group segmentation for correct premium rates
* Generate FORA XML file (industry-standard format)
* Track FORA case numbers and submission status
* Auto-create monthly FORA declarations via cron
* Calendar integration for FORA deadline tracking

Dependencies:
-------------
* l10n_se_hr_payroll — Swedish payroll rules
* l10n_se_hr_payroll_collective — Collective agreement definitions
* l10n_se_payroll_agd — Employer declaration (shares wage aggregation)
* l10n_se_tax_report — Declaration base class
* payroll, hr — Core modules
    """,
    'depends': [
        'l10n_se_hr_payroll',
        'l10n_se_hr_payroll_collective',
        'l10n_se_payroll_agd',
        'l10n_se_tax_report',
        'payroll',
        'hr',
    ],
    'external_dependencies': {
        'python': ['lxml', 'requests'],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/fora_declaration_views.xml',
        'views/collective_agreement_views.xml',
        'data/fora_cron_data.xml',
    ],
    'auto_install': False,
    'installable': True,
}
