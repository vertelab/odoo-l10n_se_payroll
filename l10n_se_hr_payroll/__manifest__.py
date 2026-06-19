# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2024- Vertel AB (<https://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'l10n_se_payroll: (Swedish Payroll)',
    'version': '0.1',
    # Version ledger: XX.0 = Odoo version. 1 = Major. Non regressionable code. 2 = Minor. New features that are regressionable. 3 = Bug fixes
    'summary': 'Swedish Payroll Rules.',
    'category': 'Payroll Localization',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se_payroll/l10n_se_hr_holidays_account',
    'images': ['static/description/banner.png'],  # 560x280 px.
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n_se_payroll',
    'depends': [
        'payroll',
        'account_period_vrtl', 
        'hr_timesheet_sheet',
        'hr_work_entry',
        'hr_work_entry_contract',
        'base_recompute_field',
    ],
    'description': """
Swedish Payroll Rules.
======================

    * Employee Details
    * Employee Contracts
    * Allowances/Deductions
    * Allow to configure Basic/Gross/Net Salary
    * Employee Payslip
    * Monthly Payroll Register
    * Integrated with Holiday Management


    This module depends on OCA:
    git@github.com:OCA/payroll.git
    git@github.com:OCA/timesheet.git
    git@github.com:OCA/web.git
    
    """,
    'auto_install': False,
    'data': [
        'data/hr_payroll_data.xml',
        'views/hr_payroll_view.xml',
        'report/hr_payroll_payslip_report.xml',
        #
        'data/hr_salary_rule_category_data.xml',
        'data/hr_salary_rule_data.xml',
        # Avkommentera nedanstående EFTER installation av holidays, 
        # sen uppgradera, för att få exempel-lönestrukturer och konstanter.
        #'data/hr_payroll_structure.xml', 
        # last
        'views/general_journal_view.xml',
        'views/hr_employee_views.xml',
        'views/hr_job_views.xml',
        'views/hr_payslip_template.xml',
        'views/hr_payslip_run_views.xml',
        # 'views/res_config_settings_views.xml',
        'views/user_payslip_views.xml',
        'views/hr_contract_views.xml',
        #'views/hr_leave_views.xml',
        'views/hr_payslip_views.xml',
        'security/ir.model.access.csv',
        'report/pivot_salary_views.xml',
        'security/hr_payslip_security.xml',
        'views/hr_pivot_views.xml',
        'views/res_company.xml',
        'views/vacation_debt_report_wizard_views.xml',
        'views/hr_payroll_salary_change_views.xml',
        'views/hr_payroll_correction_views.xml',
        'views/payroll_dashboard_views.xml',
        'report/hr_vacation_debt_report.xml',

    ],
    #'demo': [
        # ~ 'demo/hr_payroll_demo.xml',
    #    'demo/hr_payroll_demo.xml',
    #],
    'installable': True
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
