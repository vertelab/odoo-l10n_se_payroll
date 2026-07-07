# -*- coding: utf-8 -*-
"""Detailed Swedish Occupational Pension Calculation.

Models:
- hr.pension.plan: Pension plan definition per collective agreement
- hr.pension.entry: Monthly pension entry per employee
- hr.pension.bracket: Wage bracket configuration
- Extends hr.contract with salary exchange (löneväxling)
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

# 2026 Swedish base amounts
IBB = 80600       # Inkomstbasbelopp
PBB = 48300       # Prisbasbelopp
FBB = 52500       # Förhöjt prisbasbelopp


class HrPensionPlan(models.Model):
    """Pension plan definition tied to collective agreement."""

    _name = 'hr.pension.plan'
    _description = 'Pension Plan'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    code = fields.Char(required=True)
    pension_type = fields.Selection([
        ('itp1', 'ITP 1'),
        ('itp2', 'ITP 2'),
        ('saflo', 'SAF-LO'),
        ('akap', 'AKAP-KL'),
        ('custom', 'Custom'),
    ], required=True)

    # Premium rates (in %)
    basic_rate = fields.Float(
        string='Basic Rate (%)', default=4.5,
        help='Pension premium up to first bracket limit')
    high_rate = fields.Float(
        string='High Rate (%)', default=30.0,
        help='Pension premium above first bracket limit')

    # SAF-LO specific
    saf_lo_flex_rate = fields.Float(
        string='SAF-LO Flex Rate (%)', default=1.0,
        help='Optional flex part for SAF-LO. Employee can choose 0-1% extra.')
    saf_lo_flex_max = fields.Float(
        string='SAF-LO Flex Max (%)', default=1.0)

    # AKAP-KL specific
    akap_variable_rate = fields.Float(
        string='AKAP-KL Variable Rate (%)', default=1.0,
        help='Variable component for AKAP-KL')

    # Bracket configuration
    bracket_ids = fields.One2many(
        'hr.pension.bracket', 'plan_id', string='Wage Brackets')

    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company)

    def compute_monthly_pension(self, employee, wage_basis, period_date):
        """Compute monthly pension for a given employee and wage basis."""
        self.ensure_one()
        brackets = self.bracket_ids.sorted('wage_from')

        if self.pension_type == 'itp1':
            return self._compute_itp1(wage_basis, brackets)
        elif self.pension_type == 'itp2':
            # ITP2 also needs employee age
            age = self._get_age(employee, period_date)
            return self._compute_itp2(wage_basis, brackets, age)
        elif self.pension_type == 'saflo':
            return self._compute_saflo(wage_basis, employee)
        elif self.pension_type == 'akap':
            return self._compute_akap(wage_basis, brackets)
        else:
            return {'total': 0.0, 'basic': 0.0, 'high': 0.0, 'flex': 0.0}

    def _compute_itp1(self, wage_basis, brackets):
        """ITP 1: 4.5% up to 7.5 IBB, 30% above."""
        limit_7_5_ibb = 7.5 * IBB  # 604 500 kr / year → 50 375 kr / month
        monthly_limit = limit_7_5_ibb / 12

        basic = min(wage_basis, monthly_limit)
        high = max(0, wage_basis - monthly_limit)

        result = {
            'wage_basic': basic,
            'wage_high': high,
            'premium_basic': basic * (self.basic_rate / 100),
            'premium_high': high * (self.high_rate / 100),
            'total': basic * (self.basic_rate / 100) + high * (self.high_rate / 100),
        }

        # Apply bracket overrides
        for bracket in brackets:
            bw_min = bracket.wage_from
            bw_max = bracket.wage_to or 99999999
            bw_range = min(wage_basis, bw_max) - max(0, bw_min)
            if bw_range > 0:
                result[bracket.code] = bw_range * (bracket.rate / 100)

        return result

    def _compute_itp2(self, wage_basis, brackets, age):
        """ITP 2: Age-based, complex calculation with 3 brackets.

        Born before 1979. Different rates depending on age at retirement.
        """
        limit_7_5 = 7.5 * IBB / 12
        limit_20 = 20 * IBB / 12
        limit_30 = 30 * IBB / 12

        low = min(wage_basis, limit_7_5)
        mid = min(max(0, wage_basis - limit_7_5), limit_20 - limit_7_5)
        high = max(0, wage_basis - limit_20)

        # ITP2 rates vary by birth year
        if age < 28:
            rate_low = 4.5
            rate_mid = 30.0
            rate_high = 30.0
        else:
            rate_low = 4.5
            rate_mid = 30.0
            rate_high = 30.0

        return {
            'wage_low': low,
            'wage_mid': mid,
            'wage_high': high,
            'premium_low': low * (rate_low / 100),
            'premium_mid': mid * (rate_mid / 100),
            'premium_high': high * (rate_high / 100),
            'total': (low * (rate_low / 100) +
                      mid * (rate_mid / 100) +
                      high * (rate_high / 100)),
        }

    def _compute_saflo(self, wage_basis, employee):
        """SAF-LO: 4.5% base, employee can choose flex up to 1%."""
        base = wage_basis * (self.basic_rate / 100)

        # Check employee flex selection
        flex_rate = employee.saf_lo_flex_rate or 0.0
        flex = wage_basis * (flex_rate / 100)

        return {
            'premium_basic': base,
            'premium_flex': flex,
            'total': base + flex,
            'flex_rate_used': flex_rate,
        }

    def _compute_akap(self, wage_basis, brackets):
        """AKAP-KL: 6.0% base + variable component."""
        base = wage_basis * (self.basic_rate / 100)
        variable = wage_basis * (self.akap_variable_rate / 100)

        return {
            'premium_basic': base,
            'premium_variable': variable,
            'total': base + variable,
        }

    def _get_age(self, employee, ref_date):
        """Calculate age at reference date."""
        if not employee.birthday:
            return 40
        age = ref_date.year - employee.birthday.year
        if (ref_date.month, ref_date.day) < (employee.birthday.month, employee.birthday.day):
            age -= 1
        return age


class HrPensionBracket(models.Model):
    """Wage bracket for pension premium calculation."""

    _name = 'hr.pension.bracket'
    _description = 'Pension Wage Bracket'
    _order = 'wage_from'

    plan_id = fields.Many2one('hr.pension.plan', required=True, ondelete='cascade')
    name = fields.Char(required=True)
    code = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    wage_from = fields.Float(string='Wage From (monthly)', required=True)
    wage_to = fields.Float(string='Wage To (monthly)',
                           help='Leave empty for no upper limit')
    rate = fields.Float(string='Rate (%)', required=True,
                        help='Pension premium rate for wage in this bracket')
    note = fields.Text()


class HrPensionEntry(models.Model):
    """Monthly pension premium entry per employee."""

    _name = 'hr.pension.entry'
    _description = 'Monthly Pension Entry'
    _order = 'date desc, employee_id'
    _rec_name = 'name'

    name = fields.Char(compute='_compute_name', store=True)
    employee_id = fields.Many2one('hr.employee', required=True)
    contract_id = fields.Many2one('hr.contract',
                                  related='employee_id.contract_id', store=True)
    plan_id = fields.Many2one(
        'hr.pension.plan', related='employee_id.contract_id.pension_plan_id', store=True)
    payslip_id = fields.Many2one('hr.payslip',
                                 string='Lönespec',
                                 ondelete='set null')
    date = fields.Date(required=True,
                       default=lambda self: date.today().replace(day=1))

    # Wage basis for the month
    wage_basis = fields.Monetary(string='Lönebas', currency_field='currency_id')
    exchanged_amount = fields.Monetary(string='Löneväxlat',
                                       currency_field='currency_id',
                                       help='Salary exchanged to pension this month')

    # Premium calculation results
    premium_basic = fields.Monetary(string='Grundpremie',
                                    currency_field='currency_id')
    premium_high = fields.Monetary(string='Högpremie',
                                   currency_field='currency_id')
    premium_flex = fields.Monetary(string='Flexpremie',
                                   currency_field='currency_id')
    premium_variable = fields.Monetary(string='Variabel premie',
                                       currency_field='currency_id')
    premium_total = fields.Monetary(string='Total premie',
                                    currency_field='currency_id')

    # Wage bracket breakdown (store as JSON or computed fields)
    wage_basic = fields.Monetary(string='Lön grund',
                                 currency_field='currency_id')
    wage_high = fields.Monetary(string='Lön hög',
                                currency_field='currency_id')
    wage_low = fields.Monetary(string='Lön låg (ITP2)',
                               currency_field='currency_id')
    wage_mid = fields.Monetary(string='Lön mellan (ITP2)',
                               currency_field='currency_id')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('calculated', 'Calculated'),
        ('done', 'Done'),
    ], default='draft')

    currency_id = fields.Many2one('res.currency',
                                  related='company_id.currency_id')
    company_id = fields.Many2one('res.company',
                                 default=lambda self: self.env.company)

    note = fields.Text()

    @api.depends('employee_id', 'date')
    def _compute_name(self):
        for rec in self:
            if rec.employee_id and rec.date:
                rec.name = '%s — %s' % (
                    rec.employee_id.name,
                    rec.date.strftime('%Y-%m'))
            else:
                rec.name = 'Ny pensionspost'

    def calculate(self):
        """Calculate pension premium for the month."""
        for rec in self:
            if not rec.plan_id:
                raise UserError(_(
                    "No pension plan assigned to employee %s.") % rec.employee_id.name)

            result = rec.plan_id.compute_monthly_pension(
                rec.employee_id, rec.wage_basis, rec.date)

            vals = {'state': 'calculated'}
            if 'premium_basic' in result:
                vals['premium_basic'] = result['premium_basic']
            if 'premium_high' in result:
                vals['premium_high'] = result['premium_high']
            if 'premium_flex' in result:
                vals['premium_flex'] = result['premium_flex']
            if 'premium_variable' in result:
                vals['premium_variable'] = result['premium_variable']
            if 'total' in result:
                vals['premium_total'] = result['total']
            if 'wage_basic' in result:
                vals['wage_basic'] = result['wage_basic']
            if 'wage_high' in result:
                vals['wage_high'] = result['wage_high']
            if 'wage_low' in result:
                vals['wage_low'] = result['wage_low']
            if 'wage_mid' in result:
                vals['wage_mid'] = result['wage_mid']

            rec.write(vals)


class HrPensionYearlySummary(models.Model):
    """Yearly pension summary per employee for årsbesked."""

    _name = 'hr.pension.yearly.summary'
    _description = 'Yearly Pension Summary'
    _order = 'year desc, employee_id'

    employee_id = fields.Many2one('hr.employee', required=True)
    year = fields.Integer(required=True,
                          default=lambda self: date.today().year)
    contract_id = fields.Many2one('hr.contract',
                                  related='employee_id.contract_id', store=True)
    plan_id = fields.Many2one(
        'hr.pension.plan', related='employee_id.contract_id.pension_plan_id', store=True)

    total_wage_basis = fields.Monetary(string='Årets lönebas',
                                       currency_field='currency_id')
    total_exchanged = fields.Monetary(string='Totalt löneväxlat',
                                      currency_field='currency_id')
    total_premium = fields.Monetary(string='Total premie',
                                    currency_field='currency_id')

    entry_ids = fields.One2many('hr.pension.entry', string='Månadsposter',
                                compute='_compute_entries')
    entry_count = fields.Integer(string='Antal poster',
                                 compute='_compute_entries')

    currency_id = fields.Many2one('res.currency',
                                  related='company_id.currency_id')
    company_id = fields.Many2one('res.company',
                                 default=lambda self: self.env.company)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('done', 'Done'),
    ], default='draft')

    @api.depends('employee_id', 'year')
    def _compute_entries(self):
        for rec in self:
            entries = self.env['hr.pension.entry'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('date', '>=', date(rec.year, 1, 1)),
                ('date', '<=', date(rec.year, 12, 31)),
                ('state', '=', 'done'),
            ])
            rec.entry_ids = entries
            rec.entry_count = len(entries)

    def calculate_summary(self):
        """Calculate yearly totals from monthly entries."""
        for rec in self:
            rec._compute_entries()
            rec.total_wage_basis = sum(
                e.wage_basis for e in rec.entry_ids)
            rec.total_exchanged = sum(
                e.exchanged_amount for e in rec.entry_ids)
            rec.total_premium = sum(
                e.premium_total for e in rec.entry_ids)
            rec.state = 'sent'


# ---- Model extensions ----

class HrContract(models.Model):
    _inherit = 'hr.contract'

    pension_plan_id = fields.Many2one(
        'hr.pension.plan', string='Pension Plan',
        help='Which pension plan applies to this contract')

    # Salary exchange (löneväxling)
    enable_salary_exchange = fields.Boolean(
        string='Enable Salary Exchange',
        help='Allow employee to exchange part of salary for pension contribution')
    salary_exchange_percent = fields.Float(
        string='Salary Exchange (%)',
        help='Percentage of gross salary exchanged to pension',
        default=0.0)
    salary_exchange_max = fields.Float(
        string='Max Exchange (SEK/month)',
        help='Maximum monthly amount to exchange')


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    saf_lo_flex_rate = fields.Float(
        string='SAF-LO Flex Rate (%)',
        help='Optional flex part for SAF-LO pension. 0.0-1.0%.')
    enable_salary_exchange = fields.Boolean(
        related='contract_id.enable_salary_exchange', readonly=False)
    salary_exchange_percent = fields.Float(
        related='contract_id.salary_exchange_percent', readonly=False)
    salary_exchange_max = fields.Float(
        related='contract_id.salary_exchange_max', readonly=False)


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    pension_entry_id = fields.Many2one(
        'hr.pension.entry', string='Pension Entry',
        help='The pension entry created from this payslip',
        readonly=True)
