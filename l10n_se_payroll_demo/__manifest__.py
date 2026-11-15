{
    'name': 'l10n_se: Payroll Demo Data',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se_payroll/l10n_se_payroll_demo',
    'version': '18.0.1.0.0',
    'category': 'Payroll Localization',
    'license': 'AGPL-3',
    'summary': 'Quarterly payroll demo runs 2023Q4-2027Q4 for the shared demo company.',
    'description': '''
Payroll Demo Data
=================

Payroll runs for the shared demo company (l10n_se_demo_company), one
quarter at a time, 2023Q4 to 2027Q4.

Each quarter is a gzipped JSON file under data/payslips/. Loading a
quarter creates one payslip run per month, one payslip per employee who
was employed that month, computes the payslips, posts them in the payroll
journal and pays the net wage from the bank.

The sequence rule (load forward, remove backward) lives in demo.dataset,
owned by l10n_se_demo_company. This module only knows how to turn a
quarter's JSON into payslips.

Features:

    - Extends Odoo: Builds on hr.payslip, hr.contract, demo.dataset.
    ''',
    'depends': [
        'l10n_se_demo_company',
        'l10n_se_hr_payroll_account',
        'l10n_se_payroll_taxtable',
    ],
    'data': [],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
