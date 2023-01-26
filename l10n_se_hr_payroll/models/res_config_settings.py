from odoo import fields, models, _

import logging

_logger = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    choose_date_method = fields.Selection([
        ("date_now", "Date now"),
        ("date_then", "Date then"),],
        store=True, readonly=False, config_parameter='l10n_se_hr_payroll.choose_date_method')
#        store=True, compute = "compute_date_method", readonly=False, config_parameter='l10n_se_hr_payroll.choose_date_method')
    _logger.error(f"{choose_date_method=}")