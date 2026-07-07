# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

import logging

_logger = logging.getLogger(__name__)


class HrLeaveLOP(models.Model):
    """Configuration rules for Loss of Pay (LOP) deductions.
    LOP applies when an employee takes leave adjacent to public holidays
    ('klämdagar' in Swedish context)."""
    _name = "hr.leave.lop"
    _description = "Time Off LOP Rule"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'leave_type, no_of_days'

    name = fields.Char(
        string="Name",
        required=True,
        help="Descriptive name for this LOP rule.")
    leave_type = fields.Selection(
        selection=[
            ('before_holiday', 'Day Before Holiday'),
            ('after_holiday', 'Day After Holiday'),
            ('between_holidays', 'Between Holidays'),
        ],
        string="Leave Type",
        required=True,
        help="When does this LOP rule apply?\n"
             "- Day Before Holiday: leave taken the day before a public holiday\n"
             "- Day After Holiday: leave taken the day after a public holiday\n"
             "- Between Holidays: leave taken between two public holidays")
    deduction_amount = fields.Float(
        string='Deduction (%)',
        default=100.0,
        required=True,
        help="Percentage of daily wage to deduct when this LOP rule applies.")
    no_of_days = fields.Integer(
        string='Minimum Consecutive Holidays',
        default=1,
        help="Minimum number of consecutive off-days needed to trigger this "
             "rule. Used for 'Before Holiday' and 'After Holiday' types. "
             "Example: 1 means a single holiday triggers the rule.")
    no_of_days_before = fields.Integer(
        string='Minimum Holidays Before',
        default=1,
        help="Minimum consecutive off-days required BEFORE the leave. "
             "Used only for 'Between Holidays' type.")
    no_of_days_after = fields.Integer(
        string='Minimum Holidays After',
        default=1,
        help="Minimum consecutive off-days required AFTER the leave. "
             "Used only for 'Between Holidays' type.")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company)

    @api.constrains('no_of_days', 'no_of_days_before', 'no_of_days_after', 'leave_type')
    def _check_holiday_counts(self):
        for record in self:
            if record.leave_type == 'between_holidays':
                if record.no_of_days_before < 1 or record.no_of_days_after < 1:
                    raise ValidationError(_(
                        "Both 'Before' and 'After' holiday counts must be at "
                        "least 1 for 'Between Holidays' rules."))
            else:
                if record.no_of_days < 1:
                    raise ValidationError(_(
                        "Minimum consecutive holidays must be at least 1."))

    def copy(self, default=None):
        raise ValidationError(_("Cannot duplicate a Time Off LOP rule!"))
