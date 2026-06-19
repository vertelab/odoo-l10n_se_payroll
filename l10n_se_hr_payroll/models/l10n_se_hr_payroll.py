# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2014- Vertel AB (<http://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from dateutil.relativedelta import relativedelta
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval as eval
from datetime import timedelta, date, datetime, time
import calendar

import logging

_logger = logging.getLogger(__name__)


class HrPayslipLine(models.Model):
    _inherit = "hr.payslip.line"

    @api.depends("quantity", "amount", "rate")
    def _compute_total(self):
        for line in self:
            rounded_a_price = round(line.amount, 2)
            line.total = round(float(line.quantity) * rounded_a_price * (line.rate / 100.0), 2)

class HrPayslipWorkedDays(models.Model):
    _inherit = "hr.payslip.worked_days"

    hr_leave_id = fields.Many2one(comodel_name="hr.leave", string="hr leave id")


class hr_salary_rule(models.Model):
    _inherit = 'hr.salary.rule'

    salary_art = fields.Char(string='Salary art', help="Code to interchange payslip rows with other systems")

    @api.model
    def init_records(self):
        # ~ Changed "hr_payroll" to "hr_payroll_community" since "hr_payroll" is an enterprise module now
        hr_rule_basic = self.env['ir.model.data'].get_object_reference('hr_payroll_community', 'hr_rule_basic')
        self.env['hr.salary.rule'].browse(hr_rule_basic[1]).write({
            'active': False,
        })
        hr_rule_taxable = self.env['ir.model.data'].get_object_reference('hr_payroll_community', 'hr_rule_taxable')
        self.env['hr.salary.rule'].browse(hr_rule_taxable[1]).write({
            'active': False,
        })
        hr_rule_net = self.env['ir.model.data'].get_object_reference('hr_payroll_community', 'hr_rule_net')
        self.env['hr.salary.rule'].browse(hr_rule_net[1]).write({
            'active': False,
        })


class hr_contract(models.Model):
    _inherit = 'hr.contract'

    prel_tax_amount = fields.Float(string="Prel skatt kr", digits='Payroll', help="Ange preleminär skatt i kronor")

    def _wage_tax_base(self):
        self.wage_tax_base = (self.wage - self.aws_amount) + self.ded_amount

    type_id = fields.Many2one('hr.contract.type', string="Employee Category",
                              required=True, help="Employee category",
                              default=lambda self: self.env['hr.contract.type'].search([], limit=1))

    wage_tax_base = fields.Float(string="Lönunderlag", digits='Payroll',
                                 help="Uträknat löneunderlag för beräkning av preleminär skatt")
    prel_tax_tabel = fields.Char(string="Prel skatt info",
                                 help="Ange skattetabell/kolumn/ev jämkning som ligger till grund för angivet "
                                      "preleminärskatteavdrag")
    prel_tax_url = fields.Char(string="Skattetabeller SKV",
                               default="http://www.skatteverket.se/privat/skatter/arbeteochinkomst/skattetabeller.4"
                                       ".18e1b10334ebe8bc80005221.html",
                               readonly=True,
                               help="Ange skattetabell/kolumn/ev jämkning som ligger till grund för angivet "
                                    "preleminärskatteavdrag")
    vacation_days = fields.Float(string='Semesterdagar', digits='Payroll', help="Sparad semester i dagar.")
    annual_vacation_days = fields.Float(string='Årlig semesterrätt', default=25.0, help="Antal avtalade semesterdagar per år.")
    advance_vacation_days = fields.Float(string='Förskottssemesterdagar', default=0, help="Antal förskottssemesterdagar, nyanställd.")

    def _get_param(self, param, value):
        if not self.env['ir.config_parameter'].get_param(param):
            self.env['ir.config_parameter'].set_param(param, value)
        return self.env['ir.config_parameter'].get_param(param)

    def logthis(self, message):
        _logger.error(message)

    def evalthis(self, code, variables):
        eval(code, variables, mode='exec', nocopy=True)

    def get_leave_days(self, rule_id, worked_days):

        if (rule_id and rule_id == "sem_til") or (rule_id and rule_id == "sem_bet"):
            #_logger.warning(f"{rule_id=}")
            #_logger.warning(f"{worked_days=}")
            #code = self.env.ref(rule_id).work_entry_type_id.code if len(rule_id.split('.')) == 2 else rule_id
            leave_lines = []
            for key, val in worked_days.dict.items():
                #_logger.warning(f"{key=} {val=}")
                if "sem_bet" in key or (hasattr(val, 'work_entry_type_id') and 
                    val.work_entry_type_id and val.work_entry_type_id.code == 'sem_bet'):
                    leave_lines.append(val)
            if len(leave_lines) > 0:
                number_of_days = sum(line.number_of_days for line in leave_lines)
                return number_of_days
            else:
                return 0.0
        else:
            # _logger.error(f'get_leave_days: {self} {rule_id} {worked_days.dict}')
            code = self.env.ref(rule_id).work_entry_type_id.code if len(rule_id.split('.')) == 2 else rule_id            
            line = worked_days.dict.get(code, False)
            # _logger.error(f'get_leave_days: {code} {worked_days.dict}')
            # ~ _logger.error(f'get_leave_days: {line.number_of_days}')
            return line.number_of_days if line else 0.0

    def get_leave_hours(self, rule_id, worked_days):
        code = self.env.ref(rule_id).code if len(rule_id.split('.')) == 2 else rule_id
        line = worked_days.dict.get(code, False)
        #_logger.error(f'get_leave_hours: {code} {worked_days.dict}')
        # ~ _logger.error(f'get_leave_days: {line.number_of_days}')
        return line.number_of_hours if line else 0.0

    def raisethis(self, message):
        raise ValidationError(message)

    def is_rule(self, rules, code):
        return rules.dict.get(code, False)


class hr_employee(models.Model):
    _inherit = 'hr.employee'

    registration_number = fields.Char(
        string='Employee identification number', 
        copy=False, 
        help='Unique employee identification number.',
        groups="hr.group_hr_user"
    )

    nyk_id = fields.Many2one(
        'hr.nyk',
        related='job_id.nyk_id',
        string='NYK Code',
        store=True,
        help='Swedish Occupational Classification Code (NYK).'
             ' Inherited from job position.'
    )

    @api.depends("birthday")
    def _age(self):
        for employee in self:
            employee.age = 0
            if employee.birthday:
                employee.age = relativedelta(fields.Date.today(), employee.birthday).years

    age = fields.Integer(string="_compute_age", compute=_age, help="Age to calculate social security deduction")

    payslip_count = fields.Integer(
        string='Payslip Count',
        compute='_compute_payslip_count',
    )

    def _compute_payslip_count(self):
        payslip_data = self.env['hr.payslip'].sudo().read_group(
            [('employee_id', 'in', self.ids)],
            ['employee_id'],
            ['employee_id'],
        )
        mapped_data = {item['employee_id'][0]: item['employee_id_count'] for item in payslip_data}
        for employee in self:
            employee.payslip_count = mapped_data.get(employee.id, 0)

    def action_open_payslips(self):
        self.ensure_one()
        return {
            'name': 'Payslips',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }

class hr_payslip(models.Model):
    _inherit = 'hr.payslip'

    def compute_has_activities(self):
        for record in self:
            if record.activity_ids:
                record.has_activities = True
            else:
                record.has_activities = False
    has_activities = fields.Boolean(compute=compute_has_activities)

    period_id = fields.Many2one(comodel_name='account.period', 
                                string="Salary period",
                                help="Selected payroll month. Deviations are fetched from previous period.",
                                default=lambda self: self.env['account.period'].date2period(fields.Date.today()),
                                required=True,
                                tracking=1,
                                check_company=True)
    date_start = fields.Date(related='period_id.date_start',readonly=True)
    date_stop = fields.Date(related='period_id.date_stop',readonly=True)

    details_by_salary_rule_category = fields.One2many('hr.payslip.line',
                                                      compute='_compute_details_by_salary_rule_category',
                                                      string='Details by Salary Rule Category',
                                                      help="Details from the salary rule category")

    deviation_period_label = fields.Char(
        string="Deviation period",
        compute="_compute_deviation_period_label",
        help="The period from which deviations are fetched",
        readonly=True,
    )    

    payday_date = fields.Date(
        string="Payment day",
        compute="_compute_payday_date",
        store=True,
        readonly=True,
    )

    payday_policy_used = fields.Selection(
        [
            ("next_business_day", "Next business day"),
            ("nearest_business_day", "Nearest business day"),
            ("previous_or_same_business_day", "Nearest business day on or before target date"),
        ],
        string="Payday rule",
        compute="_compute_payday_date",
        store=True,
        readonly=True,
    )

    @api.depends("period_id")
    def _compute_deviation_period_label(self):
        Period = self.env["account.period"]
        for slip in self:
            slip.deviation_period_label = "-"
            if not slip.period_id:
                continue

            prev_period = Period.search(
                [
                    ("date_start", "<", slip.period_id.date_start),
                    ("company_id", "=", slip.period_id.company_id.id),
                    ("special", "=", False),
                ],
                order="date_start desc",
                limit=1,
            )

            if prev_period:
                if prev_period.date_start:
                    slip.deviation_period_label = prev_period.date_start.strftime("%b %Y")
                else:
                    slip.deviation_period_label = prev_period.display_name or prev_period.name

    def _is_bank_day(self, day, company):
        if day.weekday() >= 5:
            return False

        day_start = datetime.combine(day, time.min)
        day_end = datetime.combine(day, time.max)

        holiday_count = self.env["resource.calendar.leaves"].search_count([
            ("resource_id", "=", False),
            ("date_from", "<=", day_end),
            ("date_to", ">=", day_start),
            ("company_id", "in", [False, company.id]),
        ])
        return holiday_count == 0

    def _next_bank_day(self, day, company):
        d = day
        for _i in range(31):
            if self._is_bank_day(d, company):
                return d
            d += timedelta(days=1)
        return day

    def _prev_bank_day(self, day, company):
        d = day
        for _i in range(31):
            if self._is_bank_day(d, company):
                return d
            d -= timedelta(days=1)
        return day

    def _resolve_payday(self, base_day, company, policy):
        if policy == "next_business_day":
            return self._next_bank_day(base_day, company)

        if policy == "nearest_business_day":
            prev_d = self._prev_bank_day(base_day, company)
            next_d = self._next_bank_day(base_day, company)
            if (base_day - prev_d) <= (next_d - base_day):
                return prev_d
            return next_d

        return self._prev_bank_day(base_day, company)

    @api.depends(
        "period_id",
        "period_id.date_start",
        "company_id",
        "company_id.payroll_payday_day",
        "company_id.payroll_payday_policy",
    )
    def _compute_payday_date(self):
        for slip in self:
            slip.payday_date = False
            slip.payday_policy_used = False

            if not slip.period_id or not slip.period_id.date_start or not slip.company_id:
                continue

            company = slip.company_id
            policy = company.payroll_payday_policy or "previous_or_same_business_day"
            target_day = company.payroll_payday_day or 25

            year = slip.period_id.date_start.year
            month = slip.period_id.date_start.month
            last_day = calendar.monthrange(year, month)[1]
            target_day = min(max(target_day, 1), last_day)

            base_date = slip.period_id.date_start.replace(day=target_day)
            resolved = self._resolve_payday(base_date, company, policy)

            slip.payday_date = resolved
            slip.payday_policy_used = policy


    def move_activites_to_payslip(self):
        for record in self:
            if not record.employee_id:
                continue
            activity_obj = self.env['mail.activity']
            domain = [
                ('date_deadline','>=',record.period_id.date_start),
                ('date_deadline','<=',record.period_id.date_stop),
            ]
            # employee_id may not exist on mail.activity in all Odoo versions
            if 'employee_id' in activity_obj._fields:
                domain.append(('employee_id','=',record.employee_id.id))
            else:
                domain.extend([
                    ('res_model','=','hr.employee'),
                    ('res_id','=',record.employee_id.id),
                ])
            activites = activity_obj.search(domain)
            for activity in activites:
                model = self.env['ir.model'].search([('model','=','hr.payslip')])
                activity.res_model = model.model
                activity.res_model_id = model.id
                activity.res_id = record.id
    
    @api.model_create_multi
    def create(self, vals_list):
        #_logger.warning(f"{vals_list=}")
        res = super(hr_payslip, self).create(vals_list)
        #_logger.warning(f"{res=}")        
        res.move_activites_to_payslip()

        return res

    def get_number_of_days(self):
        year = self.date_from.year
        if year % 4 == 0:
            return 366
        return 365

    def _compute_details_by_salary_rule_category(self):
        for payslip in self:
            payslip.details_by_salary_rule_category = payslip.mapped('line_ids').filtered(lambda line: line.category_id)

    @api.onchange('employee_id', 'period_id')
    def onchange_employee(self):
        manual_inputs = {line.code: line.amount_qty for line in self.input_line_ids if line.code}

        super(hr_payslip, self).onchange_employee()

        for line in self.input_line_ids:
            if line.code in manual_inputs:
                line.amount_qty = manual_inputs[line.code]

        if self.period_id:
            self.date_from = self.period_id.date_start
            self.date_to = self.period_id.date_stop
            
            self.name = _("Salary Slip of %s for %s") % (
                self.employee_id.name,
                self.period_id.date_start.strftime('%B-%Y')
            )

    def get_payslip_vals_period(self, run, employee):
        date_from = run.period_id.prev().date_start
        date_to = run.period_id.prev().date_stop

        contract_ids = employee.contract_id.ids

        contract = self.env["hr.contract"].browse(contract_ids[0])
        contracts = self.env["hr.contract"].browse(contract_ids)
        return {
            "employee_id": employee.id,
            'period_id': run.period_id.id,
            "name": _("Salary Slip of %s for %s") % (employee.name,
                                                     run.period_id.date_start.strftime(
                                                         '%B-%Y') if run.period_id else 'None',
                                                     ),
            "struct_id": contract.struct_id.id,
            "contract_id": contract.id,
            "payslip_run_id": run.id,
            "input_line_ids": [
                (0, 0, x) for x in self.get_inputs(contracts, date_from, date_to)
            ],
            "worked_days_line_ids": [
                (0, 0, x) for x in self.get_worked_day_lines(contracts, date_from, date_to)
            ],
            "date_from": date_from,
            "date_to": date_to,
            "credit_note": run.credit_note,
            "company_id": employee.company_id.id,
        }

    @api.model
    def get_slip_line(self, code):
        return self.details_by_salary_rule_category.filtered(lambda l: l.code == code).mapped(
            lambda v: {'name': v.name, 'quantity': v.quantity, 'rate': v.rate, 'amount': v.amount, 'total': v.total})

    @api.model
    def get_slip_line_total(self, code):
        return sum(self.details_by_salary_rule_category.filtered(lambda l: l.code == code).mapped('total'))

    @api.model
    def get_slip_line_acc(self, codes):
        year = self.date_start.year
        start_date = date(year, 1, 1)
        stop_date = date(year, 12, 31)
        res = {c: 0.0 for c in codes}
        for line in self.env['hr.payslip'].search([('employee_id', '=', self.employee_id.id)]).mapped(
                'details_by_salary_rule_category').filtered(lambda c: c.code in codes):
            res[line.code] += line.total
        return res

    def _compute_leave_days(self, contract, day_from, day_to):
        """
        Override to fix code field handling for leaves without work_entry_type_id
        """
        from pytz import timezone
        from odoo.tools.translate import _
        
        leaves_positive = (
            self.env["ir.config_parameter"].sudo().get_param("payroll.leaves_positive")
        )
        leaves = {}
        calendar = contract.resource_calendar_id
        tz = timezone(calendar.tz)
        day_leave_intervals = contract.employee_id.list_leaves(
            day_from, day_to, calendar=contract.resource_calendar_id
        )
        for day, hours, leave in day_leave_intervals:
            import pytz
            day_start_utc = tz.localize(datetime.combine(day, datetime.min.time())).astimezone(pytz.UTC).replace(tzinfo=None)
            day_end_utc = tz.localize(datetime.combine(day, datetime.max.time())).astimezone(pytz.UTC).replace(tzinfo=None)
            
            is_global_leave = self.env['resource.calendar.leaves'].search_count([
                ('resource_id', '=', False),
                ('date_from', '<=', day_end_utc),
                ('date_to', '>=', day_start_utc),
                '|', ('calendar_id', '=', False), ('calendar_id', '=', calendar.id),
                ('company_id', 'in', [False, contract.company_id.id])
            ])
            
            if is_global_leave > 0:
                continue

            holiday = leave[:1].holiday_id
            # Fix: Explicitly check if work_entry_type_id is set
            work_entry_type = holiday.holiday_status_id.work_entry_type_id
            if work_entry_type:
                code = work_entry_type.code or "GLOBAL"
                sequence = work_entry_type.sequence or 5
            else:
                code = "GLOBAL"
                sequence = 5
            
            current_leave_struct = leaves.setdefault(
                holiday.holiday_status_id,
                {
                    "name": holiday.holiday_status_id.name or _("Global Leaves"),
                    "sequence": sequence,
                    "code": code,
                    "number_of_days": 0.0,
                    "number_of_hours": 0.0,
                    "contract_id": contract.id,
                },
            )
            if leaves_positive:
                current_leave_struct["number_of_hours"] += hours
            else:
                current_leave_struct["number_of_hours"] -= hours
            work_hours = calendar.get_work_hours_count(
                tz.localize(datetime.combine(day, datetime.min.time())),
                tz.localize(datetime.combine(day, datetime.max.time())),
                compute_leaves=False,
            )
            if work_hours:
                if leaves_positive:
                    current_leave_struct["number_of_days"] += hours / work_hours
                else:
                    current_leave_struct["number_of_days"] -= hours / work_hours
        return leaves.values()

    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):
        """
        @param contracts: Browse record of contracts
        @return: returns a list of dict containing the input that should be
        applied for the given contract between date_from and date_to
        """
        res = []
        for contract in contracts.filtered(
                lambda contract: contract.resource_calendar_id
        ):
            day_from = datetime.combine(date_from, datetime.min.time())
            day_to = datetime.combine(date_to, datetime.max.time())
            day_contract_start = datetime.combine(contract.date_start, datetime.min.time())
            # Support for the hr_public_holidays module.

            context_val = {'employee_id': self.employee_id.id, 'exclude_public_holidays': True, 'compute_payslip': True}
            contract = contract.with_context(context_val)

            # only use payslip day_from if it's greater than contract start date
            if day_from < day_contract_start:
                day_from = day_contract_start
            # == compute leave days == #
            leaves = self._compute_leave_days(contract, day_from, day_to)
            res.extend(leaves)
            # == compute worked days == #
            attendances = self._compute_worked_days(contract, day_from, day_to)
            res.append(attendances)
        return res


class HrPayrollStructure(models.Model):
    _inherit = "res.company"

    payroll_payday_day = fields.Integer(
        string="Payday",
        default=25,
        help="Day of the month that salary is paid (1-31).",
    )

    payroll_payday_policy = fields.Selection(
        [
            ("next_business_day", "Next business day"),
            ("nearest_business_day", "Nearest business day"),
            ("previous_or_same_business_day", "Nearest business day on or before target date"),
        ],
        string="Rule for bank holidays",
        default="previous_or_same_business_day",
        required=True,
        help="How the payday is moved if it falls on a bank holiday.",
    )

    payroll_cutoff_day = fields.Integer(
        string="Deviation cut off date",
        help="Optional cut off date for deviations (1-31).",
    )

    @api.constrains("payroll_payday_day", "payroll_cutoff_day")
    def _check_payroll_day_ranges(self):
        for rec in self:
            if rec.payroll_payday_day and not (1 <= rec.payroll_payday_day <= 31):
                raise ValidationError(_("Payday must be between 1 and 31."))
            if rec.payroll_cutoff_day and not (1 <= rec.payroll_cutoff_day <= 31):
                raise ValidationError(_("Deviation cut off must be between 1 och 31."))


    def sync_hr_payroll_structure(self):
        """FIX ME: when a copy of hr.payroll.structure is made on company B, the rule is not attached
         to the structure"""
        company_id = self.env.ref('base.main_company')

        if self.env.company.id != company_id.id:
            payroll_structure_ids = self.env['hr.payroll.structure'].with_company(company_id).search([
                ('company_id', '=', company_id.id)])
            for payroll_structure_id in payroll_structure_ids:
                structure_id = self.env['hr.payroll.structure'].with_company(self.env.company).search([
                    ('code', '=', payroll_structure_id.code), ('company_id', '=', self.env.company.id)])

                if not structure_id:
                    structure_id = self.env['hr.payroll.structure'].create({
                        'name': payroll_structure_id.name,
                        'code': payroll_structure_id.code,
                        'company_id': self.env.company.id,
                        'parent_id': payroll_structure_id.parent_id.id,
                        'rule_ids': payroll_structure_id.rule_ids.ids
                    })
                structure_id.write({
                    'rule_ids': [(4, rule.id) for rule in payroll_structure_id.rule_ids]
                })

    def sync_hr_payroll_salary_rule_category(self):
        company_id = self.env.ref('base.main_company')
        if self.env.company.id != company_id.id:
            payroll_salary_rule_category_ids = self.env['hr.salary.rule.category'].with_company(company_id).search([
                ('company_id', '=', company_id.id)])
            for payroll_salary_rule_category_id in payroll_salary_rule_category_ids:
                salary_rule_category_id = self.env['hr.salary.rule.category'].with_company(self.env.company).search([
                    ('code', '=', payroll_salary_rule_category_id.code)])
                if not salary_rule_category_id:
                    self.env['hr.salary.rule.category'].create({
                        'name': payroll_salary_rule_category_id.name,
                        'code': payroll_salary_rule_category_id.code,
                        'parent_id': payroll_salary_rule_category_id.parent_id.id,
                        'note': payroll_salary_rule_category_id.note,
                        'company_id': self.env.company.id,
                    })

    def sync_hr_payroll_salary_rule(self):
        company_id = self.env.ref('base.main_company')
        if self.env.company.id != company_id.id:
            payroll_salary_rule_ids = self.env['hr.salary.rule'].with_company(company_id).search([
                ('company_id', '=', company_id.id)])
            for payroll_salary_rule_id in payroll_salary_rule_ids:
                salary_rule_id = self.env['hr.salary.rule'].with_company(self.env.company).search([
                    ('code', '=', payroll_salary_rule_id.code), ('company_id', '=', self.env.company.id)])

                if not salary_rule_id:
                    self.env['hr.salary.rule'].create({
                        'name': payroll_salary_rule_id.name,
                        'category_id': payroll_salary_rule_id.category_id.id,
                        'code': payroll_salary_rule_id.code,
                        'sequence': payroll_salary_rule_id.sequence,
                        'active': payroll_salary_rule_id.active,
                        'appears_on_payslip': payroll_salary_rule_id.appears_on_payslip,
                        'company_id': self.env.company.id,
                        'condition_select': payroll_salary_rule_id.condition_select,
                        'condition_python': payroll_salary_rule_id.condition_python,
                        'register_id': payroll_salary_rule_id.register_id.id,
                        'amount_select': payroll_salary_rule_id.amount_select,
                        'quantity': payroll_salary_rule_id.quantity,
                        'amount_fix': payroll_salary_rule_id.amount_fix,
                        'note': payroll_salary_rule_id.note,
                        'parent_rule_id': payroll_salary_rule_id.parent_rule_id.id,
                        'account_debit': payroll_salary_rule_id.account_debit.id,
                        'account_credit': payroll_salary_rule_id.account_credit.id,
                        'account_tax_id': payroll_salary_rule_id.account_tax_id.id,
                        'tax_base_id': payroll_salary_rule_id.tax_base_id.id,
                    })
