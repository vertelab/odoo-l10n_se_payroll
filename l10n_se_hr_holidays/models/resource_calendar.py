# Copyright 2020 Shabeer VPK
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models
from odoo.addons.resource.models.resource import Intervals

from pytz import timezone
import datetime
# from datetime import datetime, time
# from dateutil.rrule import *
#
from dateutil import rrule


#
# rules = rruleset()


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    def _weekend_resource(self, start_dt, end_dt, resources):
        """
            (datetime.datetime(2022, 12, 30, 8, 0, tzinfo=<DstTzInfo 'Europe/Stockholm' CET+1:00:00 STD>), datetime.datetime(2022, 12, 30, 12, 0, tzinfo=<DstTzInfo 'Europe/Stockholm' CET+1:00:00 STD>), resource.calendar.attendance(9,))
            (datetime.datetime(2022, 12, 30, 13, 0, tzinfo=<DstTzInfo 'Europe/Stockholm' CET+1:00:00 STD>), datetime.datetime(2022, 12, 30, 17, 0, tzinfo=<DstTzInfo 'Europe/Stockholm' CET+1:00:00 STD>), resource.calendar.attendance(10,))
        """
        weekends = rrule.rrule(rrule.DAILY, byweekday=(rrule.SU, rrule.SA), dtstart=start_dt, until=end_dt)
        weekend_list = []
        # for weekend in weekends:
        #     weekend_list.append()

    def _weekend_intervals(self, start_dt, end_dt, intervals, resources, tz):
        """ Return the weekend intervals in the given datetime range.
            The returned intervals are expressed in the resource's timezone.
        """
        start = start_dt.date()
        until = end_dt.date()
        result = []

        # self._weekend_resource(start_dt, end_dt, resources)

        for resource in resources:
            interval_resource = intervals[resource.id]
            attendances = []
            # print(interval_resource._items)
            for attendance in interval_resource._items:
                print(attendance)
            # if attendance[0].date() not in list_by_dates:
            #         attendances.append(attendance)
            # intervals[resource.id] = Intervals(attendances)

        weekdays = [int(attendance.dayofweek) for attendance in self.attendance_ids]
        # weekends = [d for d in range(7) if d not in weekdays]

        return intervals

    def _attendance_intervals_batch(self, start_dt, end_dt, resources=None, domain=None, tz=None):
        res = super()._attendance_intervals_batch(
            start_dt=start_dt, end_dt=end_dt, resources=resources, domain=domain, tz=tz
        )
        # print(start_dt, end_dt)
        # if self.env.context.get("include_weekends") and resources:
        if resources:
            return self._weekend_intervals(
                start_dt, end_dt, res, resources, tz
            )
        return res
