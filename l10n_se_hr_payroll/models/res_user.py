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

class HrSaleryRule(models.TransientModel):
    _name = "user.salary.rule"
    appears_on_payslip = fields.Boolean(string="Appears on Payslip")
    salary_art = fields.Many2one(string="Salary art")

class HrSaleryCategory(models.TransientModel):
    _name = "user.salary.rule.category"
    code = fields.Char(string = "Code")


class HrPayslip(models.TransientModel):
    _name = "user.payslip"

    line_ids = fields.One2many(
        "user.payslip.line"
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

    def payslip_report(self):
        self = self.sudo()
        
        _logger.warning("1"*100)
        # ~ data = self.read(cr, uid, ids)[0]
        payslip = self
        # ~ action = self.env.ref('l10n_se_hr_payroll.payslip').report_action(docids=payslip, data={}, config=False)
        report_name = "l10n_se_hr_payroll.payslip"
        # ~ pdf = self.env['user.payslip'].sudo().get_pdf(payslip, report_name)
        _logger.warning("2"*100)

        # ~ lines = self.with_context(print_mode=True).get_pdf_lines(line_data)
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        rcontext = {
            'mode': 'print',
            'base_url': base_url,
        }
        _logger.warning("3"*100)
        view_id = self.env['ir.ui.view'].sudo().get_view_id("l10n_se_hr_payroll.payslip")
        view_obj = self.env['ir.ui.view'].sudo().browse(view_id)
        # ~ raise Warning(view_obj._render({},'ir.qweb'))


        # ~ body = self.env['ir.ui.view']._render_template(
            # ~ "l10n_se_hr_payroll.payslip",{}
            # ~ values=dict(rcontext, lines=payslip, report=self, context=self),
        # ~ )
        _logger.warning("4"*100)
        header = self.env['ir.actions.report']._render_template("web.internal_layout", values=rcontext)
        header = self.env['ir.actions.report']._render_template("web.minimal_layout", values=dict(rcontext, subst=True, body=header))

        body = self.env['ir.actions.report']._render_template("l10n_se_hr_payroll.payslip_2_report", values=dict(datas=payslip))


        pdf  = self.env['ir.actions.report']._run_wkhtmltopdf(
            [body],
            header=header,
            landscape=False,
            specific_paperformat_args={'data-report-margin-top': 10, 'data-report-header-spacing': 10}
        )
        _logger.warning("5"*100)
        file = base64.b64encode(pdf)

        data = {
       # ~ 'from_date': self.from_date,
       # ~ 'to_date': self.to_date
        }
       # docids = self.env['sale.order'].search([]).ids
        _logger.warning("6"*100)
        return self.env.ref('l10n_se_hr_payroll.payslip').report_action(payslip, data={})
        _logger.warning("7"*100)


        return file
        # ~ datas = {
             # ~ 'ids': context.get('active_ids',[]),
             # ~ 'model': 'account.analytic.account',
             # ~ 'form': data
                 # ~ }
        # ~ return {
            # ~ 'type': 'ir.actions.report.xml',
            # ~ 'report_name': 'account.analytic.account.balance',
            # ~ 'datas': datas,
            # ~ }



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

    def payslip_action(self):
        self = self.sudo()
        _logger.warning("1"*100)
        self.env['user.payslip'].search([]).unlink()
        _logger.warning("2"*100)
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
                for line in slip.line_ids:
                    _logger.warning(f"{line=}")
                    #Create user line
                    salery_category = self.env['user.salary.rule.category'].create({
                        'code': line.category_id.code if line.category_id else False
                    })
                    salary_rule_id = self.env['user.salary.rule'].create({
                        'appears_on_payslip': line.appears_on_payslip,
                        'salary_art': line.salary_rule_id.salary_art if line.salary_rule_id else False})
                    user_line = self.env["user.payslip.line"].create(
                        {'code':line.code,
                        'name':line.name,
                        'quantity':line.quantity,
                        'category_id':salery_category,
                        'salary_rule_id': salary_rule_id
                        })
                    user_payslip.write({(4,user_line.id,0)})
                    

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
            # ~ "domain": "[('id', 'in', %s)]" % copied_payslip.ids,
            "views": [
                (treeview_ref and treeview_ref.id or False, "tree"),
                # ~ (formview_ref and formview_ref.id or False, "form"),
            ],
            "context": {},
        }





