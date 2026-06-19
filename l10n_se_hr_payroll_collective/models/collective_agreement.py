# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class HrCollectiveAgreement(models.Model):
    _name = 'hr.collective.agreement'
    _description = 'Collective Agreement'
    _order = 'name'

    name = fields.Char(string='Agreement Name', required=True)
    code = fields.Char(string='Code', required=True)
    active = fields.Boolean(string='Active', default=True)

    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company)

    # ---- OB (uncomfortable working hours) ----
    ob_evening_rate = fields.Float(
        string='OB Evening Rate (%)',
        default=20.0,
        help='Extra pay percentage for evening hours (e.g. after 18:00)')
    ob_weekend_rate = fields.Float(
        string='OB Weekend Rate (%)',
        default=50.0,
        help='Extra pay percentage for weekend work')
    ob_night_rate = fields.Float(
        string='OB Night Rate (%)',
        default=70.0,
        help='Extra pay percentage for night hours (e.g. 22:00-06:00)')
    ob_holiday_rate = fields.Float(
        string='OB Holiday Rate (%)',
        default=100.0,
        help='Extra pay percentage for public holidays')

    # ---- Overtime ----
    overtime_simple_rate = fields.Float(
        string='Simple Overtime (%)',
        default=50.0,
        help='Enkel övertid — first overtime hours')
    overtime_qualified_rate = fields.Float(
        string='Qualified Overtime (%)',
        default=100.0,
        help='Kvalificerad övertid — additional overtime hours')

    # ---- Vacation supplement ----
    vacation_supplement_pct = fields.Float(
        string='Vacation Supplement (%)',
        default=0.8,
        help='Semestertillägg per day — typically 0.8% of monthly wage')
    vacation_supplement_min = fields.Float(
        string='Vacation Supplement Min/Day (kr)',
        default=0.0,
        help='Minimum vacation supplement per day if set by agreement')

    # ---- Pension ----
    pension_type = fields.Selection([
        ('itp1', 'ITP 1 (born 1979+)'),
        ('itp2', 'ITP 2 (born before 1979)'),
        ('saflo', 'SAF-LO'),
        ('akap', 'AKAP-KL'),
        ('none', 'None'),
    ], string='Pension Type')
    pension_premium_pct = fields.Float(
        string='Pension Premium (%)',
        default=4.5,
        help='Monthly pension premium as % of wage')

    # ---- Insurance ----
    insurance_tgl = fields.Boolean(string='TGL (Group Life)', default=True)
    insurance_tfa = fields.Boolean(string='TFA (Work Injury)', default=True)

    note = fields.Text(string='Notes')

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Agreement code must be unique!'),
    ]


class HrContract(models.Model):
    _inherit = 'hr.contract'

    collective_agreement_id = fields.Many2one(
        'hr.collective.agreement',
        string='Collective Agreement',
        help='Which collective agreement applies to this contract')

    # OB computed from work entries
    ob_evening_hours = fields.Float(
        string='OB Evening (h)',
        compute='_compute_ob_hours', store=True,
        help='Evening hours this month (from work entries)')
    ob_weekend_hours = fields.Float(
        string='OB Weekend (h)',
        compute='_compute_ob_hours', store=True)
    ob_night_hours = fields.Float(
        string='OB Night (h)',
        compute='_compute_ob_hours', store=True)

    # Overtime from work entries
    overtime_simple_hours = fields.Float(
        string='Simple OT (h)',
        compute='_compute_overtime_hours', store=True)
    overtime_qualified_hours = fields.Float(
        string='Qualified OT (h)',
        compute='_compute_overtime_hours', store=True)

    @api.depends('employee_id', 'date_start', 'date_end')
    def _compute_ob_hours(self):
        """Compute OB hours from work entries (placeholder)."""
        for contract in self:
            contract.ob_evening_hours = 0.0
            contract.ob_weekend_hours = 0.0
            contract.ob_night_hours = 0.0

    @api.depends('employee_id', 'date_start', 'date_end')
    def _compute_overtime_hours(self):
        """Compute overtime hours from work entries (placeholder)."""
        for contract in self:
            contract.overtime_simple_hours = 0.0
            contract.overtime_qualified_hours = 0.0
