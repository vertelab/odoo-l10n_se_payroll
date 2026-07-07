# -*- coding: utf-8 -*-
"""Swedish Tax Statements (Kontrolluppgifter).

KU20: Salary, benefits, tax withheld per employee
KU25: Pension payments per employee

Generated annually and submitted to Skatteverket.
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from lxml import etree
import base64
import requests
import logging
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class AccountKuDeclaration(models.Model):
    """Annual tax statement declaration (KU)."""

    _name = 'account.ku.declaration'
    _inherit = 'account.declaration'
    _description = 'Kontrolluppgift (KU)'
    _report_name = 'KU'
    _order = 'date desc'

    ku_type = fields.Selection([
        ('ku20', 'KU20 — Lön & Förmåner'),
        ('ku25', 'KU25 — Pension'),
    ], string='KU-typ', required=True, default='ku20')

    year = fields.Integer(required=True,
                          default=lambda self: date.today().year - 1,
                          help='Income year for tax statement')

    line_ids = fields.One2many(
        'account.ku.declaration.line', 'ku_id', string='Anställda')

    ku_file = fields.Binary(string='KU-fil', readonly=True)
    ku_file_name = fields.Char(string='Filnamn', default='kontrolluppgifter.xml')

    # Summary
    employee_count = fields.Integer(
        string='Antal anställda', compute='_compute_totals', store=True)
    total_salary = fields.Monetary(
        string='Total bruttolön', compute='_compute_totals', store=True,
        currency_field='currency_id')
    total_benefits = fields.Monetary(
        string='Totala förmåner', compute='_compute_totals', store=True,
        currency_field='currency_id')
    total_tax = fields.Monetary(
        string='Total skatt', compute='_compute_totals', store=True,
        currency_field='currency_id')
    total_pension = fields.Monetary(
        string='Total pension', compute='_compute_totals', store=True,
        currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id')

    @api.depends('line_ids.salary_amount', 'line_ids.benefit_amount',
                  'line_ids.tax_amount', 'line_ids.pension_amount')
    def _compute_totals(self):
        for rec in self:
            rec.employee_count = len(rec.line_ids)
            rec.total_salary = sum(l.salary_amount or 0.0 for l in rec.line_ids)
            rec.total_benefits = sum(l.benefit_amount or 0.0 for l in rec.line_ids)
            rec.total_tax = sum(l.tax_amount or 0.0 for l in rec.line_ids)
            rec.total_pension = sum(l.pension_amount or 0.0 for l in rec.line_ids)

    @api.onchange('year', 'ku_type')
    def _onchange_year(self):
        if self.year:
            self.name = '%s %s' % (self._report_name, self.year)
            self.date_start = date(self.year, 1, 1)
            self.date_stop = date(self.year, 12, 31)
            self.date = date(self.year + 1, 1, 31)

    # ---- Main calculation ----

    def calculate(self):
        """Aggregate yearly payslip data per employee into KU lines."""
        for rec in self:
            if rec.state not in ('draft',):
                raise UserError(_(
                    "Cannot calculate in this state. Set to draft first."))

            rec.line_ids.unlink()

            # Find all done payslips for the year
            year_start = date(rec.year, 1, 1)
            year_end = date(rec.year, 12, 31)
            slips = self.env['hr.payslip'].search([
                ('date_from', '>=', year_start),
                ('date_to', '<=', year_end),
                ('state', 'in', ('done', 'paid')),
            ])

            if not slips:
                raise UserError(_(
                    "No done payslips found for year %s.") % rec.year)

            # Group by employee
            employee_data = {}
            salary_rule_codes = self._get_salary_rule_code_map()

            for slip in slips:
                emp = slip.employee_id
                if emp.id not in employee_data:
                    employee_data[emp.id] = {
                        'employee': emp,
                        'salary': 0.0,
                        'benefits': 0.0,
                        'tax': 0.0,
                        'pension': 0.0,
                        'deductions': 0.0,
                        'pension_premiums': 0.0,
                        'slip_count': 0,
                    }
                entry = employee_data[emp.id]
                entry['slip_count'] += 1

                for line in slip.line_ids:
                    code = line.salary_rule_id.code
                    amount = abs(line.total)
                    if not amount:
                        continue

                    if code in salary_rule_codes['salary']:
                        entry['salary'] += amount
                    if code in salary_rule_codes['benefit']:
                        entry['benefits'] += amount
                    if code in salary_rule_codes['tax']:
                        entry['tax'] += amount
                    if code in salary_rule_codes['pension']:
                        entry['pension'] += amount
                    if code in salary_rule_codes['pension_premium']:
                        entry['pension_premiums'] += amount

            # Build KU lines
            ku_lines = []
            for emp_id, data in employee_data.items():
                emp = data['employee']
                vals = {
                    'ku_id': rec.id,
                    'employee_id': emp.id,
                    'personal_number': emp.identification_id or '',
                    'salary_amount': round(data['salary']),
                    'benefit_amount': round(data['benefits']),
                    'tax_amount': round(data['tax']),
                    'pension_amount': round(data['pension']),
                    'pension_premium_amount': round(data['pension_premiums']),
                    'slip_count': data['slip_count'],
                }

                has_data = any(vals[k] for k in vals if k not in ('ku_id', 'employee_id', 'personal_number', 'slip_count'))
                if has_data:
                    ku_lines.append((0, 0, vals))

            if not ku_lines:
                raise UserError(_("No salary data to report for year %s.") % rec.year)

            rec.write({'line_ids': ku_lines, 'state': 'confirmed'})
            rec.generate_ku_file()

    def _get_salary_rule_code_map(self):
        """Map salary rule codes to KU categories."""
        return {
            'salary': {
                'GROSS', 'gl', 'bl', 'OB', 'OT', 'Overtime',
                'VACATION', 'SEMESTER', 'BONUS',
            },
            'benefit': {
                'BENEFIT', 'FORMAN', 'CAR', 'BIL', 'HOUSING', 'BOSTAD',
            },
            'tax': {
                'total_skatt', 'TAX', 'SKATT',
            },
            'pension': {
                'PENSION', 'PENS',
            },
            'pension_premium': {
                'PENSION_PREMIE', 'PENSPREMIE', 'TJANSTEPENSION',
            },
        }

    # ---- KU XML generation ----

    def generate_ku_file(self):
        """Generate KU XML for submission to Skatteverket."""
        for rec in self:
            rec.ku_file = None

            root = etree.Element('Kontrolluppgifter', Version='4.0')
            header = etree.SubElement(root, 'Huvud')
            orgnr = etree.SubElement(header, 'OrgNr')
            orgnr.text = rec.company_id.company_registry or ''
            year_el = etree.SubElement(header, 'Ar')
            year_el.text = str(rec.year)

            for line in rec.line_ids:
                if rec.ku_type == 'ku20':
                    ku_el = etree.SubElement(root, 'KU20')
                    pnr = etree.SubElement(ku_el, 'Personnummer')
                    pnr.text = line.personal_number or ''

                    if line.salary_amount:
                        salary = etree.SubElement(ku_el, 'Lon')
                        salary.text = str(int(line.salary_amount))
                    if line.benefit_amount:
                        benefit = etree.SubElement(ku_el, 'Forman')
                        benefit.text = str(int(line.benefit_amount))
                    if line.tax_amount:
                        tax_el = etree.SubElement(ku_el, 'AvdragenSkatt')
                        tax_el.text = str(int(line.tax_amount))

                elif rec.ku_type == 'ku25':
                    ku_el = etree.SubElement(root, 'KU25')
                    pnr = etree.SubElement(ku_el, 'Personnummer')
                    pnr.text = line.personal_number or ''

                    if line.pension_amount:
                        pens = etree.SubElement(ku_el, 'Pension')
                        pens.text = str(int(line.pension_amount))
                    if line.tax_amount:
                        tax_el = etree.SubElement(ku_el, 'AvdragenSkatt')
                        tax_el.text = str(int(line.tax_amount))

            xml_bytes = etree.tostring(
                root, pretty_print=True, encoding='UTF-8', xml_declaration=True)
            rec.ku_file = base64.b64encode(xml_bytes)

    # ---- SKV API submission (via same pattern as AGD) ----

    def action_send_to_skv(self):
        """Submit KU to Skatteverket via API."""
        self.ensure_one()

        if not self.ku_file:
            self.generate_ku_file()
        if not self.ku_file:
            raise UserError(_("No KU file. Run 'Calculate' first."))

        partner = self._get_skv_partner()
        if not partner or not partner.enable_skatteverket_api:
            raise UserError(_("No Skatteverket API partner configured."))

        access_token = self._get_skv_access_token(partner)
        settings = self._get_skv_settings()
        xml_bytes = base64.b64decode(self.ku_file)

        headers = {
            'Authorization': 'Bearer %s' % access_token,
            'Content-Type': 'application/xml; charset=UTF-8',
            'Accept': 'application/json',
        }

        try:
            response = requests.post(
                settings['api_url'], data=xml_bytes, headers=headers, timeout=30)
            if response.status_code in (200, 201, 202):
                self.write({
                    'skv_api_status': 'accepted',
                    'skv_response': response.text[:500],
                    'skv_submitted_date': fields.Datetime.now(),
                    'state': 'done',
                })
            else:
                self.write({
                    'skv_api_status': 'error',
                    'skv_response': 'HTTP %s: %s' % (
                        response.status_code, response.text[:500]),
                })
                raise UserError(_("SKV API error %s:\n%s")
                                % (response.status_code, response.text[:500]))
        except requests.exceptions.RequestException as e:
            self.write({
                'skv_api_status': 'error',
                'skv_response': str(e),
            })
            raise UserError(_("Connection error: %s") % str(e))

    # ---- Actions ----

    def action_download_ku_file(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s/%s/ku_file/%s?download=true' % (
                self._name, self.id, self.ku_file_name),
            'target': 'self',
        }

    # ---- Cron ----

    @api.model
    def _cron_create_ku(self):
        """Cron: create KU20 and KU25 for previous year in January."""
        today = date.today()
        prev_year = today.year - 1

        # Only run in January
        if today.month != 1:
            return False

        # Check if already created
        existing = self.search([
            ('year', '=', prev_year),
            ('ku_type', '=', 'ku20'),
        ], limit=1)
        if not existing:
            ku20 = self.create({
                'ku_type': 'ku20',
                'year': prev_year,
            })
            try:
                ku20.calculate()
                _logger.info('Cron: KU20 created for year %s', prev_year)
            except Exception as e:
                _logger.warning('Cron: KU20 calculation failed: %s', e)

        existing_ku25 = self.search([
            ('year', '=', prev_year),
            ('ku_type', '=', 'ku25'),
        ], limit=1)
        if not existing_ku25:
            ku25 = self.create({
                'ku_type': 'ku25',
                'year': prev_year,
            })
            try:
                ku25.calculate()
                _logger.info('Cron: KU25 created for year %s', prev_year)
            except Exception as e:
                _logger.warning('Cron: KU25 calculation failed: %s', e)

        return True


class AccountKuDeclarationLine(models.Model):
    _name = 'account.ku.declaration.line'
    _description = 'KU Declaration Line (per employee)'

    ku_id = fields.Many2one('account.ku.declaration', required=True,
                            ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', required=True)
    personal_number = fields.Char()

    # KU20 fields
    salary_amount = fields.Monetary('Bruttolön', currency_field='currency_id')
    benefit_amount = fields.Monetary('Förmåner', currency_field='currency_id')
    tax_amount = fields.Monetary('Avdragen skatt', currency_field='currency_id')

    # KU25 fields
    pension_amount = fields.Monetary('Pension', currency_field='currency_id')
    pension_premium_amount = fields.Monetary(
        'Pensionspremier', currency_field='currency_id')

    slip_count = fields.Integer('Antal lönespecar')

    currency_id = fields.Many2one('res.currency', related='ku_id.currency_id')


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    ku_declaration_id = fields.Many2one(
        'account.ku.declaration', string='KU',
        help="The KU declaration this payslip was included in.", readonly=True)
