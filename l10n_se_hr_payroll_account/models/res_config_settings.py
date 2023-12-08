# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    payroll_account_post = fields.Boolean(string="Payroll Account Post",
                                          config_parameter='l10n_se_hr_payroll_account.payroll_account_post')
