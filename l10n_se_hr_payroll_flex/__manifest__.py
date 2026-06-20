# -*- coding: utf-8 -*-
{
    'name': 'Swedish Payroll — Flextid / Timpott',
    'version': '1.0',
    'summary': 'Flextidsbank: övertid/undertid, beordrad övertid, timpott, uttag som ledighet eller lön',
    'category': 'Payroll Localization',
    'description': """
Swedish Flexitime Bank (Timpott) for l10n_se_payroll
=====================================================

Full flexitime management integrated with timesheets and payroll:

- **Overtime/Undertime detection**: Compares reported time against
  work schedule (resource.calendar) on the weekly timesheet
- **Ordered overtime**: Manager-designated overtime earns bonus
  hours (50% or 100% extra) into the time bank
- **Flexitime Bank (Timpott)**: Accumulates flex hours with full
  transaction history — similar to holiday allocations
- **Leave withdrawal**: Flex hours can be taken as time off,
  creating proper leave records that appear on the timesheet
- **Salary payout**: Employee requests conversion of flex hours
  to salary, creating a payroll correction on the next payslip
- **Project-linked overtime**: Overtime hours are associated with
  the project they were reported on
- **Flex year rollover**: Configurable flex year with carry-over
  rules (similar to holiday year handling)

Dependencies:
- OCA hr_timesheet_sheet (timesheet reporting)
- OCA payroll (salary rules engine)
- l10n_se_hr_payroll (Swedish payroll core)
- l10n_se_hr_holidays (optional, for leave integration)
    """,
    'author': 'Vertel AB',
    'website': 'https://vertel.se',
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
