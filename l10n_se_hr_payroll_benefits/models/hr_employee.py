# -*- coding: utf-8 -*-
from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    benefit_budget_line_ids = fields.One2many(
        'hr.benefit.budget.line',
        'employee_id',
        string='Benefit Budgets')
