# -*- coding: utf-8 -*-
{
    'name': 'Swedish Payroll — Flextid / Timpott',
    'version': '18.0.1.2.0',
    'summary': 'Flextidsbank: övertid/undertid, beordrad övertid, timpott, uttag som ledighet eller lön',
    'category': 'Payroll Localization',
    'description': '''
Swedish Payroll — Flextid / Timpott
===================================

    Full flexitime management integrated with timesheets and payroll:

    Dependencies:
    - OCA hr_timesheet_sheet (timesheet reporting)
    - OCA payroll (salary rules engine)
    - l10n_se_hr_payroll (Swedish payroll core)
    - l10n_se_hr_holidays (optional, for leave integration)

    Features:

        - Guided Wizards: Step-by-step dialogs for data entry.
        - Reports: Adds printable reports.
        - UI Integration: Extends 6 view(s) in the Odoo interface.
        - Extends Odoo: Builds on description, hr.contract, hr.employee, hr.flex.bank.
    ''',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se_payroll/l10n_se_hr_payroll_flex',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n-se-payroll',
    'depends': [
        'l10n_se_hr_payroll',
        'hr_timesheet_sheet',
        'hr_work_entry_contract',
        'hr_holidays',  # for leave withdrawal integration
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/hr_flex_data.xml',
        'data/hr_salary_rule_data_flex.xml',
        'views/hr_flex_bank_views.xml',
        'views/hr_flex_request_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_timesheet_sheet_views.xml',
        'views/hr_contract_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/hr_flex_request_wizard_views.xml',
        'report/hr_flex_report.xml',
    ],
    'demo': [],
    'auto_install': False,
    'installable': True,
    'application': False,
}
