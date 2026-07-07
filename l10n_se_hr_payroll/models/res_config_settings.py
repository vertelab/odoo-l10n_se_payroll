from odoo import fields, models, _

import logging

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

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
