# Copyright 2020 Shabeer VPK
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models, fields, _
from odoo.addons.resource.models.resource import Intervals

from pytz import timezone
import datetime
# from datetime import datetime, time
# from dateutil.rrule import *
#
from dateutil import rrule
import pandas as pd


#
# rules = rruleset()


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    @api.model
    def _default_weekends(self):
        return [
            (0, 0, {'name': _('Saturday Morning'), 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12,
                    'day_period': 'morning'}),
            (0, 0, {'name': _('Saturday Afternoon'), 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17,
                    'day_period': 'afternoon'}),
            (0, 0, {'name': _('Sunday Morning'), 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12,
                    'day_period': 'morning'}),
            (0, 0, {'name': _('Sunday Afternoon'), 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17,
                    'day_period': 'afternoon'}),
        ]

    weekends = fields.One2many('resource.calendar.attendance', 'weekend_calendar_id', 'Weekend Time',
                               store=True, readonly=False, copy=True, default=_default_weekends)

    def _weekend_intervals(self, start_dt, end_dt, intervals, resources, tz):
        """ Return the weekend intervals in the given datetime range.
            The returned intervals are expressed in the resource's timezone.
        """

        attendance_id = self.env['resource.calendar.attendance'].search([], limit=1)

        for resource in resources:
            interval_resource = intervals[resource.id]
            attendances = []
            wkend_list = []

            weekends = pd.bdate_range(start=start_dt, end=end_dt, freq="C", weekmask="Sat Sun").tz_convert(resource.tz)

            for attendance in interval_resource._items:
                attendances.append(attendance)

            for wkend in weekends.to_pydatetime():
                wkend_pattern = [
                    (
                        wkend.replace(hour=8),
                        wkend.replace(hour=12),
                        attendance_id
                    ),
                    (
                        wkend.replace(hour=13),
                        wkend.replace(hour=17),
                        attendance_id
                    )
                ]
                wkend_list.extend(wkend_pattern)

            attendances.extend(wkend_list)

            intervals[resource.id] = Intervals(attendances)
        return intervals

    def _attendance_intervals_batch(self, start_dt, end_dt, resources=None, domain=None, tz=None):
        res = super()._attendance_intervals_batch(
            start_dt=start_dt, end_dt=end_dt, resources=resources, domain=domain, tz=tz
        )
        if self.env.context.get("include_weekends") and resources:
            return self._weekend_intervals(start_dt, end_dt, res, resources, tz)
        return res


class ResourceCalendarAttendance(models.Model):
    _inherit = "resource.calendar.attendance"

    weekend_calendar_id = fields.Many2one("resource.calendar", string="Resource's Calendar", required=True,
                                          ondelete='cascade')
