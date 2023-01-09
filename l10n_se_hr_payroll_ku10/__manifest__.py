# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2021- Vertel AB (<https://vertel.se>).
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
    'name': 'l10n_se_payroll: Payroll KU10',
    'version': '14.0.1.0.0',
    # Version ledger: 14.0 = Odoo version. 1 = Major. Non regressionable code. 2 = Minor. New features that are regressionable. 3 = Bug fixes
    'summary': 'Swedish benefits, accounting codes.',
    'category': 'Payroll Localization',
    #'sequence': '1'
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/l10n_se_payroll/l10n_se_hr_payroll_ku10',
    'images': ['static/description/banner.png'], # 560x280 px.
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n-se-payroll',
    # ~ 'depends': ['l10n_se_hr_payroll_benefits', 'report_glabels', 'l10n_se_hr_payroll'],
    'depends': ['l10n_se_hr_payroll_benefits', 'l10n_se_hr_payroll'], ## report_glabels
    'description': """
Swedish Payroll Rules.
======================

    * KU10 
    
Förmåner (benefit codes)
========================
    * 041   Bostad småhus
    * 042   Kost
    * 043   Bostad, ej småhus
    * 044   Ränta
    * 045   Parkering
    * 047   Annan förman t. ex. Dagstidning
    * 013   Ange kod för förmansbil
    * 017   Betalt för bilförman
    * 021   RUT
    * 022   ROT
    
Kostnadsersattningar (salary rules/input fields)
================================================
    * 050 Bilersattning enligt schablon
    * 051 Traktamente inom riket
    * 052 Traktamente utom riket
    * 055 Resekostnader
    * 056 Logi
    * 053 Tjansteresa inrikes langre an tre manader
    * 054 Tjansteresa utrikes langre an tre manader
    
    """,

    'auto_install': False,
    'data':[
        'report_ku10_view.xml',
    ],
    'demo':[
    ],
    'installable': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
