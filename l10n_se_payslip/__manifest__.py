# -*- coding: utf-8 -*-
# © 2017 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
        'name': 'l10n_se Payroll Paysplip',
    'version': '1.0.0',
    'category': 'Human Resources',
    'license': 'AGPL-3',
    'summary': 'Sample py3o payslip reports',
    'description': """
HR Expense Report Py3o
======================

This module adds a sample py3o expense reports.

    """,
    'author': 'Vertel AB',
    'depends': [
        'report_py3o',
        'l10n_se_hr_payroll',
        ],
    'data': ['report.xml'],
    'installable': True,
}
