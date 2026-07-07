# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

import logging

_logger = logging.getLogger(__name__)


class BonusReason(models.Model):
    """Configurable reasons for bonus requests."""
    _name = 'bonus.reason'
    _description = 'Bonus Reason'
    _order = 'name'

    name = fields.Char(string='Reason', required=True, translate=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company)
