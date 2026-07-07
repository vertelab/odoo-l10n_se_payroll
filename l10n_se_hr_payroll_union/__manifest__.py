# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2026- Vertel AB.
#    License AGPL-3.
#
##############################################################################

{
    'name': 'l10n_se_hr_payroll_union: Union Fees (Fackavgifter)',
    'version': '18.0.1.0.0',
    'summary': 'Swedish union fee management — automatic deduction and reporting',
    'category': 'Payroll Localization',
    'author': 'Vertel AB',
    'website': 'https://vertel.se',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n-se-payroll',
    'description': """
Swedish Union Fee Management (Fackavgifter)
===========================================

Manage union membership fees automatically deducted from salary
and reported to union organizations.

Features:
---------
* Union registry (IF Metall, Kommunal, Unionen, Sveriges Ingenjörer, etc.)
* Employee → union linkage
* Monthly union fee deduction from payslips
* Fee calculation: fixed amount or % of salary
* Union reporting: monthly/quarterly file per union
* Bankgiro/Plusgiro payment tracking
* Historical fee register per employee
    """,
    'depends': [
        'l10n_se_hr_payroll',
        'payroll', 'hr', 'hr_contract',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/union_views.xml',
        'data/union_data.xml',
    ],
    'auto_install': False,
    'installable': True,
}
