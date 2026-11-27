# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    flex_enabled = fields.Boolean(
        string='Aktivera flextid',
        config_parameter='l10n_se_hr_payroll_flex.flex_enabled',
        default=False,
        help='Aktivera flextidsbank för anställda.',
    )
