# -*- coding: utf-8 -*-
"""Swedish Employer Declaration (Arbetsgivardeklaration).

Aggregates payroll data per employee per month and generates
eSKD XML for submission to Skatteverket.
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

# Age-based employer contribution rates (2026)
# These follow Skatteverket's current rules.
EMPLOYER_CONTRIBUTION_RATES = {
    'full': 0.3142,       # <65 years: full arbetsgivaravgift
    'senior': 0.1636,     # 66-79 years: reduced
    'pensioner': 0.0615,  # >=80 years: only särskild löneskatt
}


class AccountAgdDeclaration(models.Model):
    _name = 'account.agd.declaration'
    _inherit = 'account.declaration'
    _description = 'Arbetsgivardeklaration'
    _report_name = 'AGD'
    _order = 'date desc'

    payslip_run_id = fields.Many2one(
        'hr.payslip.run', string='Lönekörning',
        help="The salary batch this AGD is based on.")

    line_ids = fields.One2many(
        'account.agd.declaration.line', 'agd_id',
        string='Anställda')

    agd_file = fields.Binary(string='AGD-fil', readonly=True)
    agd_file_name = fields.Char(
        string='Filnamn', default='arbetsgivardeklaration.xml')

    # Summary fields (computed from line_ids)
    employee_count = fields.Integer(
        string='Antal anställda', compute='_compute_totals', store=True)
    total_salary = fields.Monetary(
        string='Total bruttolön', compute='_compute_totals', store=True,
        currency_field='currency_id')
    total_employer_fee = fields.Monetary(
        string='Total arbetsgivaravgift', compute='_compute_totals', store=True,
        currency_field='currency_id')
    total_tax_withheld = fields.Monetary(
        string='Total avdragen skatt', compute='_compute_totals', store=True,
        currency_field='currency_id')
    total_to_pay = fields.Monetary(
        string='Att betala', compute='_compute_totals', store=True,
        currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id')

    @api.depends('line_ids.r50_bruttolon', 'line_ids.r56_full_avg',
                  'line_ids.r58_vaxa_avg', 'line_ids.r60_aldersp_avg',
                  'line_ids.r62_sl_aldre_avg', 'line_ids.r82_avdragen_skatt')
    def _compute_totals(self):
        for rec in self:
            rec.employee_count = len(rec.line_ids)
            rec.total_salary = sum(l.r50_bruttolon or 0.0 for l in rec.line_ids)
            rec.total_employer_fee = sum(
                (l.r56_full_avg or 0.0) + (l.r58_vaxa_avg or 0.0) +
                (l.r60_aldersp_avg or 0.0) + (l.r62_sl_aldre_avg or 0.0)
                for l in rec.line_ids)
            rec.total_tax_withheld = sum(
                l.r82_avdragen_skatt or 0.0 for l in rec.line_ids)
            rec.total_to_pay = rec.total_employer_fee + rec.total_tax_withheld

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
        """Aggregate payslip lines per employee into AGD rows."""
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
            employee_lines = {}
            for slip in slips:
                emp = slip.employee_id
                if emp.id not in employee_lines:
                    employee_lines[emp.id] = {
                        'employee': emp,
                        'slip_lines': self.env['hr.payslip.line'],
                    }
                employee_lines[emp.id]['slip_lines'] |= slip.line_ids

            # Build AGD lines
            salary_rule_codes = self._get_salary_rule_code_map()
            agd_lines = []

            for emp_id, data in employee_lines.items():
                emp = data['employee']
                age = self._get_employee_age(emp, rec.date_stop)

                vals = {
                    'agd_id': rec.id,
                    'employee_id': emp.id,
                    'personal_number': emp.identification_id or '',
                    'r50_bruttolon': 0.0,
                    'r51_formaner': 0.0,
                    'r52_avdrag': 0.0,
                    'r55_full_avg_underlag': 0.0,
                    'r56_full_avg': 0.0,
                    'r57_vaxa_underlag': 0.0,
                    'r58_vaxa_avg': 0.0,
                    'r59_aldersp_underlag': 0.0,
                    'r60_aldersp_avg': 0.0,
                    'r61_sl_aldre_underlag': 0.0,
                    'r62_sl_aldre_avg': 0.0,
                    'r81_skatteavdrag_underlag': 0.0,
                    'r82_avdragen_skatt': 0.0,
                }

                for line in data['slip_lines']:
                    code = line.salary_rule_id.code
                    amount = abs(line.total)
                    if not amount:
                        continue

                    # Basic salary → r50, r55/r59/r61, r81
                    if code in salary_rule_codes['salary']:
                        vals['r50_bruttolon'] += amount
                        vals['r81_skatteavdrag_underlag'] += amount
                        # Distribute to age-based underlag
                        if age < 65:
                            vals['r55_full_avg_underlag'] += amount
                        elif age < 80:
                            vals['r59_aldersp_underlag'] += amount
                        else:
                            vals['r61_sl_aldre_underlag'] += amount

                    # Benefits → r51
                    if code in salary_rule_codes['benefit']:
                        vals['r51_formaner'] += amount

                    # Deductions → r52
                    if code in salary_rule_codes['deduction']:
                        vals['r52_avdrag'] += amount

                    # Tax withheld → r82
                    if code in salary_rule_codes['tax']:
                        vals['r82_avdragen_skatt'] += amount

                # Apply contribution rates
                vals['r56_full_avg'] = round(
                    vals['r55_full_avg_underlag'] * EMPLOYER_CONTRIBUTION_RATES['full'])
                vals['r58_vaxa_avg'] = round(
                    vals['r57_vaxa_underlag'] * EMPLOYER_CONTRIBUTION_RATES['full'] * 0.325)
                vals['r60_aldersp_avg'] = round(
                    vals['r59_aldersp_underlag'] * EMPLOYER_CONTRIBUTION_RATES['senior'])
                vals['r62_sl_aldre_avg'] = round(
                    vals['r61_sl_aldre_underlag'] * EMPLOYER_CONTRIBUTION_RATES['pensioner'])

                # Skip rows with zero amounts
                has_amount = any(
                    vals[k] for k in vals if k.startswith('r') and k not in ('agd_id',))
                if has_amount:
                    agd_lines.append((0, 0, vals))

            if not agd_lines:
                raise UserError(_("Inga lönebelopp att redovisa för perioden."))

            rec.write({'line_ids': agd_lines, 'state': 'confirmed'})
            rec.generate_agd_file()

    def _get_salary_rule_code_map(self):
        """Map salary rule codes to AGD categories.

        Override this method to customize which salary rule codes
        map to each AGD category.
        """
        return {
            # Codes that map to gross salary (r50, r55/59/61, r81)
            'salary': {'gl', 'bl', 'GROSS'},
            # Codes that map to taxable benefits (r51)
            'benefit': {'BENEFIT', 'FORMAN'},
            # Codes that map to deductions (r52)
            'deduction': {'DEDUCTION', 'AVDRAG'},
            # Codes that map to withheld tax (r82)
            'tax': {'total_skatt', 'TAX', 'SKATT'},
        }

    def _get_employee_age(self, employee, date_stop):
        """Calculate age at end of AGD period."""
        if not employee.birthday:
            return 40  # Default to full contribution if no birthdate
        stop = fields.Date.from_string(date_stop) if isinstance(date_stop, str) else date_stop
        age = stop.year - employee.birthday.year
        if (stop.month, stop.day) < (employee.birthday.month, employee.birthday.day):
            age -= 1
        return age

    # ---- eSKD XML generation ----

    def generate_agd_file(self):
        """Generate eSKD XML for employer declaration."""
        for rec in self:
            rec.agd_file = None
            root = etree.Element('eSKDUpload', Version="6.0")
            orgnr = etree.SubElement(root, 'OrgNr')
            orgnr.text = rec.company_id.company_registry or ''

            agd = etree.SubElement(root, 'Arbetsgivardeklaration')
            period = etree.SubElement(agd, 'Period')
            period.text = fields.Date.from_string(rec.date_start).strftime('%Y%m')

            for line in rec.line_ids:
                emp_el = etree.SubElement(agd, 'Anstalld')
                pnr = etree.SubElement(emp_el, 'PersonNr')
                pnr.text = line.personal_number or ''

                # Only include non-zero fields
                field_map = [
                    ('Ruta50', 'r50_bruttolon'),
                    ('Ruta51', 'r51_formaner'),
                    ('Ruta52', 'r52_avdrag'),
                    ('Ruta55', 'r55_full_avg_underlag'),
                    ('Ruta56', 'r56_full_avg'),
                    ('Ruta57', 'r57_vaxa_underlag'),
                    ('Ruta58', 'r58_vaxa_avg'),
                    ('Ruta59', 'r59_aldersp_underlag'),
                    ('Ruta60', 'r60_aldersp_avg'),
                    ('Ruta61', 'r61_sl_aldre_underlag'),
                    ('Ruta62', 'r62_sl_aldre_avg'),
                    ('Ruta81', 'r81_skatteavdrag_underlag'),
                    ('Ruta82', 'r82_avdragen_skatt'),
                ]
                for xml_name, field_name in field_map:
                    val = getattr(line, field_name, 0.0) or 0.0
                    if val:
                        el = etree.SubElement(emp_el, xml_name)
                        el.text = str(int(round(val)))

            xml_bytes = etree.tostring(root, pretty_print=True, encoding='ISO-8859-1')
            xml_str = xml_bytes.decode('ISO-8859-1')
            # Add DOCTYPE declaration
            xml_str = xml_str.replace(
                '?>',
                '?>\n<!DOCTYPE eSKDUpload PUBLIC '
                '"-//Skatteverket, Sweden//DTD Skatteverket eSKDUpload-DTD Version 6.0//SV" '
                '"https://www.skatteverket.se/download/18.3f4496fd14864cc5ac99cb1/1415022101213/eSKDUpload_6p0.dtd">')
            rec.agd_file = base64.b64encode(xml_str.encode('ISO-8859-1'))

    # ---- SKV API submission ----

    def action_send_to_skv(self):
        """Submit employer declaration to Skatteverket via API."""
        self.ensure_one()

        if not self.agd_file:
            self.generate_agd_file()
        if not self.agd_file:
            raise UserError(_(
                "Could not generate AGD file. Please run 'Calculate' first."))

        partner = self._get_skv_partner()
        if not partner or not partner.enable_skatteverket_api:
            raise UserError(_(
                "No Skatteverket API partner configured. "
                "Enable 'Skatteverket API' on a partner record in Contacts."))

        access_token = self._get_skv_access_token(partner)

        agd_api_url = (self.company_id.skv_agd_api_url
                       or self._get_skv_settings()['api_url'])

        xml_bytes = base64.b64decode(self.agd_file)

        headers = {
            'Authorization': 'Bearer %s' % access_token,
            'Content-Type': 'application/xml; charset=ISO-8859-1',
            'Accept': 'application/json',
        }

        try:
            response = requests.post(
                agd_api_url, data=xml_bytes, headers=headers, timeout=30)
            _logger.info("SKV AGD API response: %s %s",
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
                raise UserError(_("Authentication failed. Please retry."))
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
            raise UserError(_("Could not connect to Skatteverket API:\n%s") % str(e))

    # ---- Actions ----

    def action_download_agd_file(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s/%s/agd_file/%s?download=true' % (
                self._name, self.id, self.agd_file_name),
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

    # ---- Cron ----

    @api.model
    def _cron_create_agd(self):
        """Cron: create AGD for the latest completed payslip run."""
        # Find latest completed payslip run without an AGD
        existing_agd_runs = self.search([]).mapped('payslip_run_id')
        latest_run = self.env['hr.payslip.run'].search([
            ('state', '=', 'done'),
            ('id', 'not in', existing_agd_runs.ids if existing_agd_runs else [0]),
        ], order='date_end desc', limit=1)

        if not latest_run:
            return False

        if not latest_run.date_end:
            return False

        deadline = self._calculate_vat_deadline(
            fields.Date.from_string(latest_run.date_end), 1)

        agd = self.create({
            'payslip_run_id': latest_run.id,
            'date_start': latest_run.date_start,
            'date_stop': latest_run.date_end,
            'date': fields.Date.to_string(deadline),
            'target_move': 'posted',
        })

        if agd:
            try:
                agd.calculate()
                _logger.info('Cron: AGD created for payslip run %s', latest_run.name)
            except Exception as e:
                _logger.warning('Cron: AGD calculation failed: %s', e)

        return True


class AccountAgdDeclarationLine(models.Model):
    _name = 'account.agd.declaration.line'
    _description = 'AGD Declaration Line (per employee)'
    _order = 'employee_id'

    agd_id = fields.Many2one(
        'account.agd.declaration', string='AGD-deklaration',
        required=True, ondelete='cascade')
    employee_id = fields.Many2one(
        'hr.employee', string='Anställd', required=True)
    personal_number = fields.Char(
        string='Personnummer',
        help="Swedish personal identity number (personnummer).")

    # SKV form fields (ruta 50-82)
    r50_bruttolon = fields.Monetary('50. Bruttolön', currency_field='currency_id')
    r51_formaner = fields.Monetary('51. Förmåner', currency_field='currency_id')
    r52_avdrag = fields.Monetary('52. Avdrag', currency_field='currency_id')
    r55_full_avg_underlag = fields.Monetary(
        '55. Underlag full avg.', currency_field='currency_id')
    r56_full_avg = fields.Monetary(
        '56. Full avg. 31,42%', currency_field='currency_id')
    r57_vaxa_underlag = fields.Monetary(
        '57. Underlag växa-stöd', currency_field='currency_id')
    r58_vaxa_avg = fields.Monetary(
        '58. Växa-stöd 10,21%', currency_field='currency_id')
    r59_aldersp_underlag = fields.Monetary(
        '59. Underlag 66-79 år', currency_field='currency_id')
    r60_aldersp_avg = fields.Monetary(
        '60. Avg. 16,36%', currency_field='currency_id')
    r61_sl_aldre_underlag = fields.Monetary(
        '61. Underlag 80+ år', currency_field='currency_id')
    r62_sl_aldre_avg = fields.Monetary(
        '62. Särskild löneskatt 6,15%', currency_field='currency_id')
    r81_skatteavdrag_underlag = fields.Monetary(
        '81. Underlag skatteavdrag', currency_field='currency_id')
    r82_avdragen_skatt = fields.Monetary(
        '82. Avdragen skatt', currency_field='currency_id')

    currency_id = fields.Many2one(
        'res.currency', related='agd_id.currency_id')


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    agd_declaration_id = fields.Many2one(
        'account.agd.declaration', string='AGD',
        help="The employer declaration this payslip was included in.",
        readonly=True)


class AgdDemoGenerator(models.AbstractModel):
    _name = 'l10n_se_payroll_agd.agd_demo_generator'
    _description = 'AGD Demo Data Generator'

    @api.model
    def generate_demo_data(self):
        """Generate demo data: employee + payslip + AGD."""
        if self.env['account.agd.declaration'].search_count([]) > 0:
            _logger.info('AGD demo data already exists, skipping.')
            return True

        # Find or create employee with Swedish personal number
        employee = self.env['hr.employee'].search(
            [('identification_id', '=', '19800101-1234')], limit=1)
        if not employee:
            # Need at least a user linked, find demo user
            user = self.env.ref('base.user_demo', raise_if_not_found=False)
            if not user:
                _logger.warning('No demo user found, cannot create AGD demo.')
                return False
            # Find or create a work address
            work_address = self.env['res.partner'].search(
                [('name', '=', 'Demo Employee')], limit=1)
            if not work_address:
                work_address = self.env['res.partner'].create({
                    'name': 'Demo Employee',
                    'is_company': False,
                })
            employee = self.env['hr.employee'].create({
                'name': 'Demo Employee',
                'identification_id': '19800101-1234',
                'birthday': '1980-01-01',
                'work_contact_id': work_address.id,
                'user_id': user.id,
            })

        # Find an existing salary structure or create minimal one
        structure = self.env['hr.payroll.structure'].search(
            [('code', '=', 'SE-BASIC')], limit=1)
        if not structure:
            structure = self.env['hr.payroll.structure'].search([], limit=1)
        if not structure:
            _logger.warning('No salary structure found for AGD demo.')
            return False

        # Find a contract for the employee
        contract = self.env['hr.contract'].search(
            [('employee_id', '=', employee.id)], limit=1)
        if not contract:
            contract = self.env['hr.contract'].create({
                'name': 'Demo Contract',
                'employee_id': employee.id,
                'wage': 35000.0,
                'struct_id': structure.id,
                'date_start': fields.Date.today().replace(day=1),
                'state': 'open',
            })

        # Create a payslip run for current month
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

        # Create AGD
        deadline = self.env['account.declaration']._calculate_vat_deadline(
            month_end, 1)

        agd = self.env['account.agd.declaration'].create({
            'payslip_run_id': payslip_run.id,
            'date_start': month_start,
            'date_stop': month_end,
            'date': fields.Date.to_string(deadline),
            'target_move': 'posted',
        })

        if agd:
            try:
                agd.calculate()
                _logger.info(
                    'Demo AGD created: %s with %d employees',
                    agd.name, agd.employee_count)
            except Exception as e:
                _logger.warning('Demo AGD calculation warning: %s', e)

        return True
