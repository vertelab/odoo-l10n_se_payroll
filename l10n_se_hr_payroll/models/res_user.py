# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from odoo import fields, models, api, _

from odoo.exceptions import UserError, ValidationError, RedirectWarning, Warning
import logging
import datetime

_logger = logging.getLogger(__name__)

class UserPayslipLine(models.TransientModel):
    _name = "user.payslip.line"
    _description = "User Payslip Line"
    # ~ salary_rule_id = fields.Many2one("user.salary.rule", string="Rule", required=True)
    salary_rule = fields.Char(string='Salary Rule', size=10, trim=True, )
    code = fields.Char(string="Code")
    name = fields.Char(string="Name")
    quantity = fields.Char(string="Quantity")
    category_id = fields.Many2one("user.salary.rule.category")
    category = fields.Char(string="Category")
    amount = fields.Float(string='Amount')
    sequence = fields.Integer(string='Sequence')
    
    
    user_payslip_id = fields.Many2one(
        "user.payslip"
    )
    user_payslip_line_original_id = fields.Many2one(
        "hr.payslip.line",
    )
    total = fields.Float(string="Total")
    rate = fields.Float(string="rate")


class UserSalaryRule(models.TransientModel):
    _name = "user.salary.rule"
    _description = "User Salary Rule"
    appears_on_payslip = fields.Boolean(string="Appears on Payslip")
    salary_art = fields.Char(string="Salary art")


class UserSalaryCategory(models.TransientModel):
    _name = "user.salary.rule.category"
    _description = "User Salary Rule Category"
    code = fields.Char(string="Code")


class UserContract(models.TransientModel):
    _name = "user.contract"
    _description = "User Contract"
    wage_tax_base = fields.Float(string="Lönunderlag", digits='Payroll',
                                 help="Uträknat löneunderlag för beräkning av preleminär skatt")
    prel_tax_tabel = fields.Char(string="Prel skatt info",
                                 help="Ange skattetabell/kolumn/ev jämkning som ligger till grund för angivet preleminärskatteavdrag")
    resource_calendar_id = fields.Many2one("user.calendar")
    name = fields.Char(string="Name")
    # employee_fund = fields.Many2one(string="Employee Fund", comodel_name='account.analytic.account',
    #                                 help="Use this account together with marked salary rule")
    employee_fund_balance = fields.Monetary(string='Balance', currency_field='currency_id')
    employee_fund_name = fields.Char(string='Name')
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency of the Payment Transaction"
    )

    # hr_contract_id = fields.Many2one(
    #     "user.contract", string="Contract", required=True, index=True
    # )

    table_number = fields.Integer(string="Tax Table")
    column_number = fields.Selection(
        [('column1', "Column 1"), ('column2', "Column 2"), ('column3', "Column 3"), ('column4', "Column 4"),
         ('column5', "Column 5"), ('column6', "Column 6")], 'Tax Column')
    # hr_payroll_taxable_id = fields.Many2one('payroll.taxtable', string="Payroll Taxable")
    # taxable_lines = fields.One2many("payroll.taxtable.line", "payroll_taxable_id", string="Taxable Lines")


class UserCalender(models.TransientModel):
    _name = "user.calendar"
    _description = "User Calendar"
    name = fields.Char(string="Name")


class UserWorkdays(models.TransientModel):
    _name = "user.workdays"
    _description = "User Workdays"
    name = fields.Char(string="Name")
    code = fields.Char(string="code")
    number_of_hours = fields.Float(string="Number of hours")


class UserPayslipWorkedDays(models.TransientModel):
    _name = "user.payslip.worked_days"
    _description = "Payslip Worked Days"
    _order = "payslip_id, sequence"

    name = fields.Char(string="Description", required=False)
    payslip_id = fields.Many2one(
        "user.payslip", string="Pay Slip", required=False, ondelete="cascade", index=True
    )
    sequence = fields.Integer(required=False, index=False, default=10)
    code = fields.Char(
        required=False, help="The code that can be used in the salary rules"
    )
    number_of_days = fields.Float(string="Number of Days")
    number_of_hours = fields.Float(string="Number of Hours")
    contract_id = fields.Many2one(
        "user.contract",
        string="Contract",
        required=False,
        help="The contract for which applied this input",
    )


class UserLeave(models.TransientModel):
    _name = "user.leave"
    _description = "User Leave"
    date_from = fields.Datetime()
    date_to = fields.Datetime()
    number_of_days_temp = fields.Float(string="Number of days")
    payslip_id = fields.Many2one(
        "user.payslip", string="Pay Slip", required=False, ondelete="cascade", index=True
    )
    holiday_status_id = fields.Many2one(
        "user.holiday.status"
    )


class UserHolidayStatus(models.TransientModel):
    _name = "user.holiday.status"
    _description = "User Holiday Status"
    name = fields.Char(string="name")


class UserPayslip(models.TransientModel):
    _name = "user.payslip"
    _description = "User Payslip"

    # def get_legal_leaves_consumed(self, year = False):
    #     self = self.sudo()
    #     return self.payslip_id.get_legal_leaves_consumed(year)

    def get_legal_leaves_consumed(self):
        self = self.sudo()
        return self.payslip_id.get_legal_leaves_consumed()

    def get_legal_leaves_status(self):
        self = self.sudo()
        stop_date = self.payslip_id.date_to
        _logger.error(f"{stop_date=}")
        return self.payslip_id.get_legal_leaves_status()

    def get_slip_date_to(self):
        self = self.sudo()
        return self.payslip_id.date_from

    def get_slip_date_from(self):
        self = self.sudo()
        return self.payslip_id.date_to

    # @api.model
    # def get_legal_leaves_consumed(self, year = False):
    #     # if not year:
    #         # year = datetime.datetime.now().year
    #     # start_date = datetime.datetime(year,1,1)
    #     # stop_date = datetime.datetime(year,12,30)
    #     remaining_leaves
    #     stop_date = self.get_slip_date_to()
    #     return abs(sum(self.env['hr.leave.allocation'].search([('employee_id', '=', self.employee_id.id), ('date_to', '<=',stop_date.strftime('%Y-%m-%d') ), ('state', '=', 'validate')]).filtered(lambda h: h.holiday_status_id.legal_leave == True).mapped('number_of_days')))

    worked_days_line_ids = fields.One2many(
        "user.payslip.worked_days",
        "payslip_id",
        string="Payslip Worked Days",
    )

    # social_normal_fees

    # def _holiday_ids(self):
    #     for rec in self:
    #         # ~ rec.holiday_ids = rec.env['hr.leave'].search([('state','=','validate'),('employee_id','=',rec.employee_id.id),('type','=','remove')]).filtered(lambda h: h.date_from[:10>
    #         rec.holiday_ids = rec.env['hr.leave'].search([('state','=','validate'),('employee_id','=',rec.employee_id.id)]).filtered(lambda h: h.date_from.date()<= rec.date_to and h.da>
    holiday_ids = fields.One2many('user.leave', "payslip_id")

    allocation_used_display = fields.Char(related='employee_id.allocation_used_display')
    allocation_display = fields.Char(related='employee_id.allocation_display')

    line_ids = fields.One2many(
        "user.payslip.line", inverse_name='user_payslip_id'
    )

    name = fields.Char(
        string="Payslip Name", readonly=True, states={"draft": [("readonly", False)]}
    )
    number = fields.Char(
        string="Reference",
        readonly=True,
    )
    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Employee",
    )

    leave_allocation_id = fields.Many2one(
        "hr.leave.allocation",
        string="Leave allocation",
    )

    contract_id = fields.Many2one(
        comodel_name="user.contract",
        string="Employee",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("verify", "Waiting"),
            ("done", "Done"),
            ("cancel", "Rejected"),
        ],
        string="Status",
        readonly=True,
        help="""* When the payslip is created the status is \'Draft\'
        \n* If the payslip is under verification, the status is \'Waiting\'.
        \n* If the payslip is confirmed then status is set to \'Done\'.
        \n* When user cancel payslip the status is \'Rejected\'.""",
    )
    paid = fields.Boolean(
        string="Made Payment Order ? ",
        readonly=True,
    )
    credit_note = fields.Boolean(
        string="Credit Note",
        readonly=True,
        help="Indicates this payslip has a refund of another",
    )
    payslip_run_id = fields.Many2one(
        comodel_name="hr.payslip.run",
        string="Payslip Batches",
    )
    period_id = fields.Many2one(comodel_name='account.period', string="Period",
                                readonly=True, )

    # user_payslip_id2 = fields.Many2one(
    #     "user.payslip"
    # )

    payslip_id = fields.Many2one(comodel_name='hr.payslip')

    @api.model
    def get_slip_line(self, code):
        self = self.sudo()
        lines = self.payslip_id.details_by_salary_rule_category.filtered(lambda l: l.code == code).mapped(lambda v:
                                                                                                          {
                                                                                                              'name': v.name,
                                                                                                              'quantity': v.quantity,
                                                                                                              'rate': v.rate,
                                                                                                              'amount': v.amount,
                                                                                                              'total': v.total,
                                                                                                              'amount_percentage': v.amount_percentage,
                                                                                                              })
        if len(lines) > 0:
            return lines
        else:
            return [{'amount':0,'amount_percentage': 0.0,'total': 0}]
        

    @api.model
    def get_slip_line_total(self, code):
        self = self.sudo()
        return self.payslip_id.get_slip_line_total(code)

    @api.model
    def get_slip_line_acc(self, code):
        self = self.sudo()
        return self.payslip_id.get_slip_line_acc(['bl','gl','pre','prej','san'])

    def payslip_report(self):
        self.ensure_one()
        return self.env.ref('l10n_se_hr_payroll.payslip').report_action(self, data={})

    # @api.model
    # def social_tax_combined(self, code):
    #     self = self.sudo()
    #     lines = self.payslip_id.details_by_salary_rule_category.filtered(lambda p: p.code == code).mapped(lambda a: 
    #     {
    #         '':a.,
    #     })


class ResUsers(models.Model):
    _inherit = "res.users"
    _description = "Res Users"

    def _payslip_nbr(self):
        self = self.sudo()
        self.payslip_nbr = len(self.employee_id.sudo().slip_ids if self.employee_id else 0)

    payslip_nbr = fields.Integer(string="Number Payslips", compute=_payslip_nbr)

    def __init__(self, pool, cr):
        """Override of __init__ to add access rights.
        Access rights are disabled by default, but allowed on some specific
        fields defined in self.SELF_{READ/WRITE}ABLE_FIELDS.
        """
        super().__init__(pool, cr)
        # duplicate list to avoid modifying the original reference
        type(self).SELF_WRITEABLE_FIELDS = list(self.SELF_WRITEABLE_FIELDS)
        type(self).SELF_WRITEABLE_FIELDS.extend(["payslip_nbr"])
        # duplicate list to avoid modifying the original reference
        type(self).SELF_READABLE_FIELDS = list(self.SELF_READABLE_FIELDS)
        type(self).SELF_READABLE_FIELDS.extend(["payslip_nbr"])

    #     class HrPayslipline(models.TransientModel):
    #     _name = "user.payslip.line"
    #     salary_rule_id = fields.Many2one("user.salary.rule", string="Rule", required=True)
    #     code = fields.Char(string="Code")
    #     name = fields.Char(string="Name")
    #     quantity = fields.Char(string="Quantity")
    #     category_id = fields.Many2one("user.salary.rule.category")

    # class HrSaleryRule(models.TransientModel):
    #     _name = "user.salary.rule"
    #     appears_on_payslip = fields.Boolean(string="Appears on Payslip")
    #     salary_art = fields.Many2one(string="Salary art")

    # class HrContract(models.TransientModel):
    #     _name = "user.contract"
    #     wage_tax_base = fields.Float(string="Lönunderlag", digits='Payroll', help="Uträknat löneunderlag för beräkning av preleminär skatt" )
    #     prel_tax_tabel = fields.Char(string="Prel skatt info", help="Ange skattetabell/kolumn/ev jämkning som ligger till grund för angivet preleminärskatteavdrag")
    #     resource_calendar_name = fields.Char(string="Calender Name")
    #     name = fields.Char(string="Name")
    # class HrLeave(models.TransientModel):
    #     _name = "user.leave"
    #     date_from = fields.Datetime()
    #     date_to = fields.Datetime()
    #     number_of_days_temp = fields.Float(string="Number of days")
    #     payslip_id = fields.Many2one(
    #         "user.payslip", string="Pay Slip", required=False, ondelete="cascade", index=True
    #     )
    #     holiday_status_id = fields.Many2one(
    #         "user.holiday.status"
    #     )

    # class HrHolidayStatus(models.TransientModel):
    #     _name = "user.holiday.status"
    #     name = fields.Char(string="name")

    def payslip_action(self):
        self = self.sudo()
        self.env['user.payslip'].search([("employee_id", "=", self.employee_id.id)]).unlink()
        if self.employee_id:
            for slip in self.employee_id.sudo().slip_ids:

                user_payslip = self.env['user.payslip'].create({
                    'name': slip.name,
                    'number': slip.number,
                    'employee_id': self.employee_id.id,
                    'period_id': slip.period_id.id,
                    'payslip_run_id': slip.payslip_run_id.id,
                    'credit_note': slip.credit_note,
                    'paid': slip.paid,
                    'state': slip.state,
                    'payslip_id': slip.id,
                })

                # ~ # hr_contract_id = self.env['hr.contract'].create({
                # ~ #     'column_number':slip.column_number,
                # ~ #     'table_number':slip.table_number
                # ~ # })
                # ~ # user_payslip.write({"hr_contract_ids":[(4,hr_contract_id,0)]})

                holiday_ids_ids = []
                for holiday_id in slip.holiday_ids:
                    holiday_status_id = self.env['user.holiday.status'].create(
                        {'name': holiday_id.holiday_status_id.name})
                    holiday_day_id = self.env['user.leave'].create(
                        {'holiday_status_id': holiday_status_id.id, 'date_from': holiday_id.date_from,
                         'date_to': holiday_id.date_to, 'number_of_days_temp': holiday_id.number_of_days_display})
                    holiday_ids_ids.append(holiday_day_id.id)
                user_payslip.write({"holiday_ids": [(6, 0, holiday_ids_ids)]})

                for worked_day in slip.worked_days_line_ids:
                    worked_day_id = self.env['user.payslip.worked_days'].create(
                        {'code': worked_day.code, 'number_of_hours': worked_day.number_of_hours})
                    user_payslip.write({"worked_days_line_ids": (4, worked_day_id.id, 0)})

                if slip.contract_id:
                    user_contract = self.env["user.contract"].create({
                        "wage_tax_base": slip.contract_id.wage_tax_base,
                        "prel_tax_tabel": slip.contract_id.prel_tax_tabel,
                        'column_number': slip.contract_id.column_number,
                        'table_number': slip.contract_id.table_number,
                        # "resource_calendar_id":slip.contract_id.resource_calendar_id.name,
                        "name": slip.contract_id.resource_calendar_id.name,
                        # "employee_fund_balance":slip.contract_id.employee_fund_balance,
                    })
                    if slip.contract_id.resource_calendar_id:
                        user_calendar = self.env['user.calendar'].create(
                            {'name': slip.contract_id.resource_calendar_id.name})
                        user_contract.resource_calendar_id = user_calendar.id

                    user_payslip.contract_id = user_contract

                for line in slip.line_ids.filtered(lambda l: l.appears_on_payslip == True):
                    # Create user line
                    # ~ salary_category = self.env["user.salary.rule.category"].create({
                        # ~ 'code': line.category_id.code if line.category_id else False
                    # ~ })
                    # ~ salary_rule_id = self.env['user.salary.rule'].create({
                        # ~ 'appears_on_payslip': line.appears_on_payslip,
                        # ~ 'salary_art': line.salary_rule_id.salary_art if line.salary_rule_id else False})
                    user_line = self.env["user.payslip.line"].create({
                        'code': line.code,
                        'name': line.name,
                        'quantity': line.quantity,
                         # ~ 'category_id': salary_category.id,
                         # ~ 'salary_rule_id': salary_rule_id.id,
                         'category': line.category_id.name,
                         'rate': line.rate,
                         'amount': line.amount,
                         'total': line.total,
                         'sequence': line.sequence,
                    })
                    user_payslip.write({"line_ids": [(4, user_line.id, 0)]})



        else:
            raise UserError(_("There is no employee connected to this user."))
        # ~ formview_ref = self.env.ref("payroll.hr_payslip_view_form", False)
        treeview_ref = self.env.ref("l10n_se_hr_payroll.user_payslip_view_tree", False)
        return {
            "name": _("Payslips"),
            "view_mode": "tree, form",
            "view_id": False,
            "res_model": "user.payslip",
            "type": "ir.actions.act_window",
            "target": "current",
            "domain": [("employee_id", "=", self.employee_id.id)],
            "views": [
                (treeview_ref and treeview_ref.id or False, "tree"),
                # ~ (formview_ref and formview_ref.id or False, "form"),
            ],
            "context": {},
        }
