# -*- coding: utf-8 -*-
{
    'name': 'Swedish Payroll — Försäkringskassan Integration',
    'version': '1.0',
    'summary': 'Sick leave, VAB, parental leave — FK reimbursement tracking',
    'category': 'Payroll Localization',
    'description': """
Swedish Social Insurance Agency (Försäkringskassan) integration for l10n_se_payroll:

- Track sick leave periods with karensdag calculation
- VAB (care of sick child) tracking
- Parental leave (föräldraledighet) tracking
- FK reimbursement amounts
- Reports for FK submission
    """,
    'author': 'Vertel AB',
    'website': 'https://vertel.se',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n-se-payroll',
    'depends': ['l10n_se_hr_payroll', 'l10n_se_hr_holidays'],
    'data': [
        'security/ir.model.access.csv',
        'views/fk_leave_views.xml',
    ],
    'auto_install': False,
    'installable': True,
}
