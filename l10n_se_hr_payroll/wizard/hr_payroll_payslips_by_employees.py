from odoo import _, fields, models
from odoo.exceptions import UserError


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
