import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResCalendarSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Same config_parameter as ics_import_holidays.ics_url: one URL, one
    # source, so the two modules cannot read different calendars.
    ics_url_eve = fields.Char(
        string='URL of the Swedish holiday calendar',
        config_parameter='holiday.url.ics',
        default='https://www.webcal.guru/sv-SE/ladda_ner_kalendern?calendar_instance_id=86',
        help="Holiday calendar to derive the Swedish eves from.",
    )
