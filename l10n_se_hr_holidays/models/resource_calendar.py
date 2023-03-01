# Copyright 2020 Shabeer VPK
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models, fields, _
from odoo.addons.resource.models.resource import Intervals

from pytz import timezone
import datetime
from dateutil import rrule
import pandas as pd

from collections import defaultdict
import math
from datetime import datetime, time, timedelta
from dateutil.relativedelta import relativedelta
from dateutil.rrule import rrule, DAILY, WEEKLY, MONTHLY
from functools import partial
from itertools import chain
from pytz import timezone, utc
from odoo.addons.resource.models.resource import float_round, float_to_time, float_utils
from odoo.osv import expression

# Default hour per day value. The one should
# only be used when the one from the calendar
# is not available.
HOURS_PER_DAY = 8
# This will generate 16th of days
ROUNDING_FACTOR = 16

DAYS_IN_WEEK = [
    ('0', 'Monday'),
    ('1', 'Tuesday'),
    ('2', 'Wednesday'),
    ('3', 'Thursday'),
    ('4', 'Friday'),
    ('5', 'Saturday'),
    ('6', 'Sunday')
]


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    @api.depends('attendance_ids')
    def _get_non_working_hours(self):
        for rec in self:
            formatted_days_of_weeks = {}
            for attendance in rec.attendance_ids:
                if dict(DAYS_IN_WEEK).get(attendance.dayofweek):
                    formatted_days_of_weeks.update(
                        {
                            str(attendance.dayofweek): dict(DAYS_IN_WEEK).get(attendance.dayofweek)
                        })

            absent_work_days = [days for days in DAYS_IN_WEEK if days not in list(formatted_days_of_weeks.items())]

            for absent_days in absent_work_days:
                rec.absent_work_days = [
                    (0, 0, {'name': _(f'{absent_days[-1]} Morning'), 'dayofweek': absent_days[0], 'hour_from': 8,
                            'hour_to': 12, 'day_period': 'morning', 'absent_calendar_id': self.id}),
                    (0, 0, {'name': _(f'{absent_days[-1]} Afternoon'), 'dayofweek': absent_days[0], 'hour_from': 13,
                            'hour_to': 17, 'day_period': 'afternoon', 'absent_calendar_id': self.id}),
                ]

    absent_work_days = fields.One2many('resource.calendar.attendance', 'absent_calendar_id', 'Absent Hours')

    def set_non_work_days(self):
        formatted_days_of_weeks = {}
        for attendance in self.attendance_ids:
            if dict(DAYS_IN_WEEK).get(attendance.dayofweek):
                formatted_days_of_weeks.update(
                    {
                        str(attendance.dayofweek): dict(DAYS_IN_WEEK).get(attendance.dayofweek)
                    })

        absent_work_days = [days for days in DAYS_IN_WEEK if days not in list(formatted_days_of_weeks.items())]

        for absent_days in absent_work_days:
            self.absent_work_days = [
                (0, 0, {'name': _(f'{absent_days[-1]} Morning'), 'dayofweek': absent_days[0], 'hour_from': 8,
                        'hour_to': 12, 'day_period': 'morning', 'absent_calendar_id': self.id}),
                (0, 0, {'name': _(f'{absent_days[-1]} Afternoon'), 'dayofweek': absent_days[0], 'hour_from': 13,
                        'hour_to': 17, 'day_period': 'afternoon', 'absent_calendar_id': self.id}),
            ]

    def _attendance_intervals_batch(self, start_dt, end_dt, resources=None, domain=None, tz=None):
        """ Return the attendance intervals in the given datetime range.
            The returned intervals are expressed in specified tz or in the resource's timezone.
        """
        self.ensure_one()
        resources = self.env['resource.resource'] if not resources else resources
        assert start_dt.tzinfo and end_dt.tzinfo
        self.ensure_one()
        combine = datetime.combine

        resources_list = list(resources) + [self.env['resource.resource']]
        resource_ids = [r.id for r in resources_list]
        domain = domain if domain is not None else []

        workdays_domain = expression.AND([domain, [
            ('calendar_id', '=', self.id),
            ('resource_id', 'in', resource_ids),
            ('display_type', '=', False),
        ]])

        # for each attendance spec, generate the intervals in the date range
        cache_dates = defaultdict(dict)
        cache_deltas = defaultdict(dict)
        result = defaultdict(list)

        attendances = self.env['resource.calendar.attendance'].search(workdays_domain)

        if self.env.context.get("include_weekends") or self.env.context.get("compute_payslip"):
            non_workdays_domain = expression.AND([domain, [
                ('absent_calendar_id', '=', self.id),
                ('resource_id', 'in', resource_ids),
                ('display_type', '=', False),
            ]])

            attendances = attendances + self.env['resource.calendar.attendance'].search(non_workdays_domain)

        for attendance in attendances:
            for resource in resources_list:
                # express all dates and times in specified tz or in the resource's timezone
                tz = tz if tz else timezone((resource or self).tz)
                if (tz, start_dt) in cache_dates:
                    start = cache_dates[(tz, start_dt)]
                else:
                    start = start_dt.astimezone(tz)
                    cache_dates[(tz, start_dt)] = start
                if (tz, end_dt) in cache_dates:
                    end = cache_dates[(tz, end_dt)]
                else:
                    end = end_dt.astimezone(tz)
                    cache_dates[(tz, end_dt)] = end

                start = start.date()
                if attendance.date_from:
                    start = max(start, attendance.date_from)
                until = end.date()
                if attendance.date_to:
                    until = min(until, attendance.date_to)
                if attendance.week_type:
                    start_week_type = int(math.floor((start.toordinal()-1)/7) % 2)
                    if start_week_type != int(attendance.week_type):
                        # start must be the week of the attendance
                        # if it's not the case, we must remove one week
                        start = start + relativedelta(weeks=-1)
                weekday = int(attendance.dayofweek)

                if self.two_weeks_calendar and attendance.week_type:
                    days = rrule(WEEKLY, start, interval=2, until=until, byweekday=weekday)
                else:
                    days = rrule(DAILY, start, until=until, byweekday=weekday)

                for day in days:
                    # We need to exclude incorrect days according to re-defined start previously
                    # with weeks=-1 (Note: until is correctly handled)
                    if (self.two_weeks_calendar and attendance.date_from and attendance.date_from > day.date()):
                        continue
                    # attendance hours are interpreted in the resource's timezone
                    hour_from = attendance.hour_from
                    if (tz, day, hour_from) in cache_deltas:
                        dt0 = cache_deltas[(tz, day, hour_from)]
                    else:
                        dt0 = tz.localize(combine(day, float_to_time(hour_from)))
                        cache_deltas[(tz, day, hour_from)] = dt0

                    hour_to = attendance.hour_to
                    if (tz, day, hour_to) in cache_deltas:
                        dt1 = cache_deltas[(tz, day, hour_to)]
                    else:
                        dt1 = tz.localize(combine(day, float_to_time(hour_to)))
                        cache_deltas[(tz, day, hour_to)] = dt1
                    result[resource.id].append((max(cache_dates[(tz, start_dt)], dt0), min(cache_dates[(tz, end_dt)], dt1), attendance))
        return {r.id: Intervals(result[r.id]) for r in resources_list}


class ResourceCalendarAttendance(models.Model):
    _inherit = "resource.calendar.attendance"

    absent_calendar_id = fields.Many2one("resource.calendar", string="Absent Resource's Calendar", required=False,
                                         ondelete='cascade')

    calendar_id = fields.Many2one("resource.calendar", string="Resource's Calendar", required=False,
                                  ondelete='cascade')
