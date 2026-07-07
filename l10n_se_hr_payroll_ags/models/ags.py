# -*- coding: utf-8 -*-
"""AGS (Avtalsgruppsjukförsäkring) & TFA Insurance.

AGS: collective agreement sick pay insurance that complements FK
(Försäkringskassan) sick pay starting at day 91.

TFA: Trygghetsförsäkring vid arbetsskada (work injury insurance).

Models:
- hr.sick.leave.record: Extended sick leave tracking
- hr.ags.claim: AGS claim per sick leave period
- hr.tfa.case: TFA work injury case
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

# AGS qualification threshold: day 91 (inclusive)
AGS_QUALIFICATION_DAYS = 90  # Sick days needed before AGS kicks in (day 91+)

# AGS benefit parameters (2026)
AGS_PARAMETERS = {
    'max_daily_compensation': 804,  # Max AGS per day (SEK) — approximate
    'compensation_rate': 0.75,      # 75% of SGI up to ceiling
    'ceiling_monthly': 33125,       # AGS income ceiling per month (7.5 PBB)
    'max_days': 180,                # Max days per sick period (after day 90)
    'coordinated_with_fk': True,    # Coordinates with FK sjukpenning
}


class HrSickLeaveRecord(models.Model):
    """Extended sick leave record with AGS tracking."""

    _name = 'hr.sick.leave.record'
    _description = 'Sick Leave Record'
    _inherit = ['mail.thread']
    _order = 'date_start desc'

    name = fields.Char(compute='_compute_name', store=True)
    employee_id = fields.Many2one('hr.employee', required=True)
    contract_id = fields.Many2one('hr.contract',
                                  related='employee_id.contract_id', store=True)
    collective_agreement_id = fields.Many2one(
        'hr.collective.agreement',
        related='employee_id.contract_id.collective_agreement_id', store=True)

    date_start = fields.Date(required=True)
    date_end = fields.Date()
    is_ongoing = fields.Boolean(default=True)

    leave_type = fields.Selection([
        ('sick', 'Sick Leave'),
        ('sick_child', 'VAB (Care of Sick Child)'),
        ('work_injury', 'Work Injury'),
        ('occupational_disease', 'Occupational Disease'),
        ('rehabilitation', 'Rehabilitation'),
    ], default='sick', required=True)

    # FK integration
    fk_leave_id = fields.Many2one('hr.leave',
                                  string='FK Leave',
                                  help='Linked FK leave record')
    fk_case_number = fields.Char(string='FK Ärendenummer')

    # Day counter
    sick_days = fields.Integer(compute='_compute_sick_days', store=True)
    is_ags_qualified = fields.Boolean(
        compute='_compute_sick_days', store=True,
        help='True if this leave period has reached day 91+')

    # AGS claim
    ags_claim_id = fields.Many2one('hr.ags.claim', string='AGS Claim')

    # TFA (work injury)
    is_work_related = fields.Boolean(string='Work Related',
                                     help='Is this sick leave work-related?')
    tfa_case_id = fields.Many2one('hr.tfa.case', string='TFA Case')

    # Compensation tracking
    sgi_amount = fields.Monetary(string='SGI (Årsinkomst)',
                                 currency_field='currency_id')
    fk_daily_amount = fields.Monetary(string='FK Dagbelopp',
                                      currency_field='currency_id',
                                      compute='_compute_compensation', store=True)
    ags_daily_amount = fields.Monetary(string='AGS Dagbelopp',
                                       currency_field='currency_id',
                                       compute='_compute_compensation', store=True)
    total_fk_compensation = fields.Monetary(string='Summa FK-ersättning',
                                            currency_field='currency_id')
    total_ags_compensation = fields.Monetary(string='Summa AGS-ersättning',
                                             currency_field='currency_id')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('closed', 'Closed'),
    ], default='draft')

    currency_id = fields.Many2one('res.currency',
                                  related='company_id.currency_id')
    company_id = fields.Many2one('res.company',
                                 default=lambda self: self.env.company)

    note = fields.Text()

    @api.depends('employee_id', 'date_start')
    def _compute_name(self):
        for rec in self:
            if rec.employee_id and rec.date_start:
                rec.name = '%s — %s' % (
                    rec.employee_id.name,
                    rec.date_start.strftime('%Y-%m-%d'))
            else:
                rec.name = 'Ny sjukperiod'

    @api.depends('date_start', 'date_end', 'is_ongoing')
    def _compute_sick_days(self):
        """Calculate number of sick days including weekends."""
        for rec in self:
            if not rec.date_start:
                rec.sick_days = 0
                rec.is_ags_qualified = False
                continue

            end = rec.date_end or date.today()
            if isinstance(end, str):
                end = fields.Date.from_string(end)
            start = rec.date_start
            if isinstance(start, str):
                start = fields.Date.from_string(start)

            delta = (end - start).days + 1
            rec.sick_days = max(0, delta)
            rec.is_ags_qualified = rec.sick_days > AGS_QUALIFICATION_DAYS

    @api.depends('sgi_amount', 'is_ags_qualified')
    def _compute_compensation(self):
        """Calculate daily FK and AGS compensation."""
        for rec in self:
            if rec.sgi_amount and rec.sgi_amount > 0:
                daily_sgi = rec.sgi_amount / 365.0
                rec.fk_daily_amount = round(min(
                    daily_sgi * 0.80,
                    AGS_PARAMETERS['ceiling_monthly'] * 12 / 365 * 0.80))
            else:
                rec.fk_daily_amount = 0.0
                rec.ags_daily_amount = 0.0
                continue

            if rec.is_ags_qualified:
                # AGS fills gap between FK and ~90% of salary
                # Simplified: AGS = 15% of SGI up to ceiling
                monthly_ceiling = AGS_PARAMETERS['ceiling_monthly']
                daily_ceiling = (monthly_ceiling * 12) / 365
                daily_sgi = rec.sgi_amount / 365.0
                ags_gap = min(daily_sgi, daily_ceiling) * 0.15
                rec.ags_daily_amount = round(ags_gap)
            else:
                rec.ags_daily_amount = 0.0

    def action_close(self):
        """Close the sick leave period."""
        for rec in self:
            if not rec.date_end:
                rec.date_end = date.today()
            rec.is_ongoing = False
            rec.state = 'closed'

    def action_create_ags_claim(self):
        """Create AGS claim for this sick leave period."""
        self.ensure_one()
        if not self.is_ags_qualified:
            raise UserError(_(
                "AGS requires at least %d sick days. "
                "Current: %d days.") % (AGS_QUALIFICATION_DAYS, self.sick_days))

        if self.ags_claim_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'hr.ags.claim',
                'res_id': self.ags_claim_id.id,
                'view_mode': 'form',
                'target': 'current',
            }

        claim = self.env['hr.ags.claim'].create({
            'employee_id': self.employee_id.id,
            'sick_leave_id': self.id,
            'date_start': self.date_start,
            'date_end': self.date_end or date.today(),
            'sick_days_total': self.sick_days,
            'ags_qualifying_days': max(0, self.sick_days - AGS_QUALIFICATION_DAYS),
            'daily_amount': self.ags_daily_amount,
            'total_amount': self.ags_daily_amount * max(0, self.sick_days - AGS_QUALIFICATION_DAYS),
        })
        self.ags_claim_id = claim

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.ags.claim',
            'res_id': claim.id,
            'view_mode': 'form',
            'target': 'current',
        }


class HrAgsClaim(models.Model):
    """AGS insurance claim."""

    _name = 'hr.ags.claim'
    _description = 'AGS Claim'
    _inherit = ['mail.thread']
    _order = 'date_start desc'

    name = fields.Char(compute='_compute_name', store=True)
    employee_id = fields.Many2one('hr.employee', required=True)
    sick_leave_id = fields.Many2one('hr.sick.leave.record',
                                    string='Sick Leave Record')
    collective_agreement_id = fields.Many2one(
        'hr.collective.agreement',
        related='employee_id.contract_id.collective_agreement_id', store=True)

    date_start = fields.Date(required=True)
    date_end = fields.Date(required=True)
    sick_days_total = fields.Integer()
    ags_qualifying_days = fields.Integer(
        help='Number of AGS-qualifying days (day 91+)')

    daily_amount = fields.Monetary(string='Dagbelopp AGS',
                                   currency_field='currency_id')
    total_amount = fields.Monetary(string='Totalt AGS-belopp',
                                   currency_field='currency_id')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('rejected', 'Rejected'),
    ], default='draft')

    # AFA integration
    afa_case_number = fields.Char(string='AFA Ärendenummer')
    afa_submitted_date = fields.Datetime(string='Inskickat till AFA')
    afa_decision_date = fields.Datetime(string='AFA Beslutsdatum')

    currency_id = fields.Many2one('res.currency',
                                  related='company_id.currency_id')
    company_id = fields.Many2one('res.company',
                                 default=lambda self: self.env.company)

    note = fields.Text()

    @api.depends('employee_id', 'date_start')
    def _compute_name(self):
        for rec in self:
            if rec.employee_id and rec.date_start:
                rec.name = 'AGS — %s (%s)' % (
                    rec.employee_id.name,
                    rec.date_start.strftime('%Y-%m'))
            else:
                rec.name = 'Nytt AGS-ärende'

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_approve(self):
        self.write({'state': 'approved',
                    'afa_decision_date': fields.Datetime.now()})

    def action_pay(self):
        self.write({'state': 'paid'})


class HrTfaCase(models.Model):
    """TFA (Work Injury Insurance) case."""

    _name = 'hr.tfa.case'
    _description = 'TFA Case'
    _inherit = ['mail.thread']
    _order = 'injury_date desc'

    name = fields.Char(compute='_compute_name', store=True)
    employee_id = fields.Many2one('hr.employee', required=True)
    sick_leave_id = fields.Many2one('hr.sick.leave.record',
                                    string='Related Sick Leave')

    injury_date = fields.Date(required=True)
    injury_description = fields.Text(string='Injury Description', required=True)
    injury_type = fields.Selection([
        ('accident', 'Accident'),
        ('occupational_disease', 'Occupational Disease'),
        ('commuting', 'Commuting Accident'),
        ('other', 'Other'),
    ], default='accident', required=True)

    is_reported_to_afa = fields.Boolean(string='Reported to AFA')
    is_reported_to_arbetsmiljoverket = fields.Boolean(
        string='Reported to Arbetsmiljöverket')
    afa_case_number = fields.Char(string='AFA Case Number')

    # Compensation
    tfa_type = fields.Selection([
        ('medical_costs', 'Medical Costs'),
        ('lost_income', 'Lost Income'),
        ('permanent_disability', 'Permanent Disability'),
        ('death', 'Death Benefit'),
    ])
    claimed_amount = fields.Monetary(string='Claimed Amount',
                                     currency_field='currency_id')
    awarded_amount = fields.Monetary(string='Awarded Amount',
                                     currency_field='currency_id')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('reported', 'Reported'),
        ('investigating', 'Investigating'),
        ('decided', 'Decided'),
        ('paid', 'Paid'),
        ('closed', 'Closed'),
    ], default='draft')

    currency_id = fields.Many2one('res.currency',
                                  related='company_id.currency_id')
    company_id = fields.Many2one('res.company',
                                 default=lambda self: self.env.company)

    @api.depends('employee_id', 'injury_date')
    def _compute_name(self):
        for rec in self:
            if rec.employee_id and rec.injury_date:
                rec.name = 'TFA — %s (%s)' % (
                    rec.employee_id.name,
                    rec.injury_date.strftime('%Y-%m-%d'))
            else:
                rec.name = 'Nytt TFA-ärende'


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    sick_leave_record_ids = fields.One2many('hr.sick.leave.record',
                                            'employee_id',
                                            string='Sick Leave Records')
    ags_claim_ids = fields.One2many('hr.ags.claim',
                                    'employee_id', string='AGS Claims')
    tfa_case_ids = fields.One2many('hr.tfa.case',
                                   'employee_id', string='TFA Cases')

    # Aggregated stats
    total_sick_days_ytd = fields.Integer(
        compute='_compute_sick_stats',
        string='Sjukdagar i år')
    current_ags_qualified = fields.Boolean(
        compute='_compute_sick_stats',
        string='AGS-kvalificerad',
        help='Currently in AGS-qualifying sick leave (91+ days)')

    @api.depends('sick_leave_record_ids', 'sick_leave_record_ids.sick_days',
                  'sick_leave_record_ids.date_start', 'sick_leave_record_ids.is_ongoing')
    def _compute_sick_stats(self):
        today = date.today()
        year_start = date(today.year, 1, 1)
        for emp in self:
            year_records = emp.sick_leave_record_ids.filtered(
                lambda r: r.date_start and
                fields.Date.from_string(r.date_start) >= year_start)
            emp.total_sick_days_ytd = sum(
                r.sick_days for r in year_records if r.sick_days)
            emp.current_ags_qualified = any(
                r.is_ongoing and r.is_ags_qualified
                for r in emp.sick_leave_record_ids)
