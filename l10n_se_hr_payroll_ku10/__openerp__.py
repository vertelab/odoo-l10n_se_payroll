# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2004-2015 Vertel AB (<http://vertel.se>).
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
    'name': 'Swedish - Payroll KU10',
    'category': 'Localization',
    'author': 'Vertel AB',
    'license': 'AGPL-3',
    'depends': ['l10n_se_hr_payroll','l10n_se_hr_payroll_benefits', 'report_glabels'],
    'version': '1.2',
    'description': """
Swedish Payroll Rules.
======================

    * KU10 
    
Formaner (benefit codes)
========================
    * 041	Bostad småhus
    * 042	Kost	
    * 043	Bostad ej småhus	
    * 044	Ranta	
    * 045	Parkering
    * 047	Annan forman t ex Dagstidning
    * 013	ange kod för formansbil
    * 017	Betalt för bilforman
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
    'website': 'http://www.vertel.se',
    'data':[
        'report_ku10_view.xml',
    ],
    'demo':[
    ],
    'installable': True
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
