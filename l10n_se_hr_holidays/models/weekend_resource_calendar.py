from odoo import models, fields, api, _


class WeekendResourceCalendar(models.Model):
    _name = 'weekend.resource.calendar'
    _description = "Weekend Resource Time"

    @api.model
    def default_get(self, fields):
        res = super(WeekendResourceCalendar, self).default_get(fields)
        if not res.get('name') and res.get('company_id'):
            res['name'] = _('Weekend Hours of %s', self.env['res.company'].browse(res['company_id']).name)
        if 'attendance_ids' in fields and not res.get('attendance_ids'):
            company_id = res.get('company_id', self.env.company.id)
            company = self.env['res.company'].browse(company_id)
            company_attendance_ids = company.resource_calendar_id.attendance_ids
            if company_attendance_ids:
                res['attendance_ids'] = [
                    (0, 0, {
                        'name': attendance.name,
                        'dayofweek': attendance.dayofweek,
                        'hour_from': attendance.hour_from,
                        'hour_to': attendance.hour_to,
                        'day_period': attendance.day_period,
                    })
                    for attendance in company_attendance_ids
                ]
            else:
                res['attendance_ids'] = [
                    (0, 0, {'name': _('Saturday Morning'), 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12,
                            'day_period': 'morning'}),
                    (0, 0, {'name': _('Saturday Afternoon'), 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17,
                            'day_period': 'afternoon'}),
                    (0, 0, {'name': _('Sunday Morning'), 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12,
                            'day_period': 'morning'}),
                    (0, 0, {'name': _('Sunday Afternoon'), 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17,
                            'day_period': 'afternoon'}),
                ]
        return res

    name = fields.Char(required=True)
    active = fields.Boolean("Active", default=True,
                            help="If the active field is set to false, it will allow you to hide the Working Time without removing it.")
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env.company)
    attendance_ids = fields.One2many(
        'resource.calendar.attendance', 'calendar_id', 'Working Time',
        compute='_compute_attendance_ids', store=True, readonly=False, copy=True)

    @api.depends('company_id')
    def _compute_attendance_ids(self):
        for calendar in self.filtered(lambda c: not c._origin or c._origin.company_id != c.company_id):
            company_calendar = calendar.company_id.resource_calendar_id
            calendar.write({
                'two_weeks_calendar': company_calendar.two_weeks_calendar,
                'hours_per_day': company_calendar.hours_per_day,
                'tz': company_calendar.tz,
                'attendance_ids': [(5, 0, 0)] + [
                    (0, 0, attendance._copy_attendance_vals()) for attendance in company_calendar.attendance_ids if not attendance.resource_id]
            })
