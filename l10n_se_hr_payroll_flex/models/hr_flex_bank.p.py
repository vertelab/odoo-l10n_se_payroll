# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class HrFlexBank(models.Model):
    """Flextidspott — ackumulerar övertid/undertid för en anställd.
    
    Mönster: liknar hr.leave.allocation men timbaserad.
    Varje anställd har en aktiv pott per flexår.
    """
    _name = 'hr.flex.bank'
    _description = 'Flextidspott'
    _order = 'date_from desc, employee_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # -- Identitet ------------------------------------------------
    name = fields.Char(
        string='Namn',
        compute='_compute_name',
        store=True,
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Anställd',
        required=True,
        index=True,
        domain="[('company_id', '=', company_id)]",
    )
    company_id = fields.Many2one(
        'res.company',
        string='Företag',
        default=lambda self: self.env.company,
        required=True,
    )

    # -- Period ---------------------------------------------------
    date_from = fields.Date(
        string='Giltig fr.o.m.',
        required=True,
        default=lambda self: self._default_date_from(),
        help='Flexårets startdatum.',
    )
    date_to = fields.Date(
        string='Giltig t.o.m.',
        required=True,
        default=lambda self: self._default_date_to(),
        help='Flexårets slutdatum.',
    )

    # -- Saldo (compute) ------------------------------------------
    balance_hours = fields.Float(
        string='Aktuellt saldo (timmar)',
        compute='_compute_balance',
        store=True,
        help='Summan av alla transaktioner i potten.',
    )
    accrued_hours = fields.Float(
        string='Intjänade timmar',
        compute='_compute_balance',
        store=True,
    )
    used_hours = fields.Float(
        string='Uttagna timmar',
        compute='_compute_balance',
        store=True,
    )

    # -- Regler ---------------------------------------------------
    max_hours = fields.Float(
        string='Max timmar',
        default=100.0,
        help='Tak för potten. Överskjutande tid kan betalas ut per automatik.',
    )
    overtime_rate = fields.Float(
        string='Övertidsfaktor',
        default=1.0,
        help='Standardmultiplikator för övertid (1.0 = timme för timme).',
    )
    ordered_overtime_rate = fields.Float(
        string='Beordrad övertidsfaktor',
        default=1.5,
        help='Multiplikator för beordrad övertid (t.ex. 1.5 = +50%%).',
    )

    # -- Status ---------------------------------------------------
    state = fields.Selection([
        ('draft', 'Utkast'),
        ('active', 'Aktiv'),
        ('expired', 'Utgången'),
        ('closed', 'Stängd'),
    ], string='Status', default='draft', tracking=True, required=True)

    # -- Transaktioner --------------------------------------------
    line_ids = fields.One2many(
        'hr.flex.bank.line',
        'bank_id',
        string='Transaktioner',
    )

    # -- Constraints ----------------------------------------------
    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for bank in self:
            if bank.date_from > bank.date_to:
                raise ValidationError(
                    _('Startdatum får inte vara senare än slutdatum.'))

    @api.constrains('employee_id', 'date_from', 'date_to', 'state')
    def _check_overlapping_banks(self):
        for bank in self:
            if bank.state != 'active':
                continue
            overlapping = self.search([
                ('id', '!=', bank.id),
                ('employee_id', '=', bank.employee_id.id),
                ('state', '=', 'active'),
                ('date_from', '<=', bank.date_to),
                ('date_to', '>=', bank.date_from),
            ])
            if overlapping:
                raise ValidationError(
                    _('Det finns redan en aktiv flextidspott för %(employee)s '
                      'under denna period:\n%(overlap)s',
                      employee=bank.employee_id.name,
                      overlap='\n'.join(overlapping.mapped('name'))))

    # -- Compute --------------------------------------------
    @api.depends('employee_id', 'date_from')
    def _compute_name(self):
        for bank in self:
            emp = bank.employee_id.name or '?'
            bank.name = _('Flextidspott %(employee)s (%(start)s – %(end)s)',
                          employee=emp,
                          start=bank.date_from,
                          end=bank.date_to)

    @api.depends('line_ids.hours')
    def _compute_balance(self):
        for bank in self:
            accrued = sum(
                line.hours for line in bank.line_ids
                if line.hours > 0
            )
            used = abs(sum(
                line.hours for line in bank.line_ids
                if line.hours < 0
            ))
            bank.accrued_hours = accrued
            bank.used_hours = used
            bank.balance_hours = accrued - used

    # -- Defaults -------------------------------------------
    @api.model
    def _default_date_from(self):
        """Flexåret börjar 1 april, eller dagens datum."""
        today = date.today()
        if today.month >= 4:
            return date(today.year, 4, 1)
        else:
            return date(today.year - 1, 4, 1)

    @api.model
    def _default_date_to(self):
        """Flexåret slutar 31 mars året efter start."""
        today = date.today()
        if today.month >= 4:
            return date(today.year + 1, 3, 31)
        else:
            return date(today.year, 3, 31)

    # -- Actions --------------------------------------------
    def action_activate(self):
        self.write({'state': 'active'})

    def action_expire(self):
        self.write({'state': 'expired'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_draft(self):
        self.write({'state': 'draft'})

    # -- Transaktions-hjälp ---------------------------------
    def add_hours(self, hours, transaction_type, rate_factor=1.0,
                  source_sheet_id=None, note=''):
        """Lägg till timmar i potten (positiva = intjänade)."""
        self.ensure_one()
        if self.state not in ('draft', 'active'):
            raise UserError(_('Kan inte lägga till timmar i en %s pott.')
                            % self.state)
        self.env['hr.flex.bank.line'].create({
            'bank_id': self.id,
            'date': fields.Date.today(),
            'hours': hours,
            'transaction_type': transaction_type,
            'rate_factor': rate_factor,
            'source_sheet_id': source_sheet_id,
            'note': note,
        })

    def deduct_hours(self, hours, transaction_type, source_leave_id=None,
                     source_correction_id=None, note=''):
        """Dra timmar från potten (negativa transaktioner)."""
        self.ensure_one()
        if self.state not in ('draft', 'active'):
            raise UserError(_('Kan inte dra timmar från en %s pott.')
                            % self.state)
        self.env['hr.flex.bank.line'].create({
            'bank_id': self.id,
            'date': fields.Date.today(),
            'hours': -hours,
            'transaction_type': transaction_type,
            'rate_factor': 1.0,
            'source_leave_id': source_leave_id,
            'source_correction_id': source_correction_id,
            'note': note,
        })

    # -- Hjälpmetoder för att hitta rätt pott ---------------
    @api.model
    def _get_active_bank(self, employee):
        """Returnera den aktiva flextidspotten för en anställd.
        Om ingen finns, skapa en ny."""
        today = fields.Date.today()
        bank = self.search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'active'),
            ('date_from', '<=', today),
            ('date_to', '>=', today),
        ], limit=1)
        if not bank:
            bank = self.search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'draft'),
            ], limit=1, order='date_from desc')
        if not bank:
            bank = self.create({
                'employee_id': employee.id,
                'state': 'active',
            })
        elif bank.state == 'draft':
            bank.action_activate()
        return bank


class HrFlexBankLine(models.Model):
    """En transaktion i flextidspotten.
    
    Positiva timmar = intjäning (övertid, beordrad övertid)
    Negativa timmar = uttag (ledighet, löneutbetalning, undertid)
    """
    _name = 'hr.flex.bank.line'
    _description = 'Flextidstransaktion'
    _order = 'date desc, id desc'
    _rec_name = 'description'

    bank_id = fields.Many2one(
        'hr.flex.bank',
        string='Flextidspott',
        required=True,
        ondelete='cascade',
        index=True,
    )
    employee_id = fields.Many2one(
        'hr.employee',
        related='bank_id.employee_id',
        store=True,
        index=True,
    )
    company_id = fields.Many2one(
        'res.company',
        related='bank_id.company_id',
        store=True,
    )
    date = fields.Date(
        string='Datum',
        required=True,
        default=fields.Date.today,
    )
    hours = fields.Float(
        string='Timmar',
        required=True,
        help='Positivt = intjänat, Negativt = uttag.',
    )
    transaction_type = fields.Selection([
        ('overtime', 'Övertid (enkel)'),
        ('ordered_overtime', 'Övertid (beordrad)'),
        ('undertime', 'Undertid'),
        ('leave_taken', 'Uttag som ledighet'),
        ('salary_payout', 'Uttag som lön'),
        ('adjustment', 'Korrigering'),
        ('rollover', 'Överfört från föregående år'),
    ], string='Typ', required=True)
    rate_factor = fields.Float(
        string='Faktor',
        default=1.0,
        help='Multiplikator för timmarna (1.0 = rakt av, 1.5 = +50%%, 2.0 = +100%%).',
    )
    source_sheet_id = fields.Many2one(
        'hr_timesheet.sheet',
        string='Tidrapport',
        help='Tidrapporten som genererade denna transaktion.',
    )
    source_leave_id = fields.Many2one(
        'hr.leave',
        string='Ledighet',
        help='Ledigheten som detta uttag avser.',
    )
    source_correction_id = fields.Many2one(
        'hr.payroll.correction',
        string='Lönekorrigering',
        help='Lönekorrigeringen som utbetalningen avser.',
    )
    note = fields.Text(string='Notering')
    description = fields.Char(
        string='Beskrivning',
        compute='_compute_description',
        store=True,
    )

    @api.depends('date', 'hours', 'transaction_type', 'rate_factor')
    def _compute_description(self):
        for line in self:
            sign = '+' if line.hours >= 0 else ''
            rate_info = ''
            if line.rate_factor != 1.0 and line.hours > 0:
                raw = line.hours / line.rate_factor
                rate_info = _(' (%.1ft × %.1f)') % (raw, line.rate_factor)
            type_name = dict(self._fields['transaction_type'].selection).get(
                line.transaction_type, line.transaction_type)
            line.description = '%s%s tim %s%s' % (
                sign,
                line.hours,
                type_name,
                rate_info,
            )
