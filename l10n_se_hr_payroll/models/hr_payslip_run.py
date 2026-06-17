import logging
from odoo import fields, models, api, _

_logger = logging.getLogger(__name__)

class HrPayslipRun(models.Model):
    _inherit = "hr.payslip.run"
    _mail_post_access = "read"

    name = fields.Char(
        required=True, readonly=True, states={"draft": [("readonly", False)]}
    )
    period_id = fields.Many2one(
        comodel_name='account.period',
        string="Salary period",
        help="Selected payroll month. Deviations are fetched from previous period.",
        readonly=False,
        required=True,
        default=lambda self: self.env['account.period'].date2period(fields.Date.today()),
        states={"draft": [("readonly", False)]},
        tracking=1,
        check_company=True,
    )
    date_start = fields.Date(related="period_id.date_start", store=True)
    date_end = fields.Date(related="period_id.date_stop", store=True)

    slip_ids_count = fields.Integer(
        string="Payslips Count",
        compute="_compute_slip_ids_count",
    )

    gl_amount = fields.Monetary(string="Grundlön")
    bl_amount = fields.Monetary(string="Bruttolön")
    nl_amount = fields.Monetary(string="Nettolön")
    total_skatt_amount = fields.Monetary(string="Skatt")
    sa_amount = fields.Monetary(string="Arbetsgivaravgift")
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id")

    def _compute_slip_ids_count(self):
        for run in self:
            run.slip_ids_count = len(run.slip_ids)

    def _compute_amounts(self):
        salary_rule_codes = {"gl": "gl_amount", "bl": "bl_amount", "nl": "nl_amount",
                             "total_skatt": "total_skatt_amount", "sa": "sa_amount"}
        for run in self:
            amounts = {key: 0.0 for key in salary_rule_codes.values()}
            for slip in run.slip_ids.filtered(lambda s: s.state in ('done', 'paid')):
                for line in slip.line_ids:
                    code = line.salary_rule_id.code
                    if code in salary_rule_codes:
                        amounts[salary_rule_codes[code]] += abs(line.total)
            for fname, val in amounts.items():
                setattr(run, fname, val)

    def write(self, vals):
        res = super().write(vals)
        if 'slip_ids' in vals or 'state' in vals:
            self._compute_amounts()
        return res

    @api.onchange('period_id')
    def onchange_name(self):
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
            "domain": [("active", "=", True), ('contract_id.state', '=', 'open')],
            "context": {
                "active_payslip_run_id": self.id,
                "create": False,
                "edit": False,
                "delete": False,
            },
        }