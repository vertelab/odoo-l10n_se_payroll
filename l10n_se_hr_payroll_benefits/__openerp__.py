# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2004-2016 Vertel AB (<http://vertel.se>).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Swedish - Schema Benefits',
    'category': 'Localization',
    'author': 'Vertel AB',
    'license': 'AGPL-3',
    'depends': ['l10n_se_hr_payroll','hr_payroll_benefits'],
    'version': '1.1',
    'description': """
Swedish Payslip additions for Benefits
    """,
    'website': 'http://www.vertel.se',
    'data':[
        'hr_salary_rule_data.xml',
    ],
    'auto_install': True,
    'installable': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
