# -*- coding: utf-8 -*-
{
    'name': 'l10n_se_payroll: 2026 (Tiichri 26)',
    'version': '1.0',
    'summary': '2026 payroll test data — extends tiichri with new payslips and salary history',
    'category': 'Payroll Localization',
    'description': """
Extends l10n_se_hr_payroll_tiichri with 2026 data:
- 12 payroll runs for 2026
- 74 payslips across 7 employees
- Multi-year contracts showing salary progression (2023-2026)
- Accounting periods for fiscal year 2026
    """,
    'author': 'Vertel AB',
    'website': 'https://vertel.se',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n-se-payroll',
    'depends': [
        'l10n_se_hr_payroll_tiichri',
    ],
    'data': [
        'data/data_periods_2026.xml',
        'data/data_payroll_run_2026.xml',
        'data/data_payslips_2026.xml',
        'data/data_contracts_2023_2026.xml',
        'data/data_corrections_2026.xml',
    ],
    'auto_install': False,
    'installable': True,
}
