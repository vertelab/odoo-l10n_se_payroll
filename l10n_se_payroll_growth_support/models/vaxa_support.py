# -*- coding: utf-8 -*-
"""Swedish Growth Support (Växa-stöd).

From January 2026, employers pay full employer contributions (31.42%)
and apply separately for reimbursement for their first and second employees.

Reimbursement rate: 31.42% - 10.21% = 21.21%
Salary cap: 25 000 SEK (hired before May 1, 2024) or 35 000 SEK (after).
Maximum 24 consecutive months per employee.
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import requests
from lxml import etree
import logging
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)

# Key constants
VACA_REIMBURSEMENT_RATE = 0.2121  # 31.42% - 10.21%
SALARY_CAP_PRE_MAY2024 = 25000.0
SALARY_CAP_POST_APR2024 = 35000.0
CUTOFF_DATE = date(2024, 5, 1)  # May 1, 2024
MAX_MONTHS = 24
DE_MINIMIS_LIMIT_EUR = 300000.0


class AccountVaxaSupport(models.Model):
    _name = 'account.vaxa.support'
    _inherit = 'account.declaration'
    _description = 'Växa-stöd Application'
    _report_name = 'Växa-stöd'
    _order = 'date desc'

    payslip_run_id = fields.Many2one(
        'hr.payslip.run', string='Lönekörning',
        help="The salary batch this växa-stöd application is based on.")

    agd_declaration_id = fields.Many2one(
        'account.agd.declaration', string='AGD-deklaration',
        help="The employer declaration this application relates to.")

    line_ids = fields.One2many(
        'account.vaxa.support.line', 'vaxa_id',
        string='Anställda')

    # Summary fields (computed from line_ids)
    employee_count = fields.Integer(
        string='Antal anställda', compute='_compute_totals', store=True)
    total_salary = fields.Monetary(
        string='Total bruttolön', compute='_compute_totals', store=True,
        currency_field='currency_id')
    total_reimbursement = fields.Monetary(
        string='Total återbetalning', compute='_compute_totals', store=True,
        currency_field='currency_id')
    total_de_minimis_eur = fields.Monetary(
        string='Totalt de minimis (EUR)', compute='_compute_totals', store=True,
        currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id')

    # Application deadline (1 year after period end)
    application_deadline = fields.Date(
        string='Sista ansökningsdag',
        compute='_compute_application_deadline', store=True,
        help="Application must be submitted within 1 year of the calendar month.")

    vaxa_file = fields.Binary(string='Växa-stöd-fil', readonly=True)
    vaxa_file_name = fields.Char(
        string='Filnamn', default='vaxa_stod_application.xml')

    @api.depends('line_ids.monthly_salary', 'line_ids.reimbursement_amount',
                  'line_ids.de_minimis_used')
    def _compute_totals(self):
        for rec in self:
            rec.employee_count = len(rec.line_ids)
            rec.total_salary = sum(l.monthly_salary or 0.0 for l in rec.line_ids)
            rec.total_reimbursement = sum(
                l.reimbursement_amount or 0.0 for l in rec.line_ids)
            rec.total_de_minimis_eur = sum(
                l.de_minimis_used or 0.0 for l in rec.line_ids)

    @api.depends('date_stop')
    def _compute_application_deadline(self):
        for rec in self:
            if rec.date_stop:
                stop = fields.Date.from_string(rec.date_stop) \
                    if isinstance(rec.date_stop, str) else rec.date_stop
                # Deadline: 1 year after end of the calendar month
                rec.application_deadline = (
                    stop.replace(day=1) + relativedelta(months=13, days=-1))

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
                self.date = self._calculate_vat_deadline(run.date_end, 1)

    # ---- Main calculation ----

    def calculate(self):
        """Calculate växa-stöd reimbursement per employee."""
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
                # Auto-find by date range
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
                        'total_salary': 0.0,
                    }
                employee_data[emp.id]['slips'] |= slip

            # Build växa-stöd lines
            vaxa_lines = []
            for emp_id, data in employee_data.items():
                emp = data['employee']

                # Get contract valid during slip period
                contract = self._get_active_contract(emp, rec.date_stop)
                if not contract:
                    _logger.warning(
                        'No active contract found for employee %s on %s',
                        emp.name, rec.date_stop)
                    continue

                hire_date = contract.date_start
                salary_cap = _get_salary_cap(self, hire_date)

                # Sum gross salary from payslip lines
                monthly_salary = 0.0
                for slip in data['slips']:
                    monthly_salary += slip.get_salary_line_total('GROSS')
                    monthly_salary += slip.get_salary_line_total('gl')
                    monthly_salary += slip.get_salary_line_total('bl')
                    # Also try other common gross salary codes
                    if not monthly_salary:
                        for line in slip.line_ids:
                            if line.salary_rule_id.code in (
                                    'GROSS', 'gl', 'bl', 'BRUTTO', 'grundlon'):
                                monthly_salary += abs(line.total)
                            # Fallback: look for salary rule category GROSS
                            if line.category_id and \
                                    line.category_id.code == 'GROSS':
                                monthly_salary += abs(line.total)

                basis = min(monthly_salary, salary_cap)
                reimbursement = round(basis * VACA_REIMBURSEMENT_RATE)

                # Determine employee number (first or second) and months used
                employee_number = self._determine_employee_number(emp)
                months_used = self._count_months_used(emp, rec.date_stop)
                months_remaining = max(0, MAX_MONTHS - months_used)

                # If no months remaining, skip but still show the employee
                if months_remaining <= 0:
                    reimbursement = 0.0
                    basis = 0.0

                de_minimis_sek = self._get_de_minimis_sek(emp, rec)

                vals = {
                    'vaxa_id': rec.id,
                    'employee_id': emp.id,
                    'personal_number': emp.identification_id or '',
                    'contract_id': contract.id,
                    'hire_date': hire_date,
                    'monthly_salary': monthly_salary,
                    'salary_cap': salary_cap,
                    'basis_for_support': basis,
                    'reimbursement_amount': reimbursement,
                    'months_used': months_used + 1,
                    'months_remaining': months_remaining - 1,
                    'employee_number': employee_number,
                    'de_minimis_used': de_minimis_sek,
                }

                has_amount = monthly_salary > 0
                if has_amount:
                    vaxa_lines.append((0, 0, vals))

            if not vaxa_lines:
                raise UserError(_(
                    "Inga lönebelopp att ansöka om för perioden."))

            rec.write({'line_ids': vaxa_lines, 'state': 'confirmed'})
            rec.generate_vaxa_file()

    def _get_active_contract(self, employee, date_stop):
        """Find the active contract for an employee at the given date."""
        if isinstance(date_stop, str):
            date_stop = fields.Date.from_string(date_stop)
        contract = self.env['hr.contract'].search([
            ('employee_id', '=', employee.id),
            ('date_start', '<=', date_stop),
            '|',
            ('date_end', '=', False),
            ('date_end', '>=', date_stop),
        ], order='date_start desc', limit=1)
        return contract

    def _determine_employee_number(self, employee):
        """Determine if this is the first or second employee for växa-stöd.

        Based on hire date. Look at all employees of the company
        and identify the chronological order.
        """
        # First, check if this employee is already tracked in any vaxa line
        prev_lines = self.env['account.vaxa.support.line'].search([
            ('employee_id', '=', employee.id),
        ], order='hire_date asc', limit=1)
        if prev_lines:
            return prev_lines.employee_number

        # Otherwise determine from hire date of all employees
        contracts = self.env['hr.contract'].search([
            ('employee_id', '!=', False),
            ('company_id', '=', self.company_id.id),
            ('date_start', '!=', False),
        ], order='date_start asc')

        seen_employees = set()
        for contract in contracts:
            if contract.employee_id.id not in seen_employees:
                seen_employees.add(contract.employee_id.id)
                if contract.employee_id.id == employee.id:
                    return 'first' if len(seen_employees) == 1 else 'second'
        return 'first'

    def _count_months_used(self, employee, date_stop):
        """Count how many months of växa-stöd have been used for this employee."""
        if isinstance(date_stop, str):
            date_stop = fields.Date.from_string(date_stop)

        prev_lines = self.env['account.vaxa.support.line'].search([
            ('employee_id', '=', employee.id),
            ('vaxa_id.date_stop', '<', date_stop),
            ('vaxa_id.state', 'in', ('confirmed', 'done')),
        ])
        # Each line represents one month
        return len(prev_lines)

    def _get_de_minimis_sek(self, employee, rec):
        """Calculate de minimis aid used for this employee in SEK.

        Växa-stöd is a de minimis aid under EU rules (max €300,000 in 3 years).
        Convert to SEK at approximate rate.
        """
        # Find all previous reimbursements for this company
        prev_lines = self.env['account.vaxa.support.line'].search([
            ('vaxa_id.state', 'in', ('confirmed', 'done')),
            ('vaxa_id.company_id', '=', rec.company_id.id),
        ])
        total_sek = sum(l.reimbursement_amount or 0.0 for l in prev_lines)
        # Also include current pending calculation
        # (approximate; the actual line amount will be set by the caller)
        return total_sek

    def _get_salary_cap(self, hire_date):
        """Get the salary cap for this employee based on hire date."""
        if isinstance(hire_date, str):
            hire_date = fields.Date.from_string(hire_date)
        if hire_date < CUTOFF_DATE:
            return SALARY_CAP_PRE_MAY2024
        return SALARY_CAP_POST_APR2024

    # ---- XML generation for download ----

    def generate_vaxa_file(self):
        """Generate XML summary for växa-stöd application."""
        for rec in self:
            rec.vaxa_file = None
            root = etree.Element('VaxaStodAnsokan')

            # Company info
            company_el = etree.SubElement(root, 'Foretag')
            orgnr = etree.SubElement(company_el, 'OrgNr')
            orgnr.text = rec.company_id.company_registry or ''
            name_el = etree.SubElement(company_el, 'Namn')
            name_el.text = rec.company_id.name or ''

            # Period
            period_el = etree.SubElement(root, 'Period')
            period_el.text = fields.Date.from_string(
                rec.date_start).strftime('%Y%m') if rec.date_start else ''

            # Employee lines
            for line in rec.line_ids:
                emp_el = etree.SubElement(root, 'Anstalld')
                pnr = etree.SubElement(emp_el, 'PersonNr')
                pnr.text = line.personal_number or ''
                anst_nr = etree.SubElement(emp_el, 'AnstalldNr')
                anst_nr.text = line.employee_number or '1'
                anst_datum = etree.SubElement(emp_el, 'Anstallningsdatum')
                anst_datum.text = str(line.hire_date) if line.hire_date else ''
                lon = etree.SubElement(emp_el, 'Manadslon')
                lon.text = str(int(round(line.monthly_salary or 0)))
                underlag = etree.SubElement(emp_el, 'Underlag')
                underlag.text = str(int(round(line.basis_for_support or 0)))
                aterbet = etree.SubElement(emp_el, 'Aterbetalning')
                aterbet.text = str(int(round(line.reimbursement_amount or 0)))

            # De minimis info
            demin_el = etree.SubElement(root, 'DeMinimis')
            total_sek = etree.SubElement(demin_el, 'TotalSEK')
            total_sek.text = str(int(rec.total_de_minimis_eur or 0))

            xml_bytes = etree.tostring(
                root, pretty_print=True, encoding='UTF-8')
            rec.vaxa_file = base64.b64encode(xml_bytes)

    # ---- SKV API submission ----

    def action_send_to_skv(self):
        """Submit växa-stöd application to Skatteverket.

        Note: As of 2026, Skatteverket may not yet have a machine-to-machine
        API for växa-stöd. This method generates a downloadable file as fallback
        and attempts API submission if an endpoint is configured.
        """
        self.ensure_one()

        if not self.vaxa_file:
            self.generate_vaxa_file()
        if not self.vaxa_file:
            raise UserError(_(
                "Could not generate växa-stöd file. "
                "Please run 'Calculate' first."))

        partner = self._get_skv_partner()
        if not partner or not partner.enable_skatteverket_api:
            raise UserError(_(
                "No Skatteverket API partner configured. "
                "Enable 'Skatteverket API' on a partner record in Contacts. "
                "You can download the växa-stöd file for manual submission."))

        vaxa_api_url = (self.company_id.skv_vaxa_api_url
                        or self._get_skv_settings()['api_url'])

        try:
            access_token = self._get_skv_access_token(partner)
        except UserError:
            # Token failed — provide downloadable fallback
            self.write({
                'skv_api_status': 'error',
                'skv_response': (
                    'API authentication failed. The växa-stöd file is '
                    'available for download and manual submission via '
                    'Skatteverket e-service.'),
                'skv_submitted_date': fields.Datetime.now(),
            })
            raise UserError(_(
                "Kunde inte autentisera mot Skatteverket API.\n"
                "Ladda ner filen för manuell inlämning via e-tjänsten."))

        xml_bytes = base64.b64decode(self.vaxa_file)
        headers = {
            'Authorization': 'Bearer %s' % access_token,
            'Content-Type': 'application/xml; charset=UTF-8',
            'Accept': 'application/json',
        }

        try:
            response = requests.post(
                vaxa_api_url, data=xml_bytes, headers=headers, timeout=30)
            _logger.info("SKV Växa-stöd API response: %s %s",
                         response.status_code, response.text[:500])

            if response.status_code in (200, 201, 202):
                self.write({
                    'skv_api_status': 'accepted',
                    'skv_response': 'OK: %s' % response.text[:500],
                    'skv_submitted_date': fields.Datetime.now(),
                    'state': 'done',
                })
            elif response.status_code == 401:
                partner.write({'access_token': False})
                self.write({
                    'skv_api_status': 'error',
                    'skv_response': 'Authentication failed.',
                })
                raise UserError(_(
                    "Authentication failed. Please retry."))
            elif response.status_code == 404:
                # API endpoint doesn't exist — fallback to download
                self.write({
                    'skv_api_status': 'submitted',
                    'skv_response': (
                        'API endpoint for växa-stöd not yet available. '
                        'Use the downloadable file for manual submission '
                        'via Skatteverket e-service.'),
                    'skv_submitted_date': fields.Datetime.now(),
                    'state': 'confirmed',
                })
                _logger.info(
                    'Växa-stöd API not available (404), falling back to '
                    'downloadable file.')
            else:
                self.write({
                    'skv_api_status': 'error',
                    'skv_response': 'HTTP %s: %s' % (
                        response.status_code, response.text[:1000]),
                    'skv_submitted_date': fields.Datetime.now(),
                })
                raise UserError(_(
                    "Skatteverket API returned error %s:\n%s")
                    % (response.status_code, response.text[:500]))
        except requests.exceptions.RequestException as e:
            self.write({
                'skv_api_status': 'error',
                'skv_response': 'Connection error: %s' % str(e),
                'skv_submitted_date': fields.Datetime.now(),
            })
            raise UserError(_(
                "Could not connect to Skatteverket API:\n%s") % str(e))

    # ---- Actions ----

    def action_download_vaxa_file(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s/%s/vaxa_file/%s?download=true' % (
                self._name, self.id, self.vaxa_file_name),
            'target': 'self',
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

    # ---- Cron ----

    @api.model
    def _cron_create_vaxa(self):
        """Cron: create växa-stöd application for the latest AGD."""
        # Find latest completed AGD without a växa-stöd application
        existing_vaxa_agds = self.search([]).mapped('agd_declaration_id')
        latest_agd = self.env['account.agd.declaration'].search([
            ('state', '=', 'done'),
            ('id', 'not in', existing_vaxa_agds.ids
             if existing_vaxa_agds else [0]),
        ], order='date_stop desc', limit=1)

        if not latest_agd:
            # Try from payslip runs directly
            existing_vaxa_runs = self.search([]).mapped('payslip_run_id')
            latest_run = self.env['hr.payslip.run'].search([
                ('state', '=', 'done'),
                ('id', 'not in', existing_vaxa_runs.ids
                 if existing_vaxa_runs else [0]),
            ], order='date_end desc', limit=1)
            if not latest_run or not latest_run.date_end:
                return False
            deadline = self._calculate_vat_deadline(
                fields.Date.from_string(latest_run.date_end), 1)
            vaxa = self.create({
                'payslip_run_id': latest_run.id,
                'date_start': latest_run.date_start,
                'date_stop': latest_run.date_end,
                'date': fields.Date.to_string(deadline),
                'target_move': 'posted',
            })
        else:
            deadline = self._calculate_vat_deadline(
                fields.Date.from_string(latest_agd.date_stop), 1)
            vaxa = self.create({
                'agd_declaration_id': latest_agd.id,
                'payslip_run_id': latest_agd.payslip_run_id.id,
                'date_start': latest_agd.date_start,
                'date_stop': latest_agd.date_stop,
                'date': fields.Date.to_string(deadline),
                'target_move': 'posted',
            })

        if vaxa:
            try:
                vaxa.calculate()
                _logger.info(
                    'Cron: Växa-stöd created for period %s - %s',
                    vaxa.date_start, vaxa.date_stop)
            except Exception as e:
                _logger.warning('Cron: Växa-stöd calculation failed: %s', e)

        return True


class AccountVaxaSupportLine(models.Model):
    _name = 'account.vaxa.support.line'
    _description = 'Växa-stöd Line (per employee)'
    _order = 'employee_id'

    vaxa_id = fields.Many2one(
        'account.vaxa.support', string='Växa-stöd-ansökan',
        required=True, ondelete='cascade')
    employee_id = fields.Many2one(
        'hr.employee', string='Anställd', required=True)
    personal_number = fields.Char(
        string='Personnummer',
        help="Swedish personal identity number (personnummer).")
    contract_id = fields.Many2one(
        'hr.contract', string='Anställningsavtal',
        help="The active contract during this period.")
    hire_date = fields.Date(
        string='Anställningsdatum',
        help="Date when the employment started.")
    employee_number = fields.Selection(
        selection=[('first', 'Första anställd'), ('second', 'Andra anställd')],
        string='Anställningsnummer',
        help="Whether this is the first or second employee for växa-stöd.")

    # Salary data
    monthly_salary = fields.Monetary(
        'Månadslön', currency_field='currency_id',
        help="Gross monthly salary for this period.")
    salary_cap = fields.Monetary(
        'Lönetak', currency_field='currency_id',
        compute='_compute_salary_cap', store=True,
        help="Maximum salary basis for växa-stöd reimbursement "
             "(25 000 or 35 000 SEK based on hire date).")
    basis_for_support = fields.Monetary(
        'Underlag växa-stöd', currency_field='currency_id',
        help="The salary amount eligible for växa-stöd (min of salary and cap).")
    reimbursement_amount = fields.Monetary(
        'Återbetalning', currency_field='currency_id',
        help="The reimbursement amount (underlag × 21.21%).")

    # Month tracking
    months_used = fields.Integer(
        'Förbrukade månader',
        help="Number of months of växa-stöd already used for this employee.")
    months_remaining = fields.Integer(
        'Återstående månader',
        compute='_compute_months_remaining', store=True,
        help="Remaining months of the 24-month period.")

    # De minimis
    de_minimis_used = fields.Monetary(
        'De minimis (SEK)', currency_field='currency_id',
        help="Total de minimis aid used by this company (includes this application).")

    currency_id = fields.Many2one(
        'res.currency', related='vaxa_id.currency_id')

    @api.depends('hire_date')
    def _compute_salary_cap(self):
        for line in self:
            if line.hire_date:
                hire_date = line.hire_date if isinstance(
                    line.hire_date, date) else fields.Date.from_string(
                        line.hire_date)
                if hire_date < CUTOFF_DATE:
                    line.salary_cap = SALARY_CAP_PRE_MAY2024
                else:
                    line.salary_cap = SALARY_CAP_POST_APR2024
            else:
                line.salary_cap = SALARY_CAP_POST_APR2024

    @api.depends('months_used')
    def _compute_months_remaining(self):
        for line in self:
            line.months_remaining = max(0, MAX_MONTHS - (line.months_used or 0))


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    vaxa_support_id = fields.Many2one(
        'account.vaxa.support', string='Växa-stöd',
        help="The växa-stöd application this payslip was included in.",
        readonly=True)


class AccountAgdDeclaration(models.Model):
    _inherit = 'account.agd.declaration'

    vaxa_support_id = fields.Many2one(
        'account.vaxa.support', string='Växa-stöd',
        help="The växa-stöd application linked to this AGD.",
        readonly=True)


class VaxaDemoGenerator(models.AbstractModel):
    _name = 'l10n_se_payroll_growth_support.vaxa_demo_generator'
    _description = 'Växa-stöd Demo Data Generator'

    @api.model
    def generate_demo_data(self):
        """Generate demo data: employee + contract + payslip + växa-stöd."""
        if self.env['account.vaxa.support'].search_count([]) > 0:
            _logger.info('Växa-stöd demo data already exists, skipping.')
            return True

        # Find or create employee
        employee = self.env['hr.employee'].search(
            [('identification_id', '=', '19850101-5678')], limit=1)
        if not employee:
            user = self.env.ref('base.user_demo', raise_if_not_found=False)
            if not user:
                _logger.warning(
                    'No demo user found, cannot create växa-stöd demo.')
                return False
            work_address = self.env['res.partner'].search(
                [('name', '=', 'Demo Employee Växa')], limit=1)
            if not work_address:
                work_address = self.env['res.partner'].create({
                    'name': 'Demo Employee Växa',
                    'is_company': False,
                })
            employee = self.env['hr.employee'].create({
                'name': 'Demo Employee Växa',
                'identification_id': '19850101-5678',
                'birthday': '1985-01-01',
                'work_contact_id': work_address.id,
                'user_id': user.id,
            })

        # Find or create salary structure
        structure = self.env['hr.payroll.structure'].search(
            [('code', '=', 'SE-BASIC')], limit=1)
        if not structure:
            structure = self.env['hr.payroll.structure'].search([], limit=1)
        if not structure:
            _logger.warning('No salary structure for växa-stöd demo.')
            return False

        # Find or create contract (hired after April 2024 for 35k cap)
        contract = self.env['hr.contract'].search(
            [('employee_id', '=', employee.id)], limit=1)
        if not contract:
            contract = self.env['hr.contract'].create({
                'name': 'Demo Contract Växa',
                'employee_id': employee.id,
                'wage': 35000.0,
                'struct_id': structure.id,
                'date_start': fields.Date.today().replace(
                    year=2024, month=6, day=1),
                'state': 'open',
            })

        # Create payslip run for current month
        today = fields.Date.today()
        month_start = today.replace(day=1)
        month_end = (month_start + relativedelta(months=1) - timedelta(days=1))

        payslip_run = self.env['hr.payslip.run'].create({
            'name': 'Demo Lönekörning %s' % month_start.strftime('%B %Y'),
            'date_start': month_start,
            'date_end': month_end,
        })

        # Create payslip
        payslip = self.env['hr.payslip'].create({
            'employee_id': employee.id,
            'contract_id': contract.id,
            'struct_id': structure.id,
            'date_from': month_start,
            'date_to': month_end,
            'payslip_run_id': payslip_run.id,
        })

        if hasattr(payslip, 'compute_sheet'):
            payslip.compute_sheet()
        if payslip.state == 'draft':
            payslip.action_payslip_done()

        # Set payslip run to done
        if payslip_run.state == 'draft':
            payslip_run.state = 'done'

        # Create växa-stöd application
        deadline = self.env['account.declaration']._calculate_vat_deadline(
            month_end, 1)

        vaxa = self.env['account.vaxa.support'].create({
            'payslip_run_id': payslip_run.id,
            'date_start': month_start,
            'date_stop': month_end,
            'date': fields.Date.to_string(deadline),
            'target_move': 'posted',
        })

        if vaxa:
            try:
                vaxa.calculate()
                _logger.info(
                    'Demo Växa-stöd created: %s with %d employees, '
                    'total reimbursement %.2f SEK',
                    vaxa.name, vaxa.employee_count,
                    vaxa.total_reimbursement)
            except Exception as e:
                _logger.warning('Demo Växa-stöd calculation: %s', e)

        return True
