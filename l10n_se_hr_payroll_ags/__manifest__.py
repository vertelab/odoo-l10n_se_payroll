# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2026- Vertel AB.
#    License AGPL-3.
#
##############################################################################

{
    'name': 'l10n_se_hr_payroll_ags: AGS & TFA Insurance',
    'version': '18.0.1.0.0',
    'summary': 'AGS (sick pay insurance) and TFA (work injury) — tracking & reporting',
    'category': 'Payroll Localization',
    'author': 'Vertel AB',
    'website': 'https://vertel.se',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n-se-payroll',
    'description': """
AGS (Avtalsgruppsjukförsäkring) & TFA Insurance
===============================================

AGS complements the Swedish social insurance (FK) for long-term sick leave
(day 91+). TFA covers work-related injuries.

Features:
---------
* Track sick leave periods per employee (from hr.holidays / FK)
* Calculate AGS eligibility and amounts
* Day 91+ tracking with AGS qualification
* AGS compensation: complements FK sjukpenning
* TFA injury case tracking
* Integration with FK (Försäkringskassan) module
* Monthly premium basis for AFA Försäkring reporting
* Historical sick leave register
    """,
    'depends': [
        'l10n_se_hr_payroll',
        'l10n_se_hr_payroll_collective',
        'l10n_se_hr_payroll_fk',
        'l10n_se_payroll_fora',
        'payroll', 'hr', 'hr_holidays',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/ags_views.xml',
        'data/ags_data.xml',
    ],
    'auto_install': False,
    'installable': True,
}
