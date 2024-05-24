from odoo import _, fields, models, api
from odoo.exceptions import UserError


class MailActivity(models.Model):
    _inherit = "mail.activity"
    
    @api.onchange("activity_type_id")
    def compute_is_payslip(self):
        for record in self:
            if record.activity_type_id:
                record.is_payslip = record.activity_type_id.is_payslip
            else:
                record.is_payslip = False

    is_payslip = fields.Boolean(compute=compute_is_payslip)
    employee_id = fields.Many2one(comodel_name="hr.employee")

class MailActivityType(models.Model):
    _inherit = "mail.activity.type"
    is_payslip = fields.Boolean()
    #employee_id = fields.Many2one(comodel_name="hr.employee")
    #fields.Many2many(comodel_name='hr.leave', compute='_holiday_ids')

class HrPayslipEmployees(models.TransientModel):
    _inherit = "hr.payslip.employees"

    def compute_sheet(self):
        payslips = self.env["hr.payslip"]
        [data] = self.read()
        active_id = self.env.context.get("active_id")
        journal_id = run = False

        if active_id:
            run = self.env["hr.payslip.run"].browse(active_id)
            journal_id = self.env['hr.payslip.run'].browse(self.env.context.get('active_id')).journal_id.id
        if not data["employee_ids"]:
            raise UserError(_("You must select employee(s) to generate payslip(s)."))
        for employee in self.env["hr.employee"].browse(data["employee_ids"]):
            slip_data = self.env["hr.payslip"].get_payslip_vals_period(run, employee)
            slip_data.update({"journal_id": journal_id})
            payslips += self.env["hr.payslip"].create(slip_data)

        payslips.with_context(journal_id=journal_id).compute_sheet()
        return {"type": "ir.actions.act_window_close"}
