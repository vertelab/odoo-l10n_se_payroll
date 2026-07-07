# -*- coding: utf-8 -*-
from odoo import api, fields, models

import logging

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    """Extend employee to add joining_date and anniversary reminder."""
    _inherit = "hr.employee"

    joining_date = fields.Date(
        string='Joining Date',
        compute='_compute_joining_date',
        store=True,
        help="Employee's first contract start date (joining date).")

    @api.depends('contract_ids.date_start')
    def _compute_joining_date(self):
        for rec in self:
            dates = rec.contract_ids.mapped('date_start')
            rec.joining_date = min(dates) if dates else False

    @api.model
    def _cron_work_anniversary_reminder(self):
        """Daily cron: send anniversary greeting emails to employees."""
        today = fields.Date.today()
        for employee in self.search([('joining_date', '!=', False)]):
            if (employee.joining_date.month == today.month
                    and employee.joining_date.day == today.day
                    and employee.work_email):
                template = self.env.ref(
                    'hr_work_anniversary_reminder.email_template_work_anniversary')
                template.send_mail(employee.id, force_send=True)
                _logger.info(
                    "Anniversary: sent greeting to %s (joined %s)",
                    employee.name, employee.joining_date,
                )
