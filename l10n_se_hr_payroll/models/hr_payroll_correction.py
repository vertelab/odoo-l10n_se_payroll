# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class HrPayrollCorrection(models.Model):
    _name = 'hr.payroll.correction'
    _description = 'Lönekorrigering'
    _order = 'date_from desc, employee_id'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Beskrivning',
        compute='_compute_name',
        store=True)

    employee_id = fields.Many2one(
        'hr.employee',
        string='Anställd',
        required=True,
        domain="[('company_id', '=', company_id)]")

    contract_id = fields.Many2one(
        'hr.contract',
        string='Kontrakt',
        compute='_compute_contract',
        store=True)

    company_id = fields.Many2one(
        'res.company',
        string='Företag',
        default=lambda self: self.env.company)

    salary_rule_id = fields.Many2one(
        'hr.salary.rule',
        string='Löneart',
        required=True,
        domain="[('appears_on_payslip', '=', True)]",
        help='Löneart som korrigeringen avser')

    amount = fields.Float(
        string='Belopp',
        required=True,
        help='Positivt = tillägg, negativt = avdrag')

    date_from = fields.Date(
        string='Gäller fr.o.m.',
        required=True,
        default=fields.Date.today,
        help='Första löneperiod korrigeringen ska gälla')

    date_to = fields.Date(
        string='Gäller t.o.m.',
        help='Sista löneperiod. Tomt = endast en period')

    reason = fields.Text(
        string='Anledning',
        help='T.ex. "Retroaktiv löneökning april-juni", "Felaktigt semesteravdrag mars"')

    state = fields.Selection([
        ('draft', 'Utkast'),
        ('done', 'Utförd'),
    ], string='Status', default='draft', tracking=True)

    payslip_id = fields.Many2one(
        'hr.payslip',
        string='Lönespecifikation',
        readonly=True,
        help='Lönespecen där korrigeringen applicerades')

    applied_date = fields.Date(
        string='Applicerades',
        readonly=True,
        help='Datum då korrigeringen lades på lönespec')

    note = fields.Text(string='Notering')

    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id')

    @api.depends('employee_id', 'salary_rule_id', 'amount', 'date_from')
    def _compute_name(self):
        for rec in self:
            emp = rec.employee_id.name or '?'
            rule = rec.salary_rule_id.name or '?'
            sign = '+' if rec.amount >= 0 else ''
            rec.name = f'{emp}: {sign}{rec.amount:,.0f} kr ({rule}) fr.o.m. {rec.date_from}'

    @api.depends('employee_id')
    def _compute_contract(self):
        for rec in self:
            rec.contract_id = rec.employee_id.contract_id

    def action_done(self):
        self.state = 'done'

    def action_draft(self):
        self.state = 'draft'
        self.payslip_id = False
        self.applied_date = False

    # ---- Called from payslip compute ----

    def _get_pending_corrections(self, employee, date_from, date_to):
        """Return pending corrections for an employee in a date range."""
        return self.search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'draft'),
            ('date_from', '<=', date_to),
            '|', ('date_to', '>=', date_from), ('date_to', '=', False),
        ])

    def _apply_to_payslip(self, payslip):
        """Apply corrections as payslip inputs and mark them as done."""
        for correction in self:
            input_vals = {
                'payslip_id': payslip.id,
                'input_type_id': correction.salary_rule_id.id,
                'amount': correction.amount,
            }
            # Find or create payslip input
            existing = payslip.input_line_ids.filtered(
                lambda i: i.input_type_id == correction.salary_rule_id)
            if existing:
                existing.amount += correction.amount
            else:
                payslip.input_line_ids = [(0, 0, input_vals)]

            correction.write({
                'state': 'done',
                'payslip_id': payslip.id,
                'applied_date': fields.Date.today(),
            })
