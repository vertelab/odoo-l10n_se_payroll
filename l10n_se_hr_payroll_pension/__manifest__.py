# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2026- Vertel AB (<https://vertel.se>).
#    License AGPL-3.
#
##############################################################################

{
    'name': 'l10n_se_hr_payroll_pension: Tjänstepensionsberäkning',
    'version': '18.0.1.0.0',
    'summary': 'Detailed Swedish occupational pension calculation (ITP1, ITP2, SAF-LO, AKAP-KL)',
    'category': 'Payroll Localization',
    'author': 'Vertel AB',
    'website': 'https://vertel.se',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n-se-payroll',
    'description': """
Detailed Swedish Occupational Pension Calculation
=================================================

Calculates occupational pension premiums and contributions per employee
based on collective agreement rules. Goes beyond the basic FORA premium
reporting with detailed wage bracket tracking and löneväxling support.

Features:
---------
* ITP 1 (born 1979+): 4.5% up to 7.5 IBB, 30% above
* ITP 2 (born before 1979): age-based with 3 brackets
* SAF-LO: 4.5% base + optional flex part
* AKAP-KL: 6.0% + variable component
* Wage bracket tracking (per IBB level)
* Löneväxling (salary exchange to pension)
* Monthly pension basis calculation per employee
* Integration with payslip salary rules
* Employee pension register with historical tracking

2026 Base Amounts:
* IBB (Inkomstbasbelopp): 80 600 kr
* PBB (Prisbasbelopp): 48 300 kr
    """,
    'depends': [
        'l10n_se_hr_payroll',
        'l10n_se_hr_payroll_collective',
        'l10n_se_payroll_fora',
        'payroll',
        'hr',
        'hr_contract',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/pension_views.xml',
        'data/pension_data.xml',
    ],
    'auto_install': False,
    'installable': True,
}
