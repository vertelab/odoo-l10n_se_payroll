# -*- coding: utf-8 -*-
import pytz
from datetime import datetime, timedelta
from odoo import fields, models, api

import logging

_logger = logging.getLogger(__name__)


class HrAttendance(models.Model):
    """Extend hr.attendance to calculate late check-in minutes."""
    _inherit = 'hr.attendance'

    late_check_in = fields.Integer(
        string="Late Check-in (Minutes)",
        compute="_compute_late_check_in",
        store=True,
        help="Duration of employee's tardiness for this attendance record")

    @api.depends('check_in', 'employee_id', 'employee_id.contract_id.resource_calendar_id')
    def _compute_late_check_in(self):
        """Calculate late check-in minutes based on the employee's contract
        schedule. Compares actual check-in time against the scheduled start
        time for the employee's working calendar."""
        for rec in self:
            rec.late_check_in = 0
            if not rec.employee_id or not rec.employee_id.contract_id:
                continue
            contract = rec.employee_id.contract_id
            if not contract.resource_calendar_id:
                continue
            for schedule in contract.resource_calendar_id.attendance_ids:
                if (schedule.dayofweek == str(rec.check_in.weekday())
                        and schedule.day_period == 'morning'):
                    dt = rec.check_in
                    try:
                        user_tz = self.env.user.tz or self.env.company.resource_calendar_id.tz or 'UTC'
                        if user_tz in pytz.all_timezones:
                            old_tz = pytz.timezone('UTC')
                            new_tz = pytz.timezone(user_tz)
                            dt = old_tz.localize(dt).astimezone(new_tz)
                    except Exception:
                        dt = dt.replace(tzinfo=None)

                    str_time = dt.strftime("%H:%M")
                    check_in_time = datetime.strptime(str_time, "%H:%M").time()
                    scheduled_time = timedelta(hours=int(schedule.hour_from),
                                               minutes=int((schedule.hour_from % 1) * 60))
                    start_time = (datetime.min + scheduled_time).time()
                    check_in_delta = timedelta(hours=check_in_time.hour,
                                               minutes=check_in_time.minute)
                    start_delta = timedelta(hours=start_time.hour,
                                            minutes=start_time.minute)
                    if check_in_delta > start_delta:
                        diff = check_in_delta - start_delta
                        rec.late_check_in = int(diff.total_seconds() / 60)

    def _cron_late_check_in_records(self):
        """Cron method: create late.check.in records for employees who were
        late, based on configured thresholds."""
        config = self.env['ir.config_parameter'].sudo()
        enabled = config.get_param('l10n_se_hr_payroll.late_checkin_enabled', default='False')
        if enabled != 'True':
            return

        minutes_after = int(config.get_param(
            'l10n_se_hr_payroll.late_checkin_minutes_after', default='0'))
        max_minutes = int(config.get_param(
            'l10n_se_hr_payroll.late_checkin_max_minutes', default='240'))

        existing_attendance_ids = self.env['late.check.in'].sudo().search(
            []).mapped('attendance_id').ids

        attendances = self.sudo().search([
            ('id', 'not in', existing_attendance_ids),
            ('late_check_in', '>', minutes_after),
            ('late_check_in', '<', max_minutes),
        ])

        for att in attendances:
            self.env['late.check.in'].sudo().create({
                'employee_id': att.employee_id.id,
                'late_minutes': att.late_check_in,
                'date': att.check_in.date(),
                'attendance_id': att.id,
            })

        # Also update existing records for attendances that were already tracked
        existing_records = self.env['late.check.in'].sudo().search([
            ('attendance_id', '!=', False),
            ('state', '=', 'draft'),
        ])
        for record in existing_records:
            attendance = record.attendance_id
            if attendance and attendance.late_check_in != record.late_minutes:
                record.write({
                    'late_minutes': attendance.late_check_in,
                    'date': attendance.check_in.date(),
                })

    def unlink(self):
        """Remove corresponding late.check.in records when attendance is deleted."""
        self.env['late.check.in'].sudo().search(
            [('attendance_id', 'in', self.ids)]).unlink()
        return super().unlink()
