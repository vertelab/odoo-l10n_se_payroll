# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

import logging

_logger = logging.getLogger(__name__)


class BonusRequest(models.Model):
    """Bonus request with approval workflow for Swedish payroll.
    Workflow: Draft → Submitted → Dept Approved → Manager Approved → Accounting.
    Once accounting-approved, the bonus amount appears as an input line
    on the employee's payslip."""
    _name = 'bonus.request'
    _description = 'Bonus Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    reference = fields.Char(
        string='Reference', copy=False,
        help='Sequence number for the bonus request.')
    name = fields.Char(
        string='Description',
        help='Short description of this bonus request.')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('department_approved', 'Department Approved'),
        ('manager_approved', 'Manager Approved'),
        ('accounting', 'Accounting Approved'),
        ('rejected', 'Rejected'),
    ], string='State', default='draft', tracking=True,
       group_expand='_group_expand_states')

    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True, tracking=True)
    department_id = fields.Many2one(
        'hr.department', string='Department', store=True)
    job_id = fields.Many2one(
        'hr.job', string='Job', store=True)
    bonus_reason_id = fields.Many2one(
        'bonus.reason', string='Bonus Reason', required=True)
    bonus_amount = fields.Float(
        string='Bonus Amount', required=True, tracking=True)
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one(
        'res.company', string='Company', readonly=True,
        default=lambda self: self.env.company)

    # Approval tracking
    confirmed_user_id = fields.Many2one(
        'res.users', string='Confirmed by', readonly=True, copy=False)
    confirmed_date = fields.Date(
        string='Confirmed Date', readonly=True, copy=False)
    department_manager_id = fields.Many2one(
        'res.users', string='Department Head', readonly=True, copy=False)
    department_approved_date = fields.Date(
        string='Department Approved Date', readonly=True, copy=False)
    hr_manager_id = fields.Many2one(
        'res.users', string='Manager', readonly=True, copy=False)
    manager_approved_date = fields.Date(
        string='Manager Approved Date', readonly=True, copy=False)

    # Accounting
    journal_id = fields.Many2one(
        'account.journal', string='Bonus Journal',
        domain="[('type', '=', 'general')]",
        help='Journal for bonus accounting entries')
    credit_account_id = fields.Many2one(
        'account.account', string='Credit Account',
        help='Credit account for the journal entry.')
    debit_account_id = fields.Many2one(
        'account.account', string='Debit Account',
        help='Debit account for the journal entry.')
    move_id = fields.Many2one(
        'account.move', string='Journal Entry', readonly=True)

    # Payslip integration
    payslip_id = fields.Many2one(
        'hr.payslip', string='Payslip', readonly=True,
        help='Payslip where this bonus was applied.')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', 'New') == 'New':
                vals['reference'] = self.env['ir.sequence'].next_by_code(
                    'bonus.request') or 'New'
        return super().create(vals_list)

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.department_id = self.employee_id.department_id
            self.job_id = self.employee_id.job_id

    def _group_expand_states(self):
        return [key for key, _ in type(self).state.selection]

    def action_submit(self):
        self.write({
            'state': 'submitted',
            'confirmed_user_id': self.env.uid,
            'confirmed_date': fields.Date.today(),
        })

    def action_department_approve(self):
        self.write({
            'state': 'department_approved',
            'department_manager_id': self.env.uid,
            'department_approved_date': fields.Date.today(),
        })

    def action_manager_approve(self):
        self.write({
            'state': 'manager_approved',
            'hr_manager_id': self.env.uid,
            'manager_approved_date': fields.Date.today(),
        })

    def action_reject(self):
        self.state = 'rejected'

    def action_reset_to_draft(self):
        self.write({
            'state': 'draft',
            'confirmed_user_id': False,
            'confirmed_date': False,
            'department_manager_id': False,
            'department_approved_date': False,
            'hr_manager_id': False,
            'manager_approved_date': False,
        })

    def action_post_journal_entry(self):
        """Create and post a journal entry for the approved bonus."""
        self.ensure_one()
        if not self.journal_id or not self.credit_account_id or not self.debit_account_id:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Configuration Missing'),
                'res_model': 'bonus.request',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
            }
        move = self.env['account.move'].create({
            'ref': self.reference,
            'date': fields.Date.today(),
            'journal_id': self.journal_id.id,
            'line_ids': [
                (0, 0, {
                    'account_id': self.debit_account_id.id,
                    'debit': self.bonus_amount,
                    'name': '%s - %s' % (self.employee_id.name, self.reference),
                }),
                (0, 0, {
                    'account_id': self.credit_account_id.id,
                    'credit': self.bonus_amount,
                    'name': '%s - %s' % (self.employee_id.name, self.reference),
                }),
            ],
        })
        move.action_post()
        self.write({
            'move_id': move.id,
            'state': 'accounting',
        })

    def action_view_journal_entry(self):
        self.ensure_one()
        return {
            'name': _('Journal Entry'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.move_id.id,
        }
