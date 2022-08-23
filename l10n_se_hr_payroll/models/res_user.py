# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from odoo import fields, models, api, _

from odoo.exceptions import UserError, ValidationError, RedirectWarning, Warning
import logging
_logger = logging.getLogger(__name__)


# class HrPayslipLine(models.Model):
#     _name = "hr.payslip.line"
#     _inherit = "hr.salary.rule"
#     _description = "Payslip Line"
#     _order = "contract_id, sequence"

#     slip_id = fields.Many2one(
#         "hr.payslip", string="Pay Slip", required=True, ondelete="cascade"
#     )
#     salary_rule_id = fields.Many2one("hr.salary.rule", string="Rule", required=True)
#     employee_id = fields.Many2one("hr.employee", string="Employee", required=True)
#     contract_id = fields.Many2one(
#         "hr.contract", string="Contract", required=True, index=True
#     )
#     rate = fields.Float(string="Rate (%)", digits="Payroll Rate", default=100.0)
#     amount = fields.Float(digits="Payroll")
#     quantity = fields.Float(digits="Payroll", default=1.0)
#     total = fields.Float(
#         compute="_compute_total",
#         string="Total",
#         digits="Payroll",
#         store=True,
#     )

#     @api.depends("quantity", "amount", "rate")
#     def _compute_total(self):
#         for line in self:
#             line.total = float(line.quantity) * line.amount * line.rate / 100

#     @api.model_create_multi
#     def create(self, vals_list):
#         for values in vals_list:
#             if "employee_id" not in values or "contract_id" not in values:
#                 payslip = self.env["hr.payslip"].browse(values.get("slip_id"))
#                 values["employee_id"] = (
#                     values.get("employee_id") or payslip.employee_id.id
#                 )
#                 values["contract_id"] = (
#                     values.get("contract_id")
#                     or payslip.contract_id
#                     and payslip.contract_id.id
#                 )
#                 if not values["contract_id"]:
#                     raise UserError(
#                         _("You must set a contract to create a payslip line.")
#                     )
#         return super(HrPayslipLine, self).create(vals_list)
class HrPayslipline(models.TransientModel):
    _name = "user.payslip.line"
    salary_rule_id = fields.Many2one("user.salary.rule", string="Rule", required=True)
    code = fields.Char(string="Code")
    name = fields.Char(string="Name")
    quantity = fields.Char(string="Quantity")
    category_id = fields.Many2one("user.salary.rule.category")
    user_payslip_id = fields.Many2one(
        "user.payslip"
    )
    user_payslip_line_original_id = fields.Many2one(
        "hr.payslip.line",
    )

class HrSaleryRule(models.TransientModel):
    _name = "user.salary.rule"
    appears_on_payslip = fields.Boolean(string="Appears on Payslip")
    salary_art = fields.Many2one(string="Salary art")

class HrSaleryCategory(models.TransientModel):
    _name = "user.salary.rule.category"
    code = fields.Char(string = "Code")

class HrContract(models.TransientModel):
    _name = "user.contract"
    wage_tax_base = fields.Float(string="Lönunderlag", digits='Payroll', help="Uträknat löneunderlag för beräkning av preleminär skatt" )
    prel_tax_tabel = fields.Char(string="Prel skatt info", help="Ange skattetabell/kolumn/ev jämkning som ligger till grund för angivet preleminärskatteavdrag")
    resource_calendar_id = fields.Many2one("user.calendar")
    name = fields.Char(string="Name")

class HrCalender(models.TransientModel):
    _name = "user.calendar"
    name = fields.Char(string="Name")

class HrWorkdays(models.TransientModel):
    _name = "user.workdays"
    name = fields.Char(string="Name")
    code = fields.Char(string="code")
    number_of_hours = fields.Float(string="Number of hours")
    
class HrPayslip(models.TransientModel):
    _name = "user.payslip"

    line_ids = fields.One2many(
        "user.payslip.line",inverse_name='user_payslip_id'
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
        readonly=True,)

    payslip_id = fields.Many2one(comodel_name='hr.payslip')
    @api.model
    def get_slip_line(self, code):
        lines = self.payslip_id.details_by_salary_rule_category.filtered(lambda l: l.code == code).mapped(lambda v: {'name': v.name, 'quantity': v.quantity, 'rate': v.rate, 'amount': v.amount, 'total': v.total})
        return lines

    @api.model
    def get_slip_line_total(self, code):
        return self.payslip_id.get_slip_line_total(code)

    @api.model
    def get_slip_line_acc(self, code):
        return self.payslip_id.get_slip_line_acc(code)

    def payslip_report(self):

        return self.env.ref('l10n_se_hr_payroll.payslip').report_action(docids=[self.id],data={})



class ResUsers(models.Model):
    _inherit = "res.users"

    def _payslip_nbr(self):
        self = self.sudo()
        self.payslip_nbr = len(self.employee_id.sudo().slip_ids if self.employee_id else 0)

    payslip_nbr = fields.Integer(string="Number Payslips",compute=_payslip_nbr)



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

    def payslip_action(self):
        self = self.sudo()
        _logger.warning("1"*100)
        self.env['user.payslip'].search([("employee_id","=",self.employee_id.id)]).unlink()
        _logger.warning("2"*100)
        if self.employee_id:
            for slip in self.employee_id.sudo().slip_ids:
                _logger.warning("Hello"*100)
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
                if slip.contract_id:
                   user_contract = self.env["user.contract"].create({
                    "wage_tax_base":slip.contract_id.wage_tax_base,
                    "prel_tax_tabel":slip.contract_id.prel_tax_tabel,
                    # "resource_calendar_id":slip.contract_id.resource_calendar_id.name,
                    "name":slip.contract_id.resource_calendar_id.name,
                   })
                   if slip.contract_id.resource_calendar_id:
                        user_calendar = self.env['user.calendar'].create({'name':slip.contract_id.resource_calendar_id.name})
                        user_contract.resource_calendar_id = user_calendar.id

                   user_payslip.contract_id = user_contract

                for line in slip.line_ids:
                    _logger.warning(f"{line=}")
                    #Create user line
                    salary_category = self.env["user.salary.rule.category"].create({
                        'code': line.category_id.code if line.category_id else False
                    })
                    salary_rule_id = self.env['user.salary.rule'].create({
                        'appears_on_payslip': line.appears_on_payslip,
                        'salary_art': line.salary_rule_id.salary_art if line.salary_rule_id else False})
                    user_line = self.env["user.payslip.line"].create(
                        {'code':line.code,
                        'name':line.name,
                        'quantity':line.quantity,
                        'category_id':salary_category,
                        'salary_rule_id': salary_rule_id
                        })
                    user_payslip.write({"line_ids":(4,user_line.id,0)})
                _logger.warning("LOOK HERE"*100)
                _logger.warning(user_payslip.line_ids)


        else:
            raise UserError(_("There is no employee connected to this user."))
        _logger.warning("3"*100)
        # ~ formview_ref = self.env.ref("payroll.hr_payslip_view_form", False)
        treeview_ref = self.env.ref("l10n_se_hr_payroll.user_payslip_view_tree", False)
        return {
            "name": _("Payslips"),
            "view_mode": "tree, form",
            "view_id": False,
            "res_model": "user.payslip",
            "type": "ir.actions.act_window",
            "target": "current",
            "domain": [("employee_id","=",self.employee_id.id)],
            "views": [
                (treeview_ref and treeview_ref.id or False, "tree"),
                # ~ (formview_ref and formview_ref.id or False, "form"),
            ],
            "context": {},
        }





