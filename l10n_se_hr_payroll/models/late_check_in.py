# -*- coding: utf-8 -*-
from odoo import api, fields, models


class LateCheckIn(models.Model):
    """Model to store late check-in records for Swedish payroll."""
    _name = 'late.check.in'
    _description = 'Late Check In'
    _order = 'date desc, id desc'

    name = fields.Char(
        readonly=True, string='Reference',
        help="Reference number of the record")
    employee_id = fields.Many2one(
        'hr.employee', string="Employee",
        required=True,
        help='Employee who arrived late')
    late_minutes = fields.Integer(
        string="Late Minutes",
        help='Number of minutes the employee was late')
    date = fields.Date(
        string="Date",
        help='Date of the late check-in')
    penalty_amount = fields.Float(
        compute="_compute_penalty_amount",
        string="Penalty Amount",
        help='Amount to be deducted from salary')
    state = fields.Selection(
        selection=[('draft', 'Draft'),
                   ('approved', 'Approved'),
                   ('refused', 'Refused'),
                   ('deducted', 'Deducted')],
        string="State", default="draft",
        help='State of the record')
    attendance_id = fields.Many2one(
        'hr.attendance', string='Attendance',
        help='Attendance record of the employee')
    company_id = fields.Many2one(
        'res.company', string='Company',
        related='employee_id.company_id', store=True)

    @api.model
    def create(self, vals_list):
        """Create a sequence for the model"""
        if not vals_list.get('name'):
            vals_list['name'] = self.env['ir.sequence'].next_by_code(
                'late.check.in') or '/'
        return super().create(vals_list)

    def _compute_penalty_amount(self):
        """Compute the penalty amount based on deduction type and amount."""
        config = self.env['ir.config_parameter'].sudo()
        amount = float(config.get_param(
            'l10n_se_hr_payroll.late_checkin_deduction_amount', default='0'))
        deduction_type = config.get_param(
            'l10n_se_hr_payroll.late_checkin_deduction_type', default='per_minute')
        for rec in self:
            if deduction_type == 'per_minute':
                rec.penalty_amount = amount * rec.late_minutes
            else:
                rec.penalty_amount = amount

    def action_approve(self):
        """Approve the late check-in record."""
        self.state = 'approved'

    def action_refuse(self):
        """Refuse the late check-in record."""
        self.state = 'refused'
