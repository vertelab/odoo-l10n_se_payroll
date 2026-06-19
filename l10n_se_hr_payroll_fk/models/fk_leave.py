# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class HrFkLeave(models.Model):
    _name = 'hr.fk.leave'
    _description = 'FK Leave Period'
    _order = 'date_start desc, employee_id'
    _inherit = ['mail.thread']

    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True)
    contract_id = fields.Many2one(
        'hr.contract', string='Contract',
        compute='_compute_contract', store=True)

    leave_type = fields.Selection([
        ('sick', 'Sick Leave (Sjuklön)'),
        ('sick_fk', 'Sick Leave FK (Sjukpenning)'),
        ('vab', 'VAB (Vård av barn)'),
        ('parental', 'Parental Leave (Föräldraledighet)'),
        ('rehab', 'Rehabilitation (Rehab)'),
    ], string='Type', required=True, default='sick')

    date_start = fields.Date(string='From', required=True)
    date_end = fields.Date(string='To', required=True)

    karens_day = fields.Boolean(
        string='Karensdag',
        help='First sick day deduction applies')

    employer_days = fields.Integer(
        string='Employer Days',
        compute='_compute_days', store=True,
        help='Days employer pays (first 14 for sick leave)')

    fk_days = fields.Integer(
        string='FK Days',
        compute='_compute_days', store=True,
        help='Days FK reimburses (after employer period)')

    employer_amount = fields.Float(
        string='Employer Amount',
        compute='_compute_amounts', store=True)

    fk_amount = fields.Float(
        string='FK Amount',
        compute='_compute_amounts', store=True)

    fk_reimbursed = fields.Float(
        string='FK Reimbursed',
        help='Amount actually received from FK')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('reported', 'Reported to FK'),
        ('reimbursed', 'Reimbursed'),
        ('done', 'Closed'),
    ], string='State', default='draft', tracking=True)

    note = fields.Text(string='Notes')
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id')

    @api.depends('employee_id')
    def _compute_contract(self):
        for rec in self:
            rec.contract_id = rec.employee_id.contract_id

    @api.depends('leave_type', 'date_start', 'date_end', 'karens_day')
    def _compute_days(self):
        for rec in self:
            if not rec.date_start or not rec.date_end:
                rec.employer_days = 0
                rec.fk_days = 0
                continue
            total = (rec.date_end - rec.date_start).days + 1
            if rec.karens_day:
                total -= 1
            if total <= 0:
                rec.employer_days = 0
                rec.fk_days = 0
                continue

            if rec.leave_type == 'sick':
                rec.employer_days = min(total, 14)
                rec.fk_days = max(total - 14, 0)
            elif rec.leave_type == 'sick_fk':
                rec.employer_days = 0
                rec.fk_days = total
            elif rec.leave_type in ('vab', 'parental', 'rehab'):
                rec.employer_days = 0
                rec.fk_days = total
            else:
                rec.employer_days = 0
                rec.fk_days = 0

    @api.depends('employer_days', 'fk_days', 'contract_id', 'contract_id.wage')
    def _compute_amounts(self):
        for rec in self:
            if not rec.contract_id or not rec.contract_id.wage:
                rec.employer_amount = 0.0
                rec.fk_amount = 0.0
                continue
            daily = rec.contract_id.wage / 26
            rec.employer_amount = rec.employer_days * daily
            # FK reimburses ~80% of daily wage up to a cap
            rec.fk_amount = rec.fk_days * daily * 0.8

    def action_report_to_fk(self):
        self.state = 'reported'

    def action_reimbursed(self):
        self.state = 'reimbursed'

    def action_close(self):
        self.state = 'done'
