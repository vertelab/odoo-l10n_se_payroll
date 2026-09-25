# -*- coding: utf-8 -*-
{
    'name': 'Swedish Payroll — Collective Agreements',
    'version': '18.0.1.0.0',
    'summary': 'Collective agreement support: OB, overtime, vacation supplement, contractual pension.',
    'category': 'Payroll Localization',
    'description': '''
Swedish Payroll — Collective Agreements
=======================================

    Swedish collective agreement (kollektivavtal) support for l10n_se_payroll:

    Features:

        - UI Integration: Extends 2 view(s) in the Odoo interface.
        - Extends Odoo: Builds on hr.collective.agreement, hr.contract.
    ''',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se_payroll/l10n_se_hr_payroll_collective',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n-se-payroll',
    'depends': ['l10n_se_hr_payroll', 'l10n_se_hr_payroll_benefits'],
    'data': [
        'security/ir.model.access.csv',
        'data/collective_agreement_data.xml',
        'views/collective_agreement_views.xml',
        'views/hr_contract_views.xml',
    ],
    'auto_install': False,
    'installable': True,
}
