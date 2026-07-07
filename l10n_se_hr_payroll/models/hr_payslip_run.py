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

    gl_amount = fields.Monetary(string="Grundlön", currency_field='currency_id')
    bl_amount = fields.Monetary(string="Bruttolön", currency_field='currency_id')
    nl_amount = fields.Monetary(string="Nettolön", currency_field='currency_id')
    total_skatt_amount = fields.Monetary(string="Skatt", currency_field='currency_id')
    sa_amount = fields.Monetary(string="Arbetsgivaravgift", currency_field='currency_id')
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

    def _cron_generate_payslips(self):
        """Cron method: automatically generate payslip batches and payslips
        for active employees if enabled and the configured day matches today."""
        config = self.env['ir.config_parameter'].sudo()
        enabled = config.get_param('l10n_se_hr_payroll.automatic_payroll_enabled', default='False')
        if enabled != 'True':
            _logger.debug("Automatic payroll is disabled.")
            return

        today = fields.Date.today()
        config_day = int(config.get_param('l10n_se_hr_payroll.automatic_payroll_day', default='25'))
        if today.day != config_day:
            _logger.debug("Today (%s) is not the configured payroll day (%s).", today.day, config_day)
            return

        # Get current accounting period
        Period = self.env['account.period']
        current_period = Period.date2period(today)
        if not current_period:
            _logger.warning("No accounting period found for today (%s).", today)
            return

        # Find employees with active contracts
        active_contracts = self.env['hr.contract'].search([('state', '=', 'open')])
        employee_ids = active_contracts.mapped('employee_id').filtered('active')
        if not employee_ids:
            _logger.info("No active employees with open contracts found.")
            return

        # Create payslip run
        PayslipRun = self.env['hr.payslip.run']
        run = PayslipRun.create({
            'name': _("Salary batch for %s") % current_period.name,
            'period_id': current_period.id,
        })
        _logger.info("Created automatic payslip run: %s (id=%s)", run.name, run.id)

        # Generate payslips for each employee
        payslips = self.env['hr.payslip']
        for employee in employee_ids:
            contract = employee.contract_id
            slip_vals = self.env['hr.payslip'].get_payslip_vals(
                date_from=current_period.date_start,
                date_to=current_period.date_stop,
                employee_id=employee.id,
                contract_id=contract.id,
            )
            if not slip_vals['value'].get('struct_id'):
                _logger.warning(
                    "Skipping employee %s (id=%s): no salary structure found.",
                    employee.name, employee.id,
                )
                continue
            slip_data = {
                'employee_id': employee.id,
                'name': slip_vals['value'].get('name', _("Salary Slip")),
                'struct_id': slip_vals['value']['struct_id'],
                'contract_id': slip_vals['value'].get('contract_id', contract.id),
                'payslip_run_id': run.id,
                'input_line_ids': [(0, 0, x) for x in slip_vals['value'].get('input_line_ids', [])],
                'worked_days_line_ids': [
                    (0, 0, x) for x in slip_vals['value'].get('worked_days_line_ids', [])
                ],
                'date_from': current_period.date_start,
                'date_to': current_period.date_stop,
                'company_id': employee.company_id.id,
            }
            payslips += self.env['hr.payslip'].create(slip_data)

        _logger.info("Generated %d payslips for run %s.", len(payslips), run.name)

        # Compute all payslips
        payslips.compute_sheet()
        _logger.info("Computed %d payslips. Run %s is ready.", len(payslips), run.name)