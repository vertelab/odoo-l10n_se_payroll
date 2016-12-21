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
    'name': 'HR Payslip Run',
    'category': 'Localization',
    'author': 'Vertel AB',
    'depends': ['hr_payroll', 'report_glabels'],
    'version': '1.0',
    'licence': 'AGPL-3',
    'summary': 'HR Payslip Run',
    'description': """
HR Payslip Run
==============
Generate a csv file for all selected employee payslip

    """,
    'auto_install': False,
    'website': 'http://vertel.se',
    'data':[
        'hr_payslip_run_data.xml',
    ],
    'demo':[
    ],
    'installable': True
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
