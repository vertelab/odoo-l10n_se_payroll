# -*- coding: utf-8 -*-
{
    'name': 'Swedish Payroll — Försäkringskassan Integration',
    'version': '18.0.1.0.0',
    'summary': 'Sick leave, VAB, parental leave — FK reimbursement tracking.',
    'category': 'Payroll Localization',
    'description': '''
Swedish Payroll — Försäkringskassan Integration
===============================================

    Swedish Social Insurance Agency (Försäkringskassan) integration for l10n_se_payroll:

    Features:

        - UI Integration: Extends 1 view(s) in the Odoo interface.
        - Extends Odoo: Builds on hr.fk.leave, mail.thread.
    ''',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se_payroll/l10n_se_hr_payroll_fk',
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
