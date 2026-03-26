import logging
from odoo import fields, models, api, _
_logger = logging.getLogger(__name__)

class HrPayslipRun(models.Model):
    _inherit = "hr.payslip.run"

    name = fields.Char(
        required=True, readonly=True, states={"draft": [("readonly", False)]}
    )
    period_id = fields.Many2one(
        comodel_name='account.period',
        string="Period",
        readonly=False,
        required=True,
        default=lambda self: self.env['account.period'].date2period(fields.Date.today()),
        states={"draft": [("readonly", False)]},
        tracking=1,
        check_company=True,
    )
    date_start = fields.Date(related="period_id.date_start", store=True)
    date_end = fields.Date(related="period_id.date_end", store=True)

    slip_ids_count = fields.Integer(
        string="Payslips Count",
        compute="_compute_slip_ids_count",
    )

    def _compute_slip_ids_count(self):
        for run in self:
            run.slip_ids_count = len(run.slip_ids)

    @api.onchange('period_id')
    def onchange_name(self):
        _logger.error(f"{self.date_start=}")
        _logger.error(f"{self.date_end=}")
        self.name = _("Salary batch for %s") % (
            self.period_id.date_start.strftime('%B-%Y') if self.period_id else 'None',
        )

    def action_view_payslips(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Payslips"),
            "res_model": "hr.payslip",
            "view_mode": "list,form",
            "domain": [("payslip_run_id", "=", self.id)],
            "context": {"default_payslip_run_id": self.id},
        }

    def action_open_employees_for_payslip(self):
        self.ensure_one()
        view = self.env.ref('l10n_se_hr_payroll.hr_employee_payslip_select_view_list')
        return {
            "type": "ir.actions.act_window",
            "name": _("Select Employees"),
            "res_model": "hr.employee",
            "view_mode": "list",
            "view_id": view.id,
            "target": "current",
            "domain": [("active", "=", True)],
            "context": {
                "active_payslip_run_id": self.id,
                "create": False,
                "edit": False,
                "delete": False,
            },
        }