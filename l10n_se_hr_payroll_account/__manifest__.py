# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2011- Vertel AB (<http://vertel.se>).
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
    'name': 'Sweden - Payroll with Accounting',
    'category': 'Localization',
    'author': 'Vertel AB',
    'depends': ['l10n_se_hr_payroll', 'hr_payroll_account_community', 'l10n_se'],
    'version': '1.0',
    'description': """
Accounting Data for Swedish Payroll Rules.
==========================================
    """,

    'auto_install': True,
    'website': 'https://www.odoo.com/page/accounting',
    'demo': [],
    'data':[
        #~ 'data/l10n_se_wizard.yml', # Leif
        'data/l10n_se_hr_salary_rule_data.xml',
        'views/l10n_se_hr_payroll_account_view.xml',
        # 'data/l10n_se_hr_payroll_account_data.xml',
        # 'data/hr.salary.rule.csv', # Leif
    ],
    'installable': True
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
