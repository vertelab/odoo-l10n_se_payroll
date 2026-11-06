import datetime
import logging

import requests
from ics import Calendar

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

IMPORT = '__import__'

# Swedish eves that do not come with the .ics file, keyed by the holiday name
# as it appears in the file. An eve is the day BEFORE the holiday that the
# calendar would otherwise count as a working day.
EVES = {
    'Nyårsdagen': 'Nyårsafton',
    'Påsk': 'Påskafton',
    'Midsommardagen': 'Midsommarafton',
    'Juldagen': 'Julafton',
}

# webcal.guru prefixes the Swedish holidays with a flag emoji, so the name
# arrives as "🇸🇪 Juldagen". Strip the prefix by checking the first word
# instead of slicing a fixed number of characters: len("🇸🇪 ") happens to be 3
# in Python, but that is a coincidence of this flag, and the slice silently
# mangles a name that carries no prefix.
def _strip_prefix(name):
    """Drop a leading non-alphanumeric token (emoji, bullet) from a name."""
    parts = name.split(' ', 1)
    if len(parts) == 2 and not parts[0].isalnum():
        return parts[1]
    return name


class ImportSwedishHolidays(models.Model):
    _inherit = 'calendar.event'

    @api.model
    def eves_conf(self):
        """Add the Swedish eves (påskafton, midsommarafton, ...) to the
        calendar and to every working schedule.

        Idempotent: an eve that already exists is not created again. Both the
        calendar.event and the resource.calendar.leaves are keyed by an
        ir.model.data xmlid derived from the name and date, and the lookup
        happens BEFORE any record is created — a create followed by an
        existence check leaks one row per run.
        """
        self = self.sudo()
        url = self.env['ir.config_parameter'].sudo().get_param('holiday.url.ics')
        if not url:
            raise UserError(_(
                "No holiday calendar URL is configured. Set it in Settings "
                "(parameter 'holiday.url.ics') before importing holidays."))
        calendar = Calendar(requests.get(url, timeout=30).text)
        responsible = self.env['res.users'].search([('login', '=', 'holidays')], limit=1)
        if not responsible:
            raise UserError(_(
                "The calendar-owning user 'holidays' does not exist. Create it "
                "before importing holidays."))

        for event in list(calendar.timeline):
            eve_name = EVES.get(_strip_prefix(event.name))
            if not eve_name:
                continue
            eve_date = event.begin.date() - datetime.timedelta(days=1)

            # Calendar event for the eve itself.
            eve_xmlid = '%s.calendar_%s_%s' % (
                IMPORT, eve_name.replace(' ', '_'), eve_date.strftime('%Y-%m-%d'))
            if not self.env.ref(eve_xmlid, raise_if_not_found=False):
                eve = self.env['calendar.event'].create({
                    'name': eve_name,
                    'start': eve_date.strftime('%Y-%m-%d'),
                    'stop': eve_date.strftime('%Y-%m-%d'),
                    'allday': True,
                    'user_id': responsible.id,
                })
                self.env['ir.model.data'].create({
                    'module': IMPORT,
                    'name': eve_xmlid.split('.')[-1],
                    'model': 'calendar.event',
                    'res_id': eve.id,
                })

            # Leave on every working schedule, so the eve is not planned as
            # working time. Date range is [eve_date, eve_date + 1 day).
            for resource_calendar in self.env['resource.calendar'].search([]):
                hours_week = resource_calendar.hours_per_day * 5
                leave_xmlid = '%s.leaves_eve_%s' % (IMPORT, ('%s_%s_%s' % (
                    hours_week,
                    eve_name.replace(' ', '_'),
                    eve_date.strftime('%Y-%m-%d'),
                )).replace('.', '_'))
                if self.env.ref(leave_xmlid, raise_if_not_found=False):
                    continue
                leave = self.env['resource.calendar.leaves'].create({
                    'name': eve_name,
                    'calendar_id': resource_calendar.id,
                    'date_from': datetime.datetime.combine(
                        eve_date, datetime.time.min),
                    'date_to': datetime.datetime.combine(
                        eve_date + datetime.timedelta(days=1), datetime.time.min),
                })
                self.env['ir.model.data'].create({
                    'module': IMPORT,
                    'name': leave_xmlid.split('.')[-1],
                    'model': 'resource.calendar.leaves',
                    'res_id': leave.id,
                })
