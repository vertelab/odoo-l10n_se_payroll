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

    @api.model
    def create(self, vals_list):
        res = super().create(vals_list)
        if vals_list.get('ics_url_eve') and not self.env['res.users'].search(
                [('login', '=', 'holidays')], limit=1):
            # Scheduling lives in data/cron_tasks.xml (cron.task), not here:
            # a cron created at settings-save time cannot be verified against
            # the code and duplicates on every save.
            self.env['res.users'].sudo().create({
                'name': 'Holidays',
                'login': 'holidays',
            })
        return res
