# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrContract(models.Model):
    _inherit = 'hr.contract'

    flex_overtime_rate = fields.Float(
        string='Övertidsfaktor (flextid)',
        default=1.0,
        help='Standardmultiplikator för övertid (1.0 = timme för timme).',
    )

    flex_ordered_overtime_rate = fields.Float(
        string='Beordrad övertidsfaktor',
        default=1.5,
        help='Multiplikator för beordrad övertid (t.ex. 1.5 = +50%%).',
    )
