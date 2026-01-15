from odoo import api, fields, models

class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    work_time_rate = fields.Float(
        string="Sysselsättningsgrad (%)",
        compute="_compute_work_time_rate",
        store=True,
        readonly=False,
        help="Procent av heltid (t.ex. 80)"
    )

    full_time_required_hours = fields.Float(
        string="Timmar för heltid",
        default=40.0,
        help="Antal timmar som räknas som 100% för denna kalendertyp"
    )

    @api.depends('attendance_ids', 'full_time_required_hours')
    def _compute_work_time_rate(self):
        for calendar in self:
            if calendar.full_time_required_hours > 0:
                total_hours = sum(line.hour_to - line.hour_from for line in calendar.attendance_ids if line.day_period != 'lunch')
                calendar.work_time_rate = (total_hours / calendar.full_time_required_hours) * 100
            else:
                calendar.work_time_rate = 100.0