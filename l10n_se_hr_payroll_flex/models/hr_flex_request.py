# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class HrFlexRequest(models.Model):
    """Anställds ansökan om flextidsuttag.
    
    Kan resultera i antingen:
    1. Ledighet (hr.leave) — frånvaro på tidrapporten
    2. Löneutbetalning (hr.payroll.correction) — extra pengar på lönespecen
    
    Mönster: kombinerar hr.leave (ansökan→godkännande) och
    hr.payroll.correction (appliceras på lönespec).
    """
    _name = 'hr.flex.request'
    _description = 'Flextidsansökan'
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # -- Identitet ------------------------------------------------
    name = fields.Char(
        string='Beskrivning',
        compute='_compute_name',
        store=True,
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Anställd',
        required=True,
        index=True,
        default=lambda self: self._default_employee(),
        domain="[('company_id', '=', company_id)]",
    )
    user_id = fields.Many2one(
        'res.users',
        related='employee_id.user_id',
        string='Användare',
        store=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Företag',
        default=lambda self: self.env.company,
        required=True,
    )

    # -- Typ ------------------------------------------------------
    request_type = fields.Selection([
        ('leave', 'Ledighet'),
        ('salary', 'Löneutbetalning'),
    ], string='Typ av uttag', required=True, default='leave')

    # -- Gemensamma fält ------------------------------------------
    bank_id = fields.Many2one(
        'hr.flex.bank',
        string='Flextidspott',
        required=True,
        domain="[('employee_id', '=', employee_id), ('state', '=', 'active')]",
        help='Vilken flextidspott timmarna ska dras från.',
    )
    hours = fields.Float(
        string='Timmar att ta ut',
        required=True,
        help='Antal timmar att ta ut från flextidspotten.',
    )
    available_hours = fields.Float(
        related='bank_id.balance_hours',
        string='Tillgängliga timmar',
    )

    # -- Ledighetsspecifika ---------------------------------------
    date_from = fields.Date(
        string='Från datum',
        help='Första ledighetsdagen.',
    )
    date_to = fields.Date(
        string='Till datum',
        help='Sista ledighetsdagen. Samma som från för en dag.',
    )

    # -- Löneutbetalningsspecifika --------------------------------
    salary_payout_amount = fields.Monetary(
        string='Belopp',
        currency_field='currency_id',
        compute='_compute_salary_payout_amount',
        store=True,
        help='Beräknat belopp baserat på timlön × timmar.',
    )
    salary_rule_id = fields.Many2one(
        'hr.salary.rule',
        string='Löneart',
        domain="[('appears_on_payslip', '=', True)]",
        help='Löneart för flextidsutbetalning.',
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
    )

    # -- Status / Flöde -------------------------------------------
    state = fields.Selection([
        ('draft', 'Utkast'),
        ('submitted', 'Inskickad'),
        ('approved', 'Godkänd'),
        ('rejected', 'Nekad'),
        ('done', 'Utförd'),
    ], string='Status', default='draft', tracking=True, required=True,
       copy=False)

    approved_by = fields.Many2one(
        'res.users',
        string='Godkänd av',
        readonly=True,
        tracking=True,
    )
    approved_date = fields.Date(
        string='Godkänd datum',
        readonly=True,
    )

    # -- Resultat ------------------------------------------------
    leave_id = fields.Many2one(
        'hr.leave',
        string='Ledighet',
        readonly=True,
        help='Ledigheten som skapades vid godkännande.',
    )
    correction_id = fields.Many2one(
        'hr.payroll.correction',
        string='Lönekorrigering',
        readonly=True,
        help='Lönekorrigeringen som skapades vid godkännande.',
    )
    note = fields.Text(string='Notering / Orsak')

    # -- Constraints ----------------------------------------------
    @api.constrains('hours', 'bank_id')
    def _check_hours_available(self):
        for req in self:
            if req.state in ('approved', 'done'):
                continue  # redan godkänd, går inte att ändra
            if req.hours > req.bank_id.balance_hours:
                raise ValidationError(
                    _('Du försöker ta ut %(requested).1f timmar, '
                      'men har bara %(available).1f timmar i potten.',
                      requested=req.hours,
                      available=req.bank_id.balance_hours))

    @api.constrains('request_type', 'date_from', 'date_to')
    def _check_leave_dates(self):
        for req in self:
            if req.request_type == 'leave' and not req.date_from:
                raise ValidationError(
                    _('Ledighetsdatum krävs vid uttag som ledighet.'))

    # -- Compute --------------------------------------------
    @api.depends('employee_id', 'request_type', 'hours')
    def _compute_name(self):
        for req in self:
            emp = req.employee_id.name or '?'
            type_map = dict(self._fields['request_type'].selection)
            type_name = type_map.get(req.request_type, '?')
            req.name = _('%(type)s: %(hours).1f h — %(emp)s',
                         type=type_name,
                         hours=req.hours,
                         emp=emp)

    @api.depends('hours', 'employee_id')
    def _compute_salary_payout_amount(self):
        for req in self:
            if req.request_type != 'salary' or not req.employee_id:
                req.salary_payout_amount = 0.0
                continue
            contract = req.employee_id.contract_id
            if not contract:
                req.salary_payout_amount = 0.0
                continue
            # Beräkna timlön från månadslön
            # Standard: månadslön / (veckoarbetstid × 4.33 veckor)
            weekly_hours = contract.resource_calendar_id.hours_per_week or 40.0
            monthly_hours = weekly_hours * 4.33
            hourly_rate = contract.wage / monthly_hours if monthly_hours else 0.0
            req.salary_payout_amount = req.hours * hourly_rate

    # -- Defaults -------------------------------------------
    @api.model
    def _default_employee(self):
        return self.env['hr.employee'].search([
            ('user_id', '=', self.env.uid),
            ('company_id', 'in', [self.env.company.id, False]),
        ], limit=1, order='company_id ASC')

    # -- State Actions ---------------------------------------
    def action_submit(self):
        """Skicka in ansökan till chef."""
        for req in self:
            if req.state != 'draft':
                raise UserError(_('Endast utkast kan skickas in.'))
            if req.hours <= 0:
                raise UserError(_('Antal timmar måste vara större än 0.'))
        self.write({'state': 'submitted'})

    def action_approve(self):
        """Godkänn ansökan och utför."""
        for req in self:
            if req.state != 'submitted':
                raise UserError(_('Endast inskickade ansökningar kan godkännas.'))

            if req.request_type == 'leave':
                req._approve_as_leave()
            elif req.request_type == 'salary':
                req._approve_as_salary()

            req.write({
                'approved_by': self.env.uid,
                'approved_date': fields.Date.today(),
            })

    def action_reject(self):
        """Neka ansökan."""
        for req in self:
            if req.state not in ('submitted',):
                raise UserError(_('Kan endast neka inskickade ansökningar.'))
        self.write({'state': 'rejected'})

    def action_draft(self):
        """Återställ till utkast."""
        for req in self:
            if req.state not in ('rejected',):
                raise UserError(_('Endast nekade ansökningar kan återställas.'))
        self.write({'state': 'draft'})

    # -- Interna godkännandemetoder --------------------------
    def _approve_as_leave(self):
        """Skapa en hr.leave och debitera potten."""
        self.ensure_one()

        # Hitta eller skapa leave type för flextid
        leave_type = self.env.ref(
            'l10n_se_hr_payroll_flex.leave_type_flex',
            raise_if_not_found=False,
        )
        if not leave_type:
            # Fallback: använd first legal leave type
            leave_type = self.env['hr.leave.type'].search([
                ('valid', '=', True),
            ], limit=1)
        if not leave_type:
            raise UserError(
                _('Ingen giltig frånvarotyp hittades för flextidsledighet. '
                  'Kontakta systemadministratören.'))

        leave_vals = {
            'name': _('Flextidsledighet: %(hours).1f h', hours=self.hours),
            'employee_id': self.employee_id.id,
            'holiday_status_id': leave_type.id,
            'date_from': self.date_from,
            'date_to': self.date_to or self.date_from,
            'number_of_days': 0,  # sätts av leave-modellen
        }
        leave = self.env['hr.leave'].create(leave_vals)
        # Flextidsansökan är redan godkänd — validera ledigheten direkt
        leave.sudo().action_validate()

        # Debitera potten
        self.bank_id.deduct_hours(
            hours=self.hours,
            transaction_type='leave_taken',
            source_leave_id=leave.id,
            note=_('Flextidsuttag som ledighet, godkänd %(date)s',
                   date=fields.Date.today()),
        )

        self.write({
            'state': 'done',
            'leave_id': leave.id,
        })

    def _approve_as_salary(self):
        """Skapa en hr.payroll.correction och debitera potten."""
        self.ensure_one()

        salary_rule = self.salary_rule_id
        if not salary_rule:
            # Hitta standardlöneart för flextidsuttag
            salary_rule = self.env.ref(
                'l10n_se_hr_payroll_flex.salary_rule_flex_payout',
                raise_if_not_found=False,
            )
        if not salary_rule:
            raise UserError(
                _('Ingen löneart konfigurerad för flextidsutbetalning. '
                  'Kontakta systemadministratören.'))

        # Skapa lönekorrigering
        correction = self.env['hr.payroll.correction'].create({
            'employee_id': self.employee_id.id,
            'salary_rule_id': salary_rule.id,
            'amount': self.salary_payout_amount,
            'date_from': fields.Date.today(),
            'reason': _('Flextidsutbetalning: %(hours).1f h × %(rate).2f kr/h '
                        '(godkänd %(date)s)',
                        hours=self.hours,
                        rate=self.salary_payout_amount / self.hours
                        if self.hours else 0,
                        date=fields.Date.today()),
        })

        # Debitera potten
        self.bank_id.deduct_hours(
            hours=self.hours,
            transaction_type='salary_payout',
            source_correction_id=correction.id,
            note=_('Flextidsuttag som lön, godkänd %(date)s. '
                   'Lönekorrigering #%(corr)d',
                   date=fields.Date.today(),
                   corr=correction.id),
        )

        self.write({
            'state': 'done',
            'correction_id': correction.id,
        })

    # -- Hjälp -------------------------------------------------
    def _get_approver(self):
        """Returnera chef/användare som ska godkänna."""
        self.ensure_one()
        parent = self.employee_id.parent_id
        if parent and parent.user_id:
            return parent.user_id
        # Fallback: HR manager group
        hr_group = self.env.ref('hr.group_hr_manager', raise_if_not_found=False)
        if hr_group:
            return hr_group.users[:1]
        return self.env.user
