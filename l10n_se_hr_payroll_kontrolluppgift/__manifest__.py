# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2026- Vertel AB.
#    License AGPL-3.
#
##############################################################################

{
    'name': 'l10n_se_hr_payroll_kontrolluppgift: Tax Statements (KU)',
    'version': '18.0.1.0.0',
    'summary': 'Swedish tax statements (Kontrolluppgifter KU20/KU25) to Skatteverket.',
    'category': 'Payroll Localization',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se_payroll/l10n_se_hr_payroll_kontrolluppgift',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n-se-payroll',
    'description': '''
Tax Statements (KU)
===================

    Annual tax statements per employee submitted to Skatteverket.

    Features:
    * KU20: Salary, benefits, tax withheld (per employee)
    * KU25: Pension payments (per employee)
    * Aggregate yearly data from payslips
    * Generate KU XML according to Skatteverket DTD
    * Submit to Skatteverket via API
    * Integration with AGD (employer declaration) for cross-checking
    * Annual summary per employee

    Features:

        - Automation: Scheduled jobs: KU: create annual tax statement for previous year.
        - UI Integration: Extends 1 view(s) in the Odoo interface.
        - Extends Odoo: Builds on account.declaration, account.ku.declaration, account.ku.declaration.line, hr.payslip.
    ''',
    'depends': [
        'l10n_se_hr_payroll',
        'l10n_se_payroll_agd',
        'l10n_se_payroll_fora',
        'l10n_se_tax_report',
        'payroll', 'hr',
    ],
    'external_dependencies': {
        'python': ['lxml'],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/ku_views.xml',
        'data/ku_data.xml',
    ],
    'auto_install': False,
    'installable': True,
}
