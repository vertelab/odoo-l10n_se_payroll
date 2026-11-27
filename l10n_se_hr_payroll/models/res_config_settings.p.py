from odoo import fields, models, _

import logging

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # -- Automatic Payroll --
    automatic_payroll_enabled = fields.Boolean(
        string="Automatic Payroll",
        config_parameter="l10n_se_hr_payroll.automatic_payroll_enabled",
        help="Enable automatic generation of payslip batches and payslips "
             "on a scheduled day each month.",
    )
    automatic_payroll_day = fields.Integer(
        string="Generation Day",
        default=25,
        config_parameter="l10n_se_hr_payroll.automatic_payroll_day",
        help="Day of the month when payslips are automatically generated "
             "(1-28 recommended). Default: 25.",
    )

    # -- Late Check-in --
    late_checkin_enabled = fields.Boolean(
        string="Late Check-in",
        config_parameter="l10n_se_hr_payroll.late_checkin_enabled",
        help="Enable late check-in tracking and automatic salary deductions.",
    )
    late_checkin_deduction_amount = fields.Float(
        string="Deduction Amount",
        default=50.0,
        config_parameter="l10n_se_hr_payroll.late_checkin_deduction_amount",
        help="Amount to deduct per minute (or per occurrence) for late check-ins.",
    )
    late_checkin_deduction_type = fields.Selection(
        selection=[('per_minute', 'Per Minute'), ('per_total', 'Per Occurrence')],
        string="Deduction Type",
        default='per_minute',
        config_parameter="l10n_se_hr_payroll.late_checkin_deduction_type",
        help="Per Minute: deduct given amount for each late minute. "
             "Per Occurrence: deduct given amount once per late check-in.",
    )
    late_checkin_minutes_after = fields.Integer(
        string="Starts After (Minutes)",
        default=5,
        config_parameter="l10n_se_hr_payroll.late_checkin_minutes_after",
        help="Grace period in minutes. Late check-ins are only recorded "
             "if the employee is at least this many minutes late.",
    )
    late_checkin_max_minutes = fields.Integer(
        string="Maximum Late Minutes",
        default=240,
        config_parameter="l10n_se_hr_payroll.late_checkin_max_minutes",
        help="Maximum minutes considered as late. Beyond this, the employee "
             "is considered absent rather than late.",
    )
