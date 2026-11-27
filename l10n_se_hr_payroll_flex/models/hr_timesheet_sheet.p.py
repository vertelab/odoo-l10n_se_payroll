# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class HrTimesheetSheet(models.Model):
    _inherit = 'hr_timesheet.sheet'

    overtime_hours = fields.Float(
        string='Övertid (timmar)',
        compute='_compute_flex_diff',
        store=True,
    )
    undertime_hours = fields.Float(
        string='Undertid (timmar)',
        compute='_compute_flex_diff',
        store=True,
    )
    expected_hours = fields.Float(
        string='Förväntad tid (timmar)',
        compute='_compute_flex_diff',
        store=True,
    )
    is_overtime_ordered = fields.Boolean(
        string='Beordrad övertid',
    )
    flex_bank_line_ids = fields.One2many(
        'hr.flex.bank.line',
        'source_sheet_id',
        string='Flextidstransaktioner',
        readonly=True,
    )
    flex_overtime_line_ids = fields.One2many(
        'hr.timesheet.sheet.overtime.line',
        'sheet_id',
        string='Övertidsrader (Flex-flik)',
    )

    # =================================================================
    # Compute: övertid/undertid
    # =================================================================

    @api.depends(
        'date_start', 'date_end', 'employee_id',
        'timesheet_ids.unit_amount',
    )
    def _compute_flex_diff(self):
        """Beräkna övertid/undertid — batchad för listvy-prestanda."""
        sheets = self.filtered(lambda s: s.employee_id and s.date_start and s.date_end)
        (self - sheets).update({
            'overtime_hours': 0.0,
            'undertime_hours': 0.0,
            'expected_hours': 0.0,
        })
        if not sheets:
            return

        # Batcha leave dates — en query för alla
        employees = sheets.mapped('employee_id')
        all_leaves = self.env['hr.leave'].search([
            ('employee_id', 'in', employees.ids),
            ('state', '=', 'validate'),
        ])
        leave_by_employee = {}
        for leave in all_leaves:
            emp_id = leave.employee_id.id
            if emp_id not in leave_by_employee:
                leave_by_employee[emp_id] = set()
            d = leave.date_from.date()
            end = leave.date_to.date()
            while d <= end:
                leave_by_employee[emp_id].add(d)
                d += timedelta(days=1)

        for sheet in sheets:
            reported = sum(sheet.timesheet_ids.mapped('unit_amount'))
            leave_dates = leave_by_employee.get(sheet.employee_id.id, set())
            expected = sheet._compute_expected_hours_fast(leave_dates)
            diff = reported - expected
            sheet.expected_hours = expected
            sheet.overtime_hours = max(0.0, diff)
            sheet.undertime_hours = max(0.0, -diff) if not leave_dates else 0.0

    def _compute_expected_hours_fast(self, leave_dates=None):
        """Snabb beräkning — ren Python från calendar.attendance_ids."""
        self.ensure_one()
        calendar = self.employee_id.resource_calendar_id
        days = (self.date_end - self.date_start).days + 1
        leave_dates = leave_dates or set()

        if not calendar:
            return sum(
                8.0 for i in range(days)
                if (self.date_start + timedelta(days=i)).weekday() < 5
                and (self.date_start + timedelta(days=i)) not in leave_dates
            )

        hours_per_weekday = {}
        for att in calendar.attendance_ids:
            dow = int(att.dayofweek)
            h = att.hour_to - att.hour_from
            hours_per_weekday[dow] = hours_per_weekday.get(dow, 0.0) + h

        return sum(
            hours_per_weekday.get((self.date_start + timedelta(days=i)).weekday(), 0.0)
            for i in range(days)
            if (self.date_start + timedelta(days=i)) not in leave_dates
        )

    def _compute_expected_hours(self, leave_dates=None):
        return self._compute_expected_hours_fast(leave_dates)

    # =================================================================
    # Flex-flik: övertidsrader per projekt
    # =================================================================

    def _refresh_overtime_lines(self):
        """Uppdatera flex_overtime_line_ids."""
        self.ensure_one()
        OvertimeLine = self.env['hr.timesheet.sheet.overtime.line']
        existing = OvertimeLine.search([('sheet_id', '=', self.id)])
        existing.unlink()
        if not self.employee_id:
            return
        leave_dates = self._get_leave_dates()
        expected_per_day = self._get_expected_hours_per_day()
        reported_per_day_project = self._get_reported_hours_per_day_project()
        new_lines = []
        for date in self._get_dates():
            if date in leave_dates:
                continue
            expected = expected_per_day.get(date, 0.0)
            if expected <= 0:
                continue
            day_data = reported_per_day_project.get(date, {})
            total_reported = sum(day_data.values())
            total_ot = max(0, total_reported - expected)
            if total_ot <= 0:
                continue
            for (project_id, task_id), hours in day_data.items():
                ot_for_project = (hours / total_reported) * total_ot if total_reported > 0 else 0
                if ot_for_project > 0:
                    new_lines.append(OvertimeLine.create({
                        'sheet_id': self.id,
                        'date': date,
                        'project_id': project_id,
                        'task_id': task_id,
                        'overtime_hours': round(ot_for_project, 2),
                    }))
        self.flex_overtime_line_ids = [(6, 0, [l.id for l in new_lines])]

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get('_flex_skip_refresh'):
            trigger_fields = {'timesheet_ids', 'line_ids', 'date_start', 'date_end', 'new_line_ids', 'employee_id'}
            if trigger_fields.intersection(vals):
                for sheet in self:
                    if sheet.state in ('new', 'draft') and sheet.employee_id:
                        sheet.with_context(_flex_skip_refresh=True)._refresh_overtime_lines()
        return res

    # =================================================================
    # Godkännande → flextidstransaktioner
    # =================================================================

    def action_timesheet_done(self):
        res = super().action_timesheet_done()
        for sheet in self:
            if sheet.overtime_hours > 0 or sheet.undertime_hours > 0:
                sheet._create_flex_transactions()
        return res

    def _create_flex_transactions(self):
        self.ensure_one()
        bank = self.env['hr.flex.bank']._get_active_bank(self.employee_id)
        contract = self.employee_id.contract_id

        for line in self.flex_overtime_line_ids:
            if line.overtime_hours <= 0:
                continue
            if line.is_ordered:
                rate = (
                    contract.flex_ordered_overtime_rate
                    if contract else bank.ordered_overtime_rate
                )
                bank.add_hours(
                    hours=line.overtime_hours * rate,
                    transaction_type='ordered_overtime',
                    rate_factor=rate,
                    source_sheet_id=self.id,
                    note='Beordrad övertid %s' % line.project_id.name,
                )
            else:
                rate = (
                    contract.flex_overtime_rate
                    if contract else bank.overtime_rate
                )
                bank.add_hours(
                    hours=line.overtime_hours * rate,
                    transaction_type='overtime',
                    rate_factor=rate,
                    source_sheet_id=self.id,
                    note='Övertid %s' % line.project_id.name,
                )

        if self.undertime_hours > 0:
            bank.deduct_hours(
                hours=self.undertime_hours,
                transaction_type='undertime',
                source_sheet_id=self.id,
                note='Undertid',
            )

    # =================================================================
    # Hjälpmetoder
    # =================================================================

    def _get_expected_hours_per_day(self):
        self.ensure_one()
        calendar = self.employee_id.resource_calendar_id
        if not calendar:
            return {}
        hours_per_weekday = {}
        for att in calendar.attendance_ids:
            dow = int(att.dayofweek)
            hours_per_weekday[dow] = hours_per_weekday.get(dow, 0.0) + (
                att.hour_to - att.hour_from
            )
        return {
            d: hours_per_weekday.get(d.weekday(), 0.0)
            for d in self._get_dates()
        }

    def _get_reported_hours_per_day_project(self):
        """Return {date: {(project_id, task_id): hours}}."""
        self.ensure_one()
        result = {}
        for line in self.timesheet_ids:
            date = line.date
            key = (line.project_id.id, line.task_id.id)
            if date not in result:
                result[date] = {}
            result[date][key] = result[date].get(key, 0.0) + line.unit_amount
        return result

    def _get_leave_dates(self):
        self.ensure_one()
        if not self.employee_id:
            return set()
        leaves = self.env['hr.leave'].search([
            ('employee_id', '=', self.employee_id.id),
            ('state', '=', 'validate'),
            ('date_from', '<=', self.date_end),
            ('date_to', '>=', self.date_start),
        ])
        leave_dates = set()
        for leave in leaves:
            d = leave.date_from.date()
            end = leave.date_to.date()
            while d <= end:
                leave_dates.add(d)
                d += timedelta(days=1)
        return leave_dates


class HrTimesheetSheetOvertimeLine(models.TransientModel):
    """En övertidsrad per projekt och dag på tidrapporten (Flex-flik)."""
    _name = 'hr.timesheet.sheet.overtime.line'
    _description = 'Övertidsrad på tidrapport'
    _order = 'date, project_id'

    sheet_id = fields.Many2one(
        'hr_timesheet.sheet',
        string='Tidrapport',
        required=True,
        ondelete='cascade',
    )
    date = fields.Date(string='Datum', required=True)
    project_id = fields.Many2one('project.project', string='Projekt')
    task_id = fields.Many2one('project.task', string='Uppgift')
    overtime_hours = fields.Float(string='Övertidstimmar')
    is_ordered = fields.Boolean(
        string='Beordrad',
        help='Markera för beordrad övertid (bonus till timpotten).',
    )
