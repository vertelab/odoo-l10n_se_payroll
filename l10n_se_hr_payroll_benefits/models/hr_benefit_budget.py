# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class HrBenefitBudget(models.Model):
    _name = 'hr.benefit.budget'
    _description = 'Förmånsbudget'
    _order = 'year desc, name'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Namn',
        required=True,
        help='T.ex. "Friskvårdsbidrag 2026", "Kompetensutveckling 2026"')

    code = fields.Char(
        string='Kod',
        required=True,
        help='Unik kod, t.ex. "friskvard_2026". Används för koppling till utlägg.')

    year = fields.Integer(
        string='År',
        required=True,
        default=lambda self: fields.Date.today().year)

    max_amount = fields.Float(
        string='Maxbelopp per anställd',
        required=True,
        default=5000.0,
        help='Högsta skattefria belopp per anställd och år')

    salary_rule_id = fields.Many2one(
        'hr.salary.rule',
        string='Löneregel',
        domain="[('code', '=like', 'frisk%')]",
        help='Löneregel som beräknar det skattefria nettolägget')

    active = fields.Boolean(string='Aktiv', default=True)

    line_ids = fields.One2many(
        'hr.benefit.budget.line',
        'budget_id',
        string='Anställdas budget')

    company_id = fields.Many2one(
        'res.company',
        string='Företag',
        default=lambda self: self.env.company)

    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id')

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Koden måste vara unik!'),
    ]

    def action_generate_lines(self):
        """Create budget lines for all active employees."""
        self.ensure_one()
        employees = self.env['hr.employee'].search([
            ('company_id', '=', self.company_id.id),
        ])
        for emp in employees:
            if not self.line_ids.filtered(lambda l: l.employee_id == emp):
                self.env['hr.benefit.budget.line'].create({
                    'budget_id': self.id,
                    'employee_id': emp.id,
                    'allocated_amount': self.max_amount,
                })

    def action_recompute_used(self):
        """Recalculate used amounts from expense lines."""
        for budget in self:
            for line in budget.line_ids:
                line._compute_used_amount()


class HrBenefitBudgetLine(models.Model):
    _name = 'hr.benefit.budget.line'
    _description = 'Anställds förmånsbudget'

    budget_id = fields.Many2one(
        'hr.benefit.budget',
        string='Budget',
        required=True,
        ondelete='cascade')

    employee_id = fields.Many2one(
        'hr.employee',
        string='Anställd',
        required=True)

    allocated_amount = fields.Float(
        string='Tilldelat belopp',
        required=True,
        help='Årlig budget för denna anställd')

    used_amount = fields.Float(
        string='Utnyttjat',
        compute='_compute_used_amount',
        store=True,
        help='Summa av godkända utlägg kopplade till denna budget')

    remaining_amount = fields.Float(
        string='Återstår',
        compute='_compute_remaining',
        store=True)

    company_id = fields.Many2one(
        related='budget_id.company_id')

    currency_id = fields.Many2one(
        related='budget_id.currency_id')

    @api.depends('budget_id.code', 'employee_id')
    def _compute_used_amount(self):
        """Sum approved expense lines linked to this budget code."""
        for line in self:
            if not line.budget_id.code:
                line.used_amount = 0.0
                continue
            # Find expense lines where analytic tag or reference matches budget code
            # Uses hr.expense module if available
            Expense = self.env.get('hr.expense')
            if Expense:
                expenses = Expense.search([
                    ('employee_id', '=', line.employee_id.id),
                    ('state', '=', 'done'),
                    ('date', '>=', f'{line.budget_id.year}-01-01'),
                    ('date', '<=', f'{line.budget_id.year}-12-31'),
                ])
                # Filter by analytic account or custom field matching budget code
                total = sum(expenses.filtered(
                    lambda e: line.budget_id.code in (e.analytic_distribution or '')
                ).mapped('total_amount'))
                line.used_amount = total
            else:
                line.used_amount = 0.0

    @api.depends('allocated_amount', 'used_amount')
    def _compute_remaining(self):
        for line in self:
            line.remaining_amount = line.allocated_amount - line.used_amount

    def action_apply_to_payslip(self, payslip):
        """Apply remaining budget as net allowance on payslip."""
        self.ensure_one()
        if self.remaining_amount <= 0:
            return
        code = f"friskvard_{self.budget_id.year}"
        input_vals = {
            'payslip_id': payslip.id,
            'name': self.budget_id.name,
            'code': code,
            'amount': self.remaining_amount,
            'contract_id': payslip.contract_id.id,
        }
        self.env['hr.payslip.input'].create(input_vals)
        return True
