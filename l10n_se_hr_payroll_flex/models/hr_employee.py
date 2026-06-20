# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    flex_bank_ids = fields.One2many(
        'hr.flex.bank',
        'employee_id',
        string='Flextidspotter',
    )

    flex_balance_hours = fields.Float(
        string='Flexsaldo (timmar)',
        compute='_compute_flex_balance',
        help='Totalt saldo över alla aktiva flextidspotter.',
    )

    @api.depends('flex_bank_ids.balance_hours', 'flex_bank_ids.state')
    def _compute_flex_balance(self):
        for emp in self:
            emp.flex_balance_hours = sum(
                bank.balance_hours
                for bank in emp.flex_bank_ids
                if bank.state == 'active'
            )
