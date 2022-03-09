# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2022- Vertel AB (<https://vertel.se>).
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
    'name': 'l10n_se_payroll: Swedish Payroll Credit Coupling',
    'version': '14.0.0.0.1',
    'summary': 'Extends payroll with a field that links between payslips and credited payslips',
    'category': 'Localization',
    'author': 'Vertel AB',
    'images': ['/static/description/banner.png'], # 560x280 px.
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n-se-payroll',
    'depends': ['account','account_period','l10n_se_hr_payroll','hr_payroll_account_community_fixed'],
    'description': """
Swedish Payroll Credit Coupling
===============================

Extends payroll with a field (coupled_payslip) that links between payslips and credited payslips.
It also adds a link between the payslip journals using a field (payment_move_id) created by
the "account_period" module.
    """,
    'auto_install': False,
    'data':[
        'views/hr_payslip_views.xml',
    ],
    'installable': True
}
