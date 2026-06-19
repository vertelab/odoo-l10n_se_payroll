# -*- coding: utf-8 -*-
from odoo import _, fields, models, api
from datetime import date


class HrBenefitBudgetGenerate(models.TransientModel):
    _name = 'hr.benefit.budget.generate'
    _description = 'Generate Benefit Budget Lines'

    type_id = fields.Many2one(
        'hr.benefit.budget.type',
        string='Budget Type',
        required=True)

    name = fields.Char(
        string='Budget Name',
        compute='_compute_name', store=True, readonly=False)

    code = fields.Char(
        string='Code',
        compute='_compute_code', store=True, readonly=False)

    year = fields.Integer(
        string='Year',
        required=True,
        default=lambda self: date.today().year)

    max_amount = fields.Float(
        string='Amount per Employee',
        compute='_compute_max_amount', store=True, readonly=False,
        help='Yearly budget amount per employee')

    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company)

    department_id = fields.Many2one(
        'hr.department', string='Department',
        domain="[('company_id', '=', company_id)]")

    job_id = fields.Many2one(
        'hr.job', string='Job Position')

    employee_ids = fields.Many2many(
        'hr.employee', string='Employees',
        domain="[('company_id', '=', company_id)]")

    salary_rule_id = fields.Many2one(
        'hr.salary.rule', string='Salary Rule',
        domain="[('appears_on_payslip', '=', True)]")

    preview_text = fields.Text(
        string='Preview', readonly=True,
        compute='_compute_preview')

    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id')

    @api.onchange('type_id')
    def _onchange_type(self):
        if self.type_id:
            self.name = f"{self.type_id.name} {self.year}"
            self.code = f"{self.type_id.code}_{self.year}"
            self.max_amount = self.type_id.max_amount
            self.salary_rule_id = self.type_id.salary_rule_id

    @api.depends('type_id', 'year')
    def _compute_name(self):
        for wiz in self:
            if wiz.type_id and not wiz.name:
                wiz.name = f"{wiz.type_id.name} {wiz.year}"

    @api.depends('type_id', 'year')
    def _compute_code(self):
        for wiz in self:
            if wiz.type_id and not wiz.code:
                wiz.code = f"{wiz.type_id.code}_{wiz.year}"

    @api.depends('type_id')
    def _compute_max_amount(self):
        for wiz in self:
            if wiz.type_id and not wiz.max_amount:
                wiz.max_amount = wiz.type_id.max_amount

    @api.onchange('department_id', 'job_id')
    def _onchange_filter(self):
        domain = [('company_id', '=', self.company_id.id)]
        if self.department_id:
            domain.append(('department_id', '=', self.department_id.id))
        if self.job_id:
            domain.append(('job_id', '=', self.job_id.id))
        employees = self.env['hr.employee'].search(domain)
        self.employee_ids = [(6, 0, employees.ids)]

    @api.depends('employee_ids', 'max_amount')
    def _compute_preview(self):
        for wiz in self:
            if not wiz.employee_ids:
                wiz.preview_text = 'Select employees to preview.'
                continue
            lines = []
            name_w = max(len(e.name) for e in wiz.employee_ids)
            total = 0.0
            for emp in wiz.employee_ids.sorted('name'):
                lines.append(f'{emp.name:<{name_w}}  {wiz.max_amount:>10,.0f} kr')
                total += wiz.max_amount
            lines.append('─' * (name_w + 15))
            lines.append(f'{"Total":<{name_w}}  {total:>10,.0f} kr ({len(wiz.employee_ids)} employees)')
            wiz.preview_text = '\n'.join(lines)

    def action_generate(self):
        """Create budget and lines for selected employees."""
        self.ensure_one()
        Budget = self.env['hr.benefit.budget']
        BudgetLine = self.env['hr.benefit.budget.line']

        budget = Budget.create({
            'name': self.name,
            'code': self.code,
            'year': self.year,
            'max_amount': self.max_amount,
            'type_id': self.type_id.id,
            'salary_rule_id': self.salary_rule_id.id,
            'company_id': self.company_id.id,
        })

        count = 0
        for emp in self.employee_ids:
            if not budget.line_ids.filtered(lambda l: l.employee_id == emp):
                BudgetLine.create({
                    'budget_id': budget.id,
                    'employee_id': emp.id,
                    'allocated_amount': self.max_amount,
                })
                count += 1

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.benefit.budget',
            'res_id': budget.id,
            'view_mode': 'form',
            'target': 'current',
        }
