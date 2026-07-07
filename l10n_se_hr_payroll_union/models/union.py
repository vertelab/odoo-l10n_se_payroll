# -*- coding: utf-8 -*-
"""Swedish Union Fee Management (Fackavgifter).

Models:
- hr.union: Union organization registry
- hr.union.membership: Employee union membership
- hr.union.fee: Monthly union fee record
- hr.union.report: Union reporting file

Integrates with payslips for automatic deduction.
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
from datetime import date

_logger = logging.getLogger(__name__)


class HrUnion(models.Model):
    """Swedish union organization registry."""

    _name = 'hr.union'
    _description = 'Union / Fackförbund'
    _order = 'name'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    active = fields.Boolean(default=True)
    union_type = fields.Selection([
        ('lo', 'LO-förbund'),
        ('tco', 'TCO-förbund'),
        ('saco', 'Saco-förbund'),
        ('other', 'Övrigt'),
    ], string='Centralorganisation')

    # Payment details
    bankgiro = fields.Char(string='Bankgiro')
    plusgiro = fields.Char(string='Plusgiro')
    bank_account = fields.Char(string='Bankkonto')

    # Default fee
    default_fee_type = fields.Selection([
        ('fixed', 'Fast belopp'),
        ('percent', 'Procent av lön'),
        ('mixed', 'Blandat'),
    ], default='fixed')
    default_fee_amount = fields.Monetary(
        string='Avgift (SEK/mån)', currency_field='currency_id')
    default_fee_percent = fields.Float(string='Avgift (%)')
    max_fee = fields.Monetary(string='Maxavgift', currency_field='currency_id')

    currency_id = fields.Many2one('res.currency',
                                  default=lambda self: self.env.company.currency_id)

    # Contact
    contact_name = fields.Char(string='Kontaktperson')
    contact_email = fields.Char(string='E-post')
    contact_phone = fields.Char(string='Telefon')

    # Reporting
    report_format = fields.Selection([
        ('csv', 'CSV'),
        ('excel', 'Excel'),
        ('xml', 'XML'),
        ('none', 'None'),
    ], default='csv', string='Rapportformat')

    member_ids = fields.One2many('hr.union.membership', 'union_id',
                                 string='Members')

    note = fields.Text()

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Union code must be unique!'),
    ]


class HrUnionMembership(models.Model):
    """Employee membership in a union."""

    _name = 'hr.union.membership'
    _description = 'Union Membership'
    _order = 'union_id, employee_id'

    name = fields.Char(compute='_compute_name', store=True)
    employee_id = fields.Many2one('hr.employee', required=True,
                                  ondelete='cascade')
    union_id = fields.Many2one('hr.union', required=True)

    member_number = fields.Char(string='Medlemsnummer')
    date_start = fields.Date(string='Medlem sedan', required=True,
                             default=date.today)
    date_end = fields.Date(string='Medlem till')
    active = fields.Boolean(compute='_compute_active', store=True)

    # Fee settings (override union defaults)
    fee_type = fields.Selection([
        ('fixed', 'Fast belopp'),
        ('percent', 'Procent av lön'),
        ('union_default', 'Enligt förbund'),
    ], default='union_default')
    fee_amount = fields.Monetary(string='Avgift (SEK/mån)', currency_field='currency_id')
    fee_percent = fields.Float(string='Avgift (%)')

    # Payment method
    payment_method = fields.Selection([
        ('salary', 'Löneavdrag'),
        ('autogiro', 'Autogiro'),
        ('invoice', 'Faktura'),
    ], default='salary')

    fee_ids = fields.One2many('hr.union.fee', 'membership_id',
                              string='Avgiftshistorik')

    company_id = fields.Many2one('res.company',
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency',
                                  related='company_id.currency_id')

    @api.depends('employee_id', 'union_id')
    def _compute_name(self):
        for rec in self:
            if rec.employee_id and rec.union_id:
                rec.name = '%s — %s' % (
                    rec.employee_id.name, rec.union_id.name)
            else:
                rec.name = 'Nytt medlemskap'

    @api.depends('date_end')
    def _compute_active(self):
        today = date.today()
        for rec in self:
            rec.active = not rec.date_end or rec.date_end >= today

    def get_monthly_fee(self, gross_salary=None):
        """Calculate monthly union fee for payslip integration."""
        self.ensure_one()

        if self.fee_type == 'union_default':
            fee_type = self.union_id.default_fee_type
        else:
            fee_type = self.fee_type

        if fee_type == 'fixed':
            amount = self.fee_amount or self.union_id.default_fee_amount or 0.0
        elif fee_type == 'percent':
            rate = self.fee_percent or self.union_id.default_fee_percent or 0.0
            if gross_salary:
                amount = gross_salary * (rate / 100)
            else:
                amount = 0.0
        else:
            amount = 0.0

        # Cap at max fee
        max_fee = self.union_id.max_fee
        if max_fee and max_fee > 0:
            amount = min(amount, max_fee)

        return round(amount, 2)


class HrUnionFee(models.Model):
    """Monthly union fee record — deducted from payslip."""

    _name = 'hr.union.fee'
    _description = 'Union Fee Record'
    _order = 'date desc'

    membership_id = fields.Many2one('hr.union.membership', required=True,
                                    ondelete='cascade')
    employee_id = fields.Many2one('hr.employee',
                                  related='membership_id.employee_id', store=True)
    union_id = fields.Many2one('hr.union',
                               related='membership_id.union_id', store=True)

    date = fields.Date(required=True,
                       default=lambda self: date.today().replace(day=1))
    amount = fields.Monetary(string='Avgiftsbelopp', required=True, currency_field='currency_id')
    payslip_id = fields.Many2one('hr.payslip', string='Lönespec',
                                 ondelete='set null')
    is_paid = fields.Boolean(string='Betald')

    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    company_id = fields.Many2one('res.company',
                                 default=lambda self: self.env.company)


class HrUnionReport(models.Model):
    """Union reporting file — monthly/quarterly report per union."""

    _name = 'hr.union.report'
    _description = 'Union Report'
    _order = 'date desc'

    name = fields.Char(required=True)
    union_id = fields.Many2one('hr.union', required=True)
    date = fields.Date(required=True,
                       default=lambda self: date.today().replace(day=1))
    period_type = fields.Selection([
        ('monthly', 'Månatlig'),
        ('quarterly', 'Kvartalsvis'),
    ], default='monthly', required=True)

    date_start = fields.Date(required=True)
    date_stop = fields.Date(required=True)

    line_ids = fields.One2many('hr.union.report.line', 'report_id',
                               string='Medlemmar')
    total_amount = fields.Monetary(string='Totalt belopp',
                                   compute='_compute_total', store=True,
                                   currency_field='currency_id')

    report_file = fields.Binary(string='Rapportfil', readonly=True)
    report_file_name = fields.Char(string='Filnamn')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('sent', 'Sent'),
    ], default='draft')

    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    company_id = fields.Many2one('res.company',
                                 default=lambda self: self.env.company)

    @api.depends('line_ids.amount')
    def _compute_total(self):
        for rec in self:
            rec.total_amount = sum(l.amount or 0.0 for l in rec.line_ids)

    def generate_report(self):
        """Generate report lines from fee records."""
        for rec in self:
            rec.line_ids.unlink()

            fees = self.env['hr.union.fee'].search([
                ('union_id', '=', rec.union_id.id),
                ('date', '>=', rec.date_start),
                ('date', '<=', rec.date_stop),
                ('is_paid', '=', True),
            ])

            # Group by employee
            employee_totals = {}
            for fee in fees:
                emp = fee.employee_id
                if emp.id not in employee_totals:
                    employee_totals[emp.id] = {
                        'employee_id': emp.id,
                        'personal_number': emp.identification_id or '',
                        'amount': 0.0,
                    }
                employee_totals[emp.id]['amount'] += fee.amount

            report_lines = []
            for emp_id, data in employee_totals.items():
                membership = self.env['hr.union.membership'].search([
                    ('employee_id', '=', emp_id),
                    ('union_id', '=', rec.union_id.id),
                    ('active', '=', True),
                ], limit=1)

                vals = {
                    'report_id': rec.id,
                    'employee_id': data['employee_id'],
                    'personal_number': data['personal_number'],
                    'member_number': membership.member_number or '',
                    'amount': data['amount'],
                }
                report_lines.append((0, 0, vals))

            rec.line_ids = report_lines
            rec.state = 'generated'

            # Generate CSV report file
            rec._generate_csv_file()

    def _generate_csv_file(self):
        """Generate CSV file for union reporting."""
        self.ensure_one()
        lines = ['Personnummer,Medlemsnummer,Namn,Belopp']
        for line in self.line_ids:
            rows = [
                line.personal_number or '',
                line.member_number or '',
                line.employee_id.name or '',
                str(int(line.amount or 0)),
            ]
            lines.append(','.join(rows))

        import base64
        csv_content = '\n'.join(lines)
        self.report_file = base64.b64encode(csv_content.encode('utf-8'))
        self.report_file_name = '%s_%s.csv' % (
            self.union_id.code,
            self.date.strftime('%Y%m'))


class HrUnionReportLine(models.Model):
    _name = 'hr.union.report.line'
    _description = 'Union Report Line'

    report_id = fields.Many2one('hr.union.report', required=True,
                                ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', required=True)
    personal_number = fields.Char()
    member_number = fields.Char()
    amount = fields.Monetary(string='Belopp', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='report_id.currency_id')


# ---- Extend existing models ----

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    union_membership_ids = fields.One2many('hr.union.membership',
                                           'employee_id',
                                           string='Fackmedlemskap')
    active_union_ids = fields.Many2many(
        'hr.union', compute='_compute_active_unions', store=True,
        string='Aktiva fackförbund')

    @api.depends('union_membership_ids', 'union_membership_ids.active',
                  'union_membership_ids.union_id')
    def _compute_active_unions(self):
        for emp in self:
            emp.active_union_ids = emp.union_membership_ids.filtered(
                lambda m: m.active).mapped('union_id')


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    union_fee_ids = fields.One2many('hr.union.fee', 'payslip_id',
                                    string='Fackavgifter')
