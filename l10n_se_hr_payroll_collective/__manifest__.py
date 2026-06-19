# -*- coding: utf-8 -*-
{
    'name': 'Swedish Payroll — Collective Agreements',
    'version': '1.0',
    'summary': 'Collective agreement support: OB, overtime, vacation supplement, contractual pension',
    'category': 'Payroll Localization',
    'description': """
Swedish collective agreement (kollektivavtal) support for l10n_se_payroll:

- Define agreement types (ITP, SAF-LO, Kommunal, etc.)
- Link agreements to employees/contracts
- Auto-calculate OB-tillägg, overtime, semestertillägg
- Salary rule templates per agreement type
- Agreement-based pension contributions
    """,
    'author': 'Vertel AB',
    'website': 'https://vertel.se',
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
