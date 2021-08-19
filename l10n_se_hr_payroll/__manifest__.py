# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2014- Vertel AB (<http://vertel.se>).
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Swedish - Payroll',
    'category': 'Localization',
    'author': 'Vertel AB',
    'depends': ['hr_payroll_community','hr_contract_types'],
    'version': '1.2',
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
    """,

    'auto_install': False,
    'website': 'http://www.vertel.se',
    'data':[
        'data/hr_payroll_data.xml',
        'views/hr_payroll_view.xml',
        'data/hr_payroll_data.xml',
        'report/hr_payroll_payslip_report.xml',
        #
        'data/hr_salary_rule_category_data.xml',
        'data/hr_salary_rule_data.xml',
        # last
        'data/hr_payroll_stucture_simple_data.xml',
        'demo/hr_payroll_demo.xml',
    ],
    'demo':[
        # ~ 'demo/hr_payroll_demo.xml',
    ],
    'installable': True
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
