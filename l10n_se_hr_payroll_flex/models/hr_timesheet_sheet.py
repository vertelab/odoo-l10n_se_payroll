# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class HrTimesheetSheet(models.Model):
    _inherit = 'hr_timesheet.sheet'

    overtime_hours = fields.Float(
        string='Övertid (timmar)',
        compute='_compute_flex_diff',
        store=True,
        help='Rapporterad tid utöver schemalagd arbetstid.',
    )
    undertime_hours = fields.Float(
        string='Undertid (timmar)',
        compute='_compute_flex_diff',
        store=True,
        help='Rapporterad tid under schemalagd arbetstid.',
    )
    expected_hours = fields.Float(
        string='Förväntad tid (timmar)',
        compute='_compute_flex_diff',
        store=True,
        help='Schemalagd arbetstid för perioden.',
    )
    is_overtime_ordered = fields.Boolean(
        string='Beordrad övertid',
        help='Markera om övertiden är beordrad av arbetsgivaren.',
    )
    flex_bank_line_ids = fields.One2many(
        'hr.flex.bank.line',
        'source_sheet_id',
        string='Flextidstransaktioner',
        readonly=True,
    )

    @api.depends(
        'date_start', 'date_end', 'employee_id',
        'timesheet_ids.unit_amount',
    )
    def _compute_flex_diff(self):
        """Beräkna övertid/undertid mot schema."""
        for sheet in self:
            if not sheet.employee_id or not sheet.date_start or not sheet.date_end:
                sheet.overtime_hours = 0.0
                sheet.undertime_hours = 0.0
                sheet.expected_hours = 0.0
                continue

            # Rapporterad tid (exklusive frånvaro?)
            reported = sum(sheet.timesheet_ids.mapped('unit_amount'))

            # Förväntad tid från kalender
            calendar = sheet.employee_id.resource_calendar_id
            expected = 0.0
            if calendar:
                try:
                    from datetime import datetime, time
                    from pytz import timezone as tz

                    emp_tz = tz(sheet.employee_id.tz or 'Europe/Stockholm')
                    start_dt = emp_tz.localize(datetime.combine(
                        sheet.date_start, time.min))
                    end_dt = emp_tz.localize(datetime.combine(
                        sheet.date_end, time.max))

                    intervals = calendar._attendance_intervals_batch(
                        start_dt.astimezone(tz('UTC')).replace(tzinfo=None),
                        end_dt.astimezone(tz('UTC')).replace(tzinfo=None),
                    )
                    # _attendance_intervals_batch returns {resource_id: Intervals}
                    for rid, interval_set in intervals.items():
                        expected += sum(
                            (stop - start).total_seconds() / 3600.0
                            for start, stop, att in interval_set
                        )
                except Exception as e:
                    _logger.warning(
                        'Kunde inte beräkna förväntad tid för sheet %s: %s',
                        sheet.id, e)
                    # Fallback: 8h/dag × arbetsdagar
                    from datetime import timedelta
                    days = (sheet.date_end - sheet.date_start).days + 1
                    # Räkna bara vardagar (mån-fre)
                    workdays = sum(
                        1 for i in range(days)
                        if (sheet.date_start + timedelta(days=i)).weekday() < 5
                    )
                    expected = workdays * 8.0

            diff = reported - expected
            sheet.expected_hours = expected
            sheet.overtime_hours = max(0.0, diff)
            sheet.undertime_hours = max(0.0, -diff)

    def action_timesheet_done(self):
        """Vid godkännande: skapa flextidstransaktioner."""
        res = super().action_timesheet_done()
        for sheet in self:
            if sheet.overtime_hours > 0 or sheet.undertime_hours > 0:
                sheet._create_flex_transactions()
        return res

    def _create_flex_transactions(self):
        """Skapa flexbank-transaktioner från övertid/undertid."""
        self.ensure_one()
        bank = self.env['hr.flex.bank']._get_active_bank(self.employee_id)

        contract = self.employee_id.contract_id

        if self.overtime_hours > 0:
            if self.is_overtime_ordered:
                rate = (
                    contract.flex_ordered_overtime_rate
                    if contract else bank.ordered_overtime_rate
                )
                bank.add_hours(
                    hours=self.overtime_hours * rate,
                    transaction_type='ordered_overtime',
                    rate_factor=rate,
                    source_sheet_id=self.id,
                    note='Beordrad övertid från tidrapport vecka %s' % self.name,
                )
            else:
                rate = (
                    contract.flex_overtime_rate
                    if contract else bank.overtime_rate
                )
                bank.add_hours(
                    hours=self.overtime_hours * rate,
                    transaction_type='overtime',
                    rate_factor=rate,
                    source_sheet_id=self.id,
                    note='Övertid från tidrapport vecka %s' % self.name,
                )

        if self.undertime_hours > 0:
            bank.deduct_hours(
                hours=self.undertime_hours,
                transaction_type='undertime',
                source_sheet_id=self.id,
                note='Undertid från tidrapport vecka %s' % self.name,
            )
