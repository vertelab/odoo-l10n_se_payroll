# -*- coding: utf-8 -*-
from odoo import fields, models


class HrJob(models.Model):
    _inherit = 'hr.job'

    nyk_id = fields.Many2one(
        'hr.nyk',
        string='NYK-kod',
        help='Swedish Occupational Classification Code (NYK)'
    )
