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
from odoo.exceptions import except_orm, Warning, RedirectWarning, UserError, ValidationError
from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval as eval
from datetime import timedelta, date, datetime
import random
import dateutil.relativedelta

import logging

_logger = logging.getLogger(__name__)


class HrPayslipLine(models.Model):
    _inherit = "hr.payslip.line"

    @api.depends("quantity", "amount", "rate")
    def _compute_total(self):
        for line in self:
            line.total = round(float(line.quantity) * line.amount * line.rate / 100)


class HrPayslipWorkedDays(models.Model):
    _inherit = "hr.payslip.worked_days"

    hr_leave_id = fields.Many2one(comodel_name="hr.leave", string="hr leave id")


class hr_salary_rule(models.Model):
    _inherit = 'hr.salary.rule'

    salary_art = fields.Char(string='Salary art', help="Code to interchange payslip rows with other systems")

    # payslip_character = fields.Selection([
    #     ("minus", "Minus"),
    #     ("parentheses", "Parentheses"),
    # ],default=False)

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
    # ~ car_company_amount = fields.Float('Bruttolöneavdrag för bil', digits_compute=dp.get_precision('Payroll'),
    # help="Bruttolöneavdraget för företagsbil, dvs företagets kostnad för företagsbilen") ~ car_employee_deduction =
    # fields.Float(string='Förmånsvärde för bil', digits_compute=dp.get_precision('Payroll'), help="Beräknat
    # förmånsvärde för bil från skatteverket",) ~ car_deduction_url = fields.Char(string='Förmånsvärdesberäkning
    # SKV', default="http://www.skatteverket.se/privat/skatter/biltrafik/bilformansberakning", readonly=True,
    # help="Beräknat förmånsvärde för bil från skatteverket")
    vacation_days = fields.Float(string='Semesterdagar', digits='Payroll', help="Sparad semester i dagar", )

    # ~ office_fund = fields.Float(string='Office fund', digits_compute=dp.get_precision('Payroll'), help="Fund for
    # personal office supplies",)

    # hourly_employee = fields.Float(string="Hourly employee")

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
            _logger.warning(f"{rule_id=}")
            _logger.warning(f"{worked_days=}")
            code = self.env.ref(rule_id).code if len(rule_id.split('.')) == 2 else rule_id
            leave_lines = []
            for key, val in worked_days.dict.items():
                _logger.warning(f"{key=} {val=}")
                if "sem_bet" in key:
                    leave_lines.append(val)
            if len(leave_lines) > 0:
                number_of_days = 0
                for line in leave_lines:
                    number_of_days += line.number_of_days
                    _logger.warning(f"{number_of_days=}")
                return number_of_days
            else:
                return 0.0
        else:
            # _logger.error(f'get_leave_days: {self} {rule_id} {worked_days.dict}')
            code = self.env.ref(rule_id).code if len(rule_id.split('.')) == 2 else rule_id
            line = worked_days.dict.get(code, False)
            # _logger.error(f'get_leave_days: {code} {worked_days.dict}')
            # ~ _logger.error(f'get_leave_days: {line.number_of_days}')
            return line.number_of_days if line else 0.0

    # def get_leave_days2(self, rule_id, worked_days): #rule_id = "sem_bet" if rule_id and rule_id == "sem_bet":
    # _logger.warning("LOOK HERE"*100) _logger.error(f'get_leave_days: {self} {rule_id} {worked_days.dict}') code =
    # self.env.ref(rule_id).code if len(rule_id.split('.')) == 2 else rule_id #{'WORK100': hr.payslip.worked_days(15,
    # ), 'Legal Leaves 2022': hr.payslip.worked_days(13,), 'Legal Leaves 2023': hr.payslip.worked_days(14,)} #line =
    # worked_days.dict.get(code,False) if rule_id and rule_id == "sem_bet": _logger.error(f'get_leave_days: {code} {
    # worked_days.dict}') for key,val in worked_days.dict: _logger.warning(f"{key=} {val=}") if "Legal Leaves" in
    # key: line.append(val) if len(line) == 0: line = False else: return 4 return line.number_of_days if line else 0.0

    def get_leave_hours(self, rule_id, worked_days):
        code = self.env.ref(rule_id).code if len(rule_id.split('.')) == 2 else rule_id
        line = worked_days.dict.get(code, False)
        _logger.error(f'get_leave_hours: {code} {worked_days.dict}')
        # ~ _logger.error(f'get_leave_days: {line.number_of_days}')
        return line.number_of_hours if line else 0.0

    def raisethis(self, message):
        raise Warning(message)

    def is_rule(self, rules, code):
        return rules.dict.get(code, False)


class hr_employee(models.Model):
    _inherit = 'hr.employee'

    @api.depends("birthday")
    def _age(self):
        for employee in self:
            employee.age = 0
            if employee.birthday:
                employee.age = relativedelta(fields.Date.today(), employee.birthday).years

    age = fields.Integer(string="_compute_age", compute=_age, help="Age to calculate social security deduction")


class hr_payslip(models.Model):
    _inherit = 'hr.payslip'

    period_id = fields.Many2one(comodel_name='account.period', string="Period",
                                readonly=True,
                                required=True,
                                default=lambda self: self.env['account.period'].date2period(fields.Date.today()),
                                states={"draft": [("readonly", False)]},
                                tracking=1, )
    date_start = fields.Date(related='period_id.date_start')
    date_stop = fields.Date(related='period_id.date_stop')

    details_by_salary_rule_category = fields.One2many('hr.payslip.line',
                                                      compute='_compute_details_by_salary_rule_category',
                                                      string='Details by Salary Rule Category',
                                                      help="Details from the salary rule category")
    
#Work in progres
    # allocation_display = fields.Char(related='employee_id.allocation_display') #Dont know about this one?
    # collected_vacation_days = fields.Date(string="Collected Vacation days", compute="_compute_vacation_days")

    # def _compute_vacation_days(self):
    #     year = date.strftime(date.today().year, "%Y")
    #     _logger.error(f"{year=}")
    #     april = date.strftime('03-01', "%m-%d").strftime('%m-%d')
    #     employed_days = date.today()
    #     _logger.error(f"{date.today()=}")
    #     _logger.error(f"{employed_days=}")
    #     allocation = self.allocation_display
    #     _logger.error(f"{allocation=}")
    #     step = allocation * employed_days
    #     _logger.error(f"{self.allocation_display=}")
    #     _logger.error(f"{step=}")
    #     res = step/date.year
    #     _logger.error(f"{date.year=}")
    #     _logger.error(f"{res=}")
    #     return res

    # last_salary_payslip = fields.Boolean(string="Last Salary", readonly=False)

    # @api.onchange('last_salary_payslip')
    # def onchange_employee_last_salary(self):
    #     # super(hr_payslip, self).onchange_employee_last_salary()
    #     _logger.error(f"{self.last_salary_payslip=}")
    #     if self.last_salary_payslip == True:
    #         self.date_from = self.period_id.date_start - dateutil.relativedelta.relativedelta(months=1)
    #         _logger.error(f"{self.date_from=}")
    #         if self.contract_id.date_end:
    #             self.date_to = self.contract_id.date_end
    #         elif self.contract_id.date_end == None:
    #             self.date_to = self.period_id.date_stop
    #         _logger.error(f"{self.date_to=}")
    #         self.name = _("Salary Slip of %s for %s") % (
    #             self.employee_id.name,
    #             self.period_id.date_start.strftime('%B-%Y') if self.period_id else 'None',
    #         )

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
        super(hr_payslip, self).onchange_employee()
        # if self.choose_date_method == "date_then" and self.period_id.date_start and self.period_id.date_stop:

        if not self.period_id:
            self.period_id = self.period_id.now()
            raise UserError('pelle %s' % self.env['account.period'].find())

        self.date_from = self.period_id.date_start - dateutil.relativedelta.relativedelta(months=1)
        self.date_to = self.period_id.date_stop - dateutil.relativedelta.relativedelta(months=1)
        self.name = _("Salary Slip of %s for %s") % (
            self.employee_id.name,
            self.period_id.date_start.strftime('%B-%Y') if self.period_id else 'None',
            )
        return
    
# Might be casing a problem or maby not useful for now

    # @api.onchange('employee_id', 'period_id')
    # def onchange_employee_date_now(self):
    #     # super(hr_payslip, self).onchange_employee_date_now()
    #     if self.choose_date_method == "date_now":
    #         self.date_from = self.period_id.date_start
    #         self.date_to = self.period_id.date_stop
    #         self.name = _("Salary Slip of %s for %s") % (
    #             self.employee_id.name,
    #             self.period_id.date_start.strftime('%B-%Y') if self.period_id else 'None',
    #         )
    #     return

    # def compute_date_method(self):
    #      self.choose_date_method = (
    #          self.env["ir.config_parameter"].sudo().get_param("l10n_se_hr_payroll.choose_date_method")
    #      )

    # choose_date_method = fields.Selection([
    #      ("date_now", "Same date as period"),
    #      ("date_then", "A month after period"), ],
    #      store=True, compute="compute_date_method", readonly=False, default="date_then")

    # _logger.error(f"{choose_date_method=}")
    # compute = "compute_date_method")

    def get_payslip_vals_period(self, run, employee):
        date_from = run.period_id.prev().date_start
        date_to = run.period_id.prev().date_stop

        contract_ids = employee.contract_id.ids

        # ~ contract_ids = employee._get_contracts(
        # ~ date_from=period.date_start, date_to=period.date_stop
        # ~ ).ids
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
    def get_slip_line_acc(self, code):
        year = datetime.now().year
        start_date = datetime(year, 1, 1)
        return sum(self.env['hr.payslip'].search(
            [('employee_id', '=', self.employee_id.id), ('date_from', '>=', start_date.strftime('%Y-%m-%d')),
             ('date_to', '<=', self.date_to)]).mapped('details_by_salary_rule_category').filtered(
            lambda l: l.code == code).mapped('total'))

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

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
