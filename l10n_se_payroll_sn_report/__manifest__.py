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
    'name': 'l10n_se_payroll_sn_report: (SN Lönestatistik & NYK-koder)',
    'version': '18.0.1.0.0',
    'summary': 'SN Lönestatistik rapport och NYK-koder för Svenskt Näringsliv',
    'category': 'Payroll Localization',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se_payroll/l10n_se_payroll_sn_report',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n_se_payroll',
    'depends': [
        'l10n_se_hr_payroll',
    ],
    'auto_install': False,
    'data': [
        'security/ir.model.access.csv',
        'data/hr_nyk_data.xml',
        'views/hr_nyk_views.xml',
        'wizard/sn_lonestatistik_wizard_views.xml',
        'report/sn_lonestatistik_report.xml',
    ],
    'installable': True,
    'application': False,
}
