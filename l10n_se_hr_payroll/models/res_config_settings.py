from odoo import fields, models, _

import logging

_logger = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    choose_date_method = fields.Selection([
        ("date_now", "Date now"),
        ("date_then", "Date then"),],
        store=True, default=False, readonly=False, config_parameter='l10n_se_hr_payroll.choose_date_method')