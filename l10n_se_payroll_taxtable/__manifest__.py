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
    'name': 'l10n_se_payroll: Payroll Tax Table',
    'version': '14.0.1.0.0',
    'summary': 'https://skatteverket.entryscape.net/store/9/resource/1534',
    'category': 'Payroll Localization',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/l10n_se_payroll/l10n_se_payroll_taxtable',
    'images': ['static/description/banner.png'], # 560x280 px.
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n-se-payroll',
    'depends': ['l10n_se', 'hr_contract', 'l10n_se_hr_payroll'],
    'description': """
    To configure the tax table start with coping this link:
    https://skatteverket.entryscape.net/store/9/resource/1534
    Then go to Employee and chose in the sub menu Configuration.
    Click on Sync TaxTable and insert the link.
    Click on Sync and it's done.
    """,
    'auto_install': False,
    'demo': [],
    'data': [
        'security/ir.model.access.csv',
        'views/payroll_taxtable_view.xml',
        'views/hr_contract_view.xml',
        'data/ir_config.xml',
        # 'data/ir_server_action.xml',
    ],
    'installable': True
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
