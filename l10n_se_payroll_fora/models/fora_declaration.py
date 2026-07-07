# -*- coding: utf-8 -*-
"""FORA — Collective Insurance & Pension Premium Reporting.

Aggregates payroll data per employee per collective agreement per period,
computes FORA insurance premiums, generates FORA XML files, and submits
to FORA's API.

Premium Categories (by collective agreement):
- TGL: Tjänstegrupplivförsäkring (Group Life Insurance)
- TFA: Trygghetsförsäkring vid arbetsskada (Work Injury Insurance)
- AGS: Avtalsgruppsjukförsäkring (Sick Pay Insurance)
- AGB: Avgångsbidrag (Severance Pay Insurance)
- Avtalspension: SAF-LO / ITP1 / ITP2 / AKAP-KL

FORA premium rates (2026):
  SAF-LO:
    TGL: 0.15% of gross wages
    TFA: 0.02% of gross wages
    AGS: 0.30% of gross wages
    AGB: 0.10% of gross wages
    Avtalspension: 4.5% of gross wages

  ITP1:
    TGL: 0.15% of gross wages
    Avtalspension: 4.5% up to 7.5 IBB, 30% above 7.5 IBB

  ITP2:
    TGL: 0.15% of gross wages
    Avtalspension: age-based, complex calculation

  AKAP-KL:
    TGL: 0.15% of gross wages
    Avtalspension: 6.0% of gross wages
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from lxml import etree
import base64
import requests
import logging
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)

# FORA premium rate tables (2026)
# These are the standard rates; can be overridden per agreement.
FORA_RATES = {
    'saflo': {
        'tgl': 0.0015,      # 0.15% TGL
        'tfa': 0.0002,      # 0.02% TFA
        'ags': 0.0030,      # 0.30% AGS
        'agb': 0.0010,      # 0.10% AGB
        'avtalspension': 0.045,   # 4.5% Avtalspension
    },
    'itp1': {
        'tgl': 0.0015,
        'avtalspension_basic': 0.045,    # 4.5% up to 7.5 IBB
        'avtalspension_high': 0.30,      # 30% above 7.5 IBB
        'ibb_limit': 7.5,                # multiplier of IBB
        'ibb_amount': 80600,             # 2026 IBB (inkomstbasbelopp) = 80 600 kr
    },
    'itp2': {
        'tgl': 0.0015,
        'avtalspension_low': 0.045,      # up to 7.5 IBB
        'avtalspension_mid': 0.30,       # 7.5-20 IBB
        'avtalspension_high': 0.30,      # 20-30 IBB
        'ibb_limit_low': 7.5,
        'ibb_limit_mid': 20,
        'ibb_limit_high': 30,
        'ibb_amount': 80600,
    },
    'akap': {
        'tgl': 0.0015,
        'avtalspension': 0.06,    # 6.0% Avtalspension
    },
}

# 2026 base amounts (Swedish "basbelopp" / income base amounts)
IBB_2026 = 80600   # Inkomstbasbelopp
PBB_2026 = 48300   # Prisbasbelopp


class AccountForaDeclaration(models.Model):
    _name = 'account.fora.declaration'
    _inherit = 'account.declaration'
    _description = 'FORA Premium Declaration'
    _report_name = 'FORA'
    _order = 'date desc'

    payslip_run_id = fields.Many2one(
        'hr.payslip.run', string='Lönekörning',
        help="The salary batch this FORA declaration is based on.")

    line_ids = fields.One2many(
        'account.fora.declaration.line', 'fora_id',
        string='Anställda')

    fora_file = fields.Binary(string='FORA-fil', readonly=True)
    fora_file_name = fields.Char(
        string='Filnamn', default='fora_premier.xml')

    # Summary fields (computed from line_ids)
    employee_count = fields.Integer(
        string='Antal anställda', compute='_compute_totals', store=True)
    total_wage_basis = fields.Monetary(
        string='Total lönebas', compute='_compute_totals', store=True,
        currency_field='currency_id')
    total_tgl_premium = fields.Monetary(
        string='Total TGL-premie', compute='_compute_totals', store=True,
        currency_field='currency_id')
    total_tfa_premium = fields.Monetary(
        string='Total TFA-premie', compute='_compute_totals', store=True,
        currency_field='currency_id')
    total_ags_premium = fields.Monetary(
        string='Total AGS-premie', compute='_compute_totals', store=True,
        currency_field='currency_id')
    total_agb_premium = fields.Monetary(
        string='Total AGB-premie', compute='_compute_totals', store=True,
        currency_field='currency_id')
    total_pension_premium = fields.Monetary(
        string='Total pensionspremie', compute='_compute_totals', store=True,
        currency_field='currency_id')
    total_premium = fields.Monetary(
        string='Total premie', compute='_compute_totals', store=True,
        currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id')

    # FORA-specific reporting fields
    fora_report_type = fields.Selection([
        ('monthly', 'Månadsrapport'),
        ('quarterly', 'Kvartalsrapport'),
        ('annual', 'Årsrapport (slutlikvid)'),
    ], string='Rapporttyp', default='monthly', required=True)

    fora_case_number = fields.Char(
        string='FORA Ärendenummer',
        help="Reference number from FORA (after submission).")
    fora_submitted_date = fields.Datetime(
        string='FORA Inskickat',
        help="When this declaration was submitted to FORA.")

    @api.depends(
        'line_ids.wage_basis', 'line_ids.tgl_premium',
        'line_ids.tfa_premium', 'line_ids.ags_premium',
        'line_ids.agb_premium', 'line_ids.pension_premium',
    )
    def _compute_totals(self):
        for rec in self:
            rec.employee_count = len(rec.line_ids)
            rec.total_wage_basis = sum(
                (l.wage_basis or 0.0) for l in rec.line_ids)
            rec.total_tgl_premium = sum(
                (l.tgl_premium or 0.0) for l in rec.line_ids)
            rec.total_tfa_premium = sum(
                (l.tfa_premium or 0.0) for l in rec.line_ids)
            rec.total_ags_premium = sum(
                (l.ags_premium or 0.0) for l in rec.line_ids)
            rec.total_agb_premium = sum(
                (l.agb_premium or 0.0) for l in rec.line_ids)
            rec.total_pension_premium = sum(
                (l.pension_premium or 0.0) for l in rec.line_ids)
            rec.total_premium = (
                rec.total_tgl_premium +
                rec.total_tfa_premium +
                rec.total_ags_premium +
                rec.total_agb_premium +
                rec.total_pension_premium
            )

    @api.onchange('date_start', 'date_stop')
    def _onchange_period_dates(self):
        if self.date_start and self.date_stop:
            self.name = '%s %s' % (
                self._report_name,
                fields.Date.from_string(self.date_start).strftime('%Y-%m'))

    @api.onchange('payslip_run_id')
    def _onchange_payslip_run(self):
        """Auto-fill date range from payslip run."""
        if self.payslip_run_id:
            run = self.payslip_run_id
            self.date_start = run.date_start
            self.date_stop = run.date_end
            if run.date_end:
                self.date = self._calculate_fora_deadline(run.date_end)

    # ---- Main calculation ----

    def calculate(self):
        """Aggregate payslips per employee and compute FORA premiums."""
        for rec in self:
            if rec.state not in ('draft',):
                raise UserError(_(
                    "Du kan inte beräkna i denna status, ändra till utkast."))

            # Clear existing lines
            rec.line_ids.unlink()

            # Find payslips
            if rec.payslip_run_id:
                slips = rec.payslip_run_id.slip_ids.filtered(
                    lambda s: s.state in ('done', 'paid'))
            else:
                slips = self.env['hr.payslip'].search([
                    ('date_from', '>=', rec.date_start),
                    ('date_to', '<=', rec.date_stop),
                    ('state', 'in', ('done', 'paid')),
                ])

            if not slips:
                raise UserError(_(
                    "Inga färdiga lönespecar hittades för perioden %s - %s.")
                    % (rec.date_start, rec.date_stop))

            # Group by employee
            employee_data = {}
            for slip in slips:
                emp = slip.employee_id
                if emp.id not in employee_data:
                    employee_data[emp.id] = {
                        'employee': emp,
                        'slips': self.env['hr.payslip'],
                    }
                employee_data[emp.id]['slips'] |= slip

            # Build FORA lines
            salary_rule_codes = self._get_salary_rule_code_map()
            fora_lines = []
            ibb = IBB_2026

            for emp_id, data in employee_data.items():
                emp = data['employee']
                contract = emp.contract_id
                if not contract:
                    continue

                agreement = contract.collective_agreement_id
                if not agreement:
                    # Employees without collective agreement are not reported to FORA
                    continue

                # Determine age and pension type
                age = self._get_employee_age(emp, rec.date_stop)
                pension_type = agreement.pension_type

                # Calculate wage basis
                wage_basis = 0.0
                for slip in data['slips']:
                    for line in slip.line_ids:
                        code = line.salary_rule_id.code
                        amount = abs(line.total)
                        if not amount:
                            continue
                        if code in salary_rule_codes['wage_basis']:
                            wage_basis += amount

                if wage_basis <= 0:
                    continue

                # Get FORA rates for this agreement's pension type
                rates = FORA_RATES.get(pension_type, {})

                # Compute premiums
                vals = {
                    'fora_id': rec.id,
                    'employee_id': emp.id,
                    'personal_number': emp.identification_id or '',
                    'collective_agreement_id': agreement.id,
                    'pension_type': pension_type,
                    'age_group': self._get_age_group(age),
                    'wage_basis': round(wage_basis),
                }

                # TGL basic (usually 0.15%, applies to most agreements)
                tgl_rate = rates.get('tgl', 0.0)
                vals['tgl_premium'] = round(wage_basis * tgl_rate)

                # TFA
                tfa_rate = rates.get('tfa', 0.0)
                vals['tfa_premium'] = round(wage_basis * tfa_rate)

                # AGS
                ags_rate = rates.get('ags', 0.0)
                vals['ags_premium'] = round(wage_basis * ags_rate)

                # AGB
                agb_rate = rates.get('agb', 0.0)
                vals['agb_premium'] = round(wage_basis * agb_rate)

                # Avtalspension — varies by pension type
                if pension_type == 'saflo':
                    vals['pension_premium'] = round(
                        wage_basis * rates.get('avtalspension', 0.045))

                elif pension_type == 'itp1':
                    limit = rates.get('ibb_limit', 7.5) * ibb
                    basic = min(wage_basis, limit)
                    high = max(0, wage_basis - limit)
                    vals['pension_wage_basic'] = round(basic)
                    vals['pension_wage_high'] = round(high)
                    vals['pension_premium'] = round(
                        basic * rates.get('avtalspension_basic', 0.045) +
                        high * rates.get('avtalspension_high', 0.30)
                    )

                elif pension_type == 'itp2':
                    limit_low = rates.get('ibb_limit_low', 7.5) * ibb
                    limit_mid = rates.get('ibb_limit_mid', 20) * ibb
                    limit_high = rates.get('ibb_limit_high', 30) * ibb
                    low_wage = min(wage_basis, limit_low)
                    mid_wage = min(max(0, wage_basis - limit_low), limit_mid - limit_low)
                    high_wage = max(0, wage_basis - limit_mid)
                    vals['pension_wage_low'] = round(low_wage)
                    vals['pension_wage_mid'] = round(mid_wage)
                    vals['pension_wage_high'] = round(high_wage)
                    vals['pension_premium'] = round(
                        low_wage * rates.get('avtalspension_low', 0.045) +
                        mid_wage * rates.get('avtalspension_mid', 0.30) +
                        high_wage * rates.get('avtalspension_high', 0.30)
                    )

                elif pension_type == 'akap':
                    vals['pension_premium'] = round(
                        wage_basis * rates.get('avtalspension', 0.06))
                else:
                    vals['pension_premium'] = 0.0

                fora_lines.append((0, 0, vals))

            if not fora_lines:
                raise UserError(_(
                    "Inga anställda med kollektivavtal hittades under perioden."))

            rec.write({'line_ids': fora_lines, 'state': 'confirmed'})
            rec.generate_fora_file()

    def _get_salary_rule_code_map(self):
        """Map salary rule codes to FORA wage basis categories.

        Override to customize which salary codes form the basis
        for FORA premium calculation.
        """
        return {
            # Codes that should be included in the FORA wage basis
            'wage_basis': {
                'GROSS', 'gl', 'bl',        # Gross salary
                'OB', 'OT', 'Overtime',     # OB/overtime
                'BENEFIT', 'FORMAN',        # Taxable benefits
                'VACATION', 'SEMESTER',     # Vacation pay
                'BONUS',                    # Bonuses
            },
        }

    def _get_age_group(self, age):
        """Return age group for FORA reporting."""
        if age < 26:
            return 'under_26'
        elif age < 65:
            return 'working_age'
        elif age < 80:
            return 'senior'
        else:
            return 'pensioner'

    def _get_employee_age(self, employee, date_stop):
        """Calculate age at end of declaration period."""
        if not employee.birthday:
            return 40
        stop = (fields.Date.from_string(date_stop)
                if isinstance(date_stop, str) else date_stop)
        age = stop.year - employee.birthday.year
        if (stop.month, stop.day) < (employee.birthday.month, employee.birthday.day):
            age -= 1
        return age

    # ---- FORA XML generation ----

    def generate_fora_file(self):
        """Generate FORA XML for insurance and pension premium reporting.

        FORA XML format follows FORA's standard structure with:
        - Company information (orgnr, period)
        - Employee-level data per agreement type
        - Insurance and pension premium amounts
        """
        for rec in self:
            rec.fora_file = None

            nsmap = {
                None: 'http://www.fora.se/foraXML',   # noqa
                'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            }
            root = etree.Element(
                'FORAInrapportering',
                nsmap=nsmap,
                Version='2.1',
            )

            # Company info
            company_el = etree.SubElement(root, 'Foretag')
            orgnr = etree.SubElement(company_el, 'Organisationsnummer')
            orgnr.text = rec.company_id.company_registry or ''
            name_el = etree.SubElement(company_el, 'Foretagsnamn')
            name_el.text = rec.company_id.name or ''

            # Period
            period_el = etree.SubElement(root, 'Period')
            start = etree.SubElement(period_el, 'Start')
            start.text = fields.Date.from_string(rec.date_start).strftime('%Y%m%d')
            stop_el = etree.SubElement(period_el, 'Stop')
            stop_el.text = fields.Date.from_string(rec.date_stop).strftime('%Y%m%d')
            report_type = etree.SubElement(period_el, 'Rapporttyp')
            report_type.text = rec.fora_report_type

            # Employee data grouped by collective agreement
            agreements = {}
            for line in rec.line_ids:
                ag_id = line.collective_agreement_id.id
                if ag_id not in agreements:
                    agreements[ag_id] = {
                        'agreement': line.collective_agreement_id,
                        'lines': [],
                    }
                agreements[ag_id]['lines'].append(line)

            for ag_id, ag_data in agreements.items():
                ag = ag_data['agreement']

                ag_el = etree.SubElement(root, 'Avtal')
                ag_code = etree.SubElement(ag_el, 'Avtalskod')
                ag_code.text = ag.code
                ag_name = etree.SubElement(ag_el, 'Avtalsnamn')
                ag_name.text = ag.name

                for line in ag_data['lines']:
                    emp_el = etree.SubElement(ag_el, 'Anstalld')

                    # Employee identification
                    pnr_el = etree.SubElement(emp_el, 'Personnummer')
                    pnr_el.text = line.personal_number or ''
                    age_el = etree.SubElement(emp_el, 'Aldersgrupp')
                    age_el.text = line.age_group

                    # Wage basis
                    wage_el = etree.SubElement(emp_el, 'Loneunderlag')
                    wage_el.text = str(int(line.wage_basis or 0))

                    # Insurance premiums section
                    ins_el = etree.SubElement(emp_el, 'Forsakringspremier')
                    if line.tgl_premium:
                        tgl = etree.SubElement(ins_el, 'TGL')
                        tgl.text = str(int(line.tgl_premium))
                    if line.tfa_premium:
                        tfa = etree.SubElement(ins_el, 'TFA')
                        tfa.text = str(int(line.tfa_premium))
                    if line.ags_premium:
                        ags = etree.SubElement(ins_el, 'AGS')
                        ags.text = str(int(line.ags_premium))
                    if line.agb_premium:
                        agb = etree.SubElement(ins_el, 'AGB')
                        agb.text = str(int(line.agb_premium))

                    # Pension premium
                    if line.pension_premium:
                        pens_el = etree.SubElement(emp_el, 'Pensionspremie')
                        pensionskod = etree.SubElement(pens_el, 'Pensionskod')
                        pensionskod.text = line.pension_type or 'none'
                        belopp = etree.SubElement(pens_el, 'Belopp')
                        belopp.text = str(int(line.pension_premium))
                        grund_el = etree.SubElement(pens_el, 'Premieunderlag')
                        grund_el.text = str(int(line.wage_basis or 0))

                        # ITP wage brackets
                        if line.pension_type == 'itp1':
                            if line.pension_wage_basic:
                                basic_el = etree.SubElement(pens_el, 'UnderlagBasic')
                                basic_el.text = str(int(line.pension_wage_basic))
                            if line.pension_wage_high:
                                high_el = etree.SubElement(pens_el, 'UnderlagHog')
                                high_el.text = str(int(line.pension_wage_high))
                        elif line.pension_type == 'itp2':
                            if line.pension_wage_low:
                                low_el = etree.SubElement(pens_el, 'UnderlagLag')
                                low_el.text = str(int(line.pension_wage_low))
                            if line.pension_wage_mid:
                                mid_el = etree.SubElement(pens_el, 'UnderlagMellan')
                                mid_el.text = str(int(line.pension_wage_mid))
                            if line.pension_wage_high:
                                high_el = etree.SubElement(pens_el, 'UnderlagHog')
                                high_el.text = str(int(line.pension_wage_high))

            xml_bytes = etree.tostring(
                root, pretty_print=True, encoding='UTF-8',
                xml_declaration=True)
            rec.fora_file = base64.b64encode(xml_bytes)

    # ---- FORA API submission ----

    def action_send_to_fora(self):
        """Submit FORA declaration to FORA's API."""
        self.ensure_one()

        if not self.fora_file:
            self.generate_fora_file()
        if not self.fora_file:
            raise UserError(_(
                "No FORA file generated. Please run 'Calculate' first."))

        xml_bytes = base64.b64decode(self.fora_file)
        fora_api_url = self._get_fora_api_url()

        headers = {
            'Content-Type': 'application/xml; charset=UTF-8',
            'Accept': 'application/xml',
        }

        try:
            response = requests.post(
                fora_api_url, data=xml_bytes, headers=headers, timeout=60)
            _logger.info(
                "FORA API response: %s %s",
                response.status_code, response.text[:500])

            if response.status_code in (200, 201, 202):
                # Try to extract case number from response
                case_number = self._extract_fora_case(response.text)
                self.write({
                    'fora_submitted_date': fields.Datetime.now(),
                    'fora_case_number': case_number,
                    'skv_api_status': 'accepted',
                    'skv_response': 'FORA accepterade. Ärende: %s' % (case_number or 'N/A'),
                    'state': 'done',
                })
            elif response.status_code == 422:
                # Validation errors from FORA
                self.write({
                    'fora_submitted_date': fields.Datetime.now(),
                    'skv_api_status': 'error',
                    'skv_response': 'FORA valideringsfel:\n%s' % response.text[:1000],
                })
                raise UserError(_(
                    "FORA rejected the file with validation errors:\n%s")
                    % response.text[:500])
            else:
                self.write({
                    'fora_submitted_date': fields.Datetime.now(),
                    'skv_api_status': 'error',
                    'skv_response': 'HTTP %s: %s' % (
                        response.status_code, response.text[:1000]),
                })
                raise UserError(_(
                    "FORA API returned error %s:\n%s")
                    % (response.status_code, response.text[:500]))
        except requests.exceptions.RequestException as e:
            self.write({
                'fora_submitted_date': fields.Datetime.now(),
                'skv_api_status': 'error',
                'skv_response': 'Connection error: %s' % str(e),
            })
            raise UserError(_("Could not connect to FORA API:\n%s") % str(e))

    def _get_fora_api_url(self):
        """Get the FORA API endpoint URL.

        FORA's submission API endpoint. Override for test/production.
        """
        company = self.company_id or self.env.company
        if hasattr(company, 'fora_api_url') and company.fora_api_url:
            return company.fora_api_url
        # Default FORA API endpoint
        return 'https://api.fora.se/inrapportering/v2'

    def _extract_fora_case(self, response_text):
        """Extract FORA case number from API response XML."""
        try:
            root = etree.fromstring(response_text.encode('utf-8'))
            ns = {'f': 'http://www.fora.se/foraXML'}
            case_el = root.find('.//f:Arendenummer', ns)
            if case_el is not None and case_el.text:
                return case_el.text.strip()
            case_el = root.find('.//Arendenummer')
            if case_el is not None and case_el.text:
                return case_el.text.strip()
        except Exception:
            pass
        return None

    # ---- Actions ----

    def action_download_fora_file(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s/%s/fora_file/%s?download=true' % (
                self._name, self.id, self.fora_file_name),
            'target': 'self',
        }

    def action_open_calendar_event(self):
        self.ensure_one()
        if self.event_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'calendar.event',
                'res_id': self.event_id.id,
                'view_mode': 'form',
                'target': 'current',
            }

    def action_view_payslips(self):
        self.ensure_one()
        if not self.payslip_run_id:
            return
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip',
            'view_mode': 'list,form',
            'domain': [('payslip_run_id', '=', self.payslip_run_id.id)],
            'context': {'create': False},
        }

    def action_view_agreement(self):
        """Show the collective agreement used in this declaration."""
        self.ensure_one()
        agreement_ids = self.line_ids.mapped('collective_agreement_id').ids
        if not agreement_ids:
            return
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.collective.agreement',
            'view_mode': 'form',
            'res_id': agreement_ids[0],
            'target': 'current',
        }

    # ---- Deadlines ----

    @api.model
    def _calculate_fora_deadline(self, date_stop):
        """Calculate FORA submission deadline.

        FORA deadlines: last day of month following the reporting period.
        January and August have extended deadlines.
        """
        cal = self._get_swedish_calendar()
        if isinstance(date_stop, str):
            date_stop = fields.Date.from_string(date_stop)

        # Next month, last day
        deadline = date_stop + relativedelta(months=1)
        deadline = deadline.replace(
            day=1) + relativedelta(months=1, days=-1)

        # Move to working day if weekend/holiday
        while not cal.is_working_day(deadline):
            deadline -= timedelta(days=1)

        return deadline

    def _get_swedish_calendar(self):
        """Get Swedish working calendar."""
        try:
            from workalendar.europe import Sweden
            return Sweden()
        except ImportError:
            # Fallback: simple weekday check
            class SimpleCalendar:
                @staticmethod
                def is_working_day(d):
                    return d.weekday() < 5
            return SimpleCalendar()

    # ---- Cron ----

    @api.model
    def _cron_create_fora(self):
        """Cron: create FORA declaration for the latest completed payslip run."""
        existing_fora_runs = self.search([]).mapped('payslip_run_id')
        latest_run = self.env['hr.payslip.run'].search([
            ('state', '=', 'done'),
            ('id', 'not in', existing_fora_runs.ids if existing_fora_runs else [0]),
        ], order='date_end desc', limit=1)

        if not latest_run or not latest_run.date_end:
            return False

        deadline = self._calculate_fora_deadline(
            fields.Date.from_string(latest_run.date_end))

        fora = self.create({
            'payslip_run_id': latest_run.id,
            'date_start': latest_run.date_start,
            'date_stop': latest_run.date_end,
            'date': fields.Date.to_string(deadline),
            'target_move': 'posted',
        })

        if fora:
            try:
                # Check if there are employees with collective agreements
                has_agreements = False
                for slip in latest_run.slip_ids:
                    if (slip.state in ('done', 'paid') and
                            slip.employee_id.contract_id.collective_agreement_id):
                        has_agreements = True
                        break

                if has_agreements:
                    fora.calculate()
                    _logger.info(
                        'Cron: FORA created for payslip run %s', latest_run.name)
                else:
                    _logger.info(
                        'Cron: No collective agreements found, skipping FORA for run %s',
                        latest_run.name)
                    # Keep the draft but don't calculate
            except Exception as e:
                _logger.warning('Cron: FORA calculation failed: %s', e)

        return True


class AccountForaDeclarationLine(models.Model):
    _name = 'account.fora.declaration.line'
    _description = 'FORA Declaration Line (per employee)'
    _order = 'collective_agreement_id, employee_id'

    fora_id = fields.Many2one(
        'account.fora.declaration', string='FORA-deklaration',
        required=True, ondelete='cascade')
    employee_id = fields.Many2one(
        'hr.employee', string='Anställd', required=True)
    personal_number = fields.Char(
        string='Personnummer',
        help="Swedish personal identity number (personnummer).")
    collective_agreement_id = fields.Many2one(
        'hr.collective.agreement', string='Kollektivavtal',
        required=True)
    pension_type = fields.Selection([
        ('itp1', 'ITP 1'),
        ('itp2', 'ITP 2'),
        ('saflo', 'SAF-LO'),
        ('akap', 'AKAP-KL'),
        ('none', 'Ingen'),
    ], string='Pensionstyp')
    age_group = fields.Selection([
        ('under_26', 'Under 26 år'),
        ('working_age', '26-64 år'),
        ('senior', '65-79 år'),
        ('pensioner', '80+ år'),
    ], string='Åldersgrupp')

    # Wage basis
    wage_basis = fields.Monetary('Löneunderlag', currency_field='currency_id')

    # Insurance premiums
    tgl_premium = fields.Monetary('TGL-premie', currency_field='currency_id')
    tfa_premium = fields.Monetary('TFA-premie', currency_field='currency_id')
    ags_premium = fields.Monetary('AGS-premie', currency_field='currency_id')
    agb_premium = fields.Monetary('AGB-premie', currency_field='currency_id')

    # Pension premium
    pension_premium = fields.Monetary(
        'Pensionspremie', currency_field='currency_id')
    # ITP wage brackets (for detailed reporting)
    pension_wage_basic = fields.Monetary(
        'Underlag ITP1 basic', currency_field='currency_id')
    pension_wage_high = fields.Monetary(
        'Underlag ITP1 hög', currency_field='currency_id')
    pension_wage_low = fields.Monetary(
        'Underlag ITP2 låg', currency_field='currency_id')
    pension_wage_mid = fields.Monetary(
        'Underlag ITP2 mellan', currency_field='currency_id')

    # Total
    total_premium = fields.Monetary(
        'Total premie', compute='_compute_total', store=True,
        currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency', related='fora_id.currency_id')

    @api.depends(
        'tgl_premium', 'tfa_premium', 'ags_premium',
        'agb_premium', 'pension_premium')
    def _compute_total(self):
        for line in self:
            line.total_premium = (
                (line.tgl_premium or 0.0) +
                (line.tfa_premium or 0.0) +
                (line.ags_premium or 0.0) +
                (line.agb_premium or 0.0) +
                (line.pension_premium or 0.0)
            )


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    fora_declaration_id = fields.Many2one(
        'account.fora.declaration', string='FORA',
        help="The FORA declaration this payslip was included in.",
        readonly=True)


class HrCollectiveAgreement(models.Model):
    _inherit = 'hr.collective.agreement'

    # Override FORA rates per agreement (if different from defaults)
    fora_tgl_rate = fields.Float(
        string='FORA TGL Rate (%)',
        help="Override TGL premium rate for this agreement (%). Leave 0 for default.")
    fora_tfa_rate = fields.Float(
        string='FORA TFA Rate (%)')
    fora_ags_rate = fields.Float(
        string='FORA AGS Rate (%)')
    fora_agb_rate = fields.Float(
        string='FORA AGB Rate (%)')
    fora_pension_rate = fields.Float(
        string='FORA Pension Rate (%)')
