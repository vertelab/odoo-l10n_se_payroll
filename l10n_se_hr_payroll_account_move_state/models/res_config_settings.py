from odoo import fields, models, _

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    slip_state_is_draft = fields.Boolean(string='Account Slip Status',config_parameter='l10n_se_hr_payroll_account_move_state.slip_state_is_draft')
