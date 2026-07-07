# -*- coding: utf-8 -*-
import datetime
from odoo import fields, models, api, _

import logging

_logger = logging.getLogger(__name__)


class HrPayslip(models.Model):
    """Extend payslip to calculate Loss of Pay (LOP) based on
    leave taken adjacent to Swedish public holidays."""
    _inherit = 'hr.payslip'

    lop_amount = fields.Float(
        string='LOP Amount',
        default=0.0,
        help="Total Loss of Pay deduction for this payslip period.")

    def _get_all_off_days(self):
        """Return a set of all non-working dates (weekly off + public holidays)
        within a window around the payslip period."""
        off_days = set()
        if not self.date_from or not self.date_to:
            return off_days

        calendar = self.employee_id.resource_calendar_id
        working_weekdays = set()
        if calendar:
            for att in calendar.attendance_ids:
                working_weekdays.add(int(att.dayofweek))

        # Collect weekly off days (with buffer for adjacent checks)
        start = self.date_from - datetime.timedelta(days=14)
        end = self.date_to + datetime.timedelta(days=14)
        current = start
        while current <= end:
            if current.weekday() not in working_weekdays:
                off_days.add(current)
            current += datetime.timedelta(days=1)

        # Add public holidays
        public_holidays = self.env['resource.calendar.leaves'].search([
            ('resource_id', '=', False),
        ])
        for holiday in public_holidays:
            h_start = holiday.date_from.date() if hasattr(
                holiday.date_from, 'date') else holiday.date_from
            h_end = holiday.date_to.date() if hasattr(
                holiday.date_to, 'date') else holiday.date_to
            current = h_start
            while current <= h_end:
                off_days.add(current)
                current += datetime.timedelta(days=1)

        return off_days

    def compute_sheet(self):
        """Calculate LOP before computing the payslip."""
        for slip in self:
            slip._calculate_lop()
        return super().compute_sheet()

    def _calculate_lop(self):
        """Calculate Loss of Pay for this payslip based on approved leaves
        adjacent to public holidays/weekends."""
        self.ensure_one()

        if not self.contract_id or not self.employee_id:
            self.sudo().write({'lop_amount': 0.0})
            return

        # Daily wage: monthly / 30 (Swedish standard for LOP)
        daily_wage = self.contract_id.wage / 30.0

        off_days = self._get_all_off_days()

        # Find approved leaves overlapping the payslip period
        leaves = self.env['hr.leave'].search([
            ('employee_id', '=', self.employee_id.id),
            ('state', '=', 'validate'),
            ('request_date_from', '<=', self.date_to),
            ('request_date_to', '>=', self.date_from),
        ])

        total_lop = 0.0

        for leave in leaves:
            leave_start = leave.request_date_from
            leave_end = leave.request_date_to

            # Count consecutive off-days before the leave
            days_before = 0
            check = leave_start - datetime.timedelta(days=1)
            while check.date() in off_days:
                days_before += 1
                check -= datetime.timedelta(days=1)

            # Count consecutive off-days after the leave
            days_after = 0
            check = leave_end + datetime.timedelta(days=1)
            while check.date() in off_days:
                days_after += 1
                check += datetime.timedelta(days=1)

            # Determine leave type
            has_before = days_before > 0
            has_after = days_after > 0

            if has_before and has_after:
                leave_type = 'between_holidays'
            elif has_after and not has_before:
                leave_type = 'before_holiday'
            elif has_before and not has_after:
                leave_type = 'after_holiday'
            else:
                continue

            # Find matching LOP rule
            domain = [('active', '=', True)]
            if leave_type == 'between_holidays':
                domain += [
                    ('leave_type', '=', leave_type),
                    ('no_of_days_before', '<=', days_before),
                    ('no_of_days_after', '<=', days_after),
                ]
                rule = self.env['hr.leave.lop'].search(
                    domain, limit=1,
                    order='no_of_days_before desc, no_of_days_after desc')
            else:
                rule_days = days_before if leave_type == 'after_holiday' else days_after
                domain += [
                    ('leave_type', '=', leave_type),
                    ('no_of_days', '<=', rule_days),
                ]
                rule = self.env['hr.leave.lop'].search(
                    domain, limit=1, order='no_of_days desc')

            if rule:
                # LOP is applied per leave day (klämdag)
                leave_days = (leave_end - leave_start).days + 1
                lop_amount = daily_wage * leave_days * (rule.deduction_amount / 100.0)
                total_lop += lop_amount
                _logger.debug(
                    "LOP: employee=%s, leave=%s, type=%s, "
                    "days_before=%d, days_after=%d, "
                    "rule=%s, deduction=%s%%, lop_amount=%.2f",
                    self.employee_id.name, leave.name, leave_type,
                    days_before, days_after,
                    rule.name, rule.deduction_amount, lop_amount,
                )

        self.sudo().write({'lop_amount': total_lop})

        if total_lop > 0:
            _logger.info(
                "LOP calculated for %s (%s): %.2f SEK",
                self.employee_id.name, self.name, total_lop,
            )
