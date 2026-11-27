import logging

from odoo import api, fields, models
_logger = logging.getLogger(__name__)


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    @api.model
    def _auto_init_swedish_holidays(self, *args):     
        country_se = self.env.ref('base.se', raise_if_not_found=False)
        if not country_se:
            return False

        years_to_fetch = [2021, 2022, 2023]

        for year in years_to_fetch:
            nager_cal = self.env['calendar.public.holiday'].search([
                ('year', '=', year),
                ('country_id', '=', country_se.id)
            ], limit=1)

            if not nager_cal:
                nager_cal = self.env['calendar.public.holiday'].create({
                    'year': year,
                    'country_id': country_se.id
                })

            try:
                nager_cal.fetch_public_holidays()
            except Exception as e:
                _logger.warning("Kunde inte hämta Nager-helgdagar under auto-init: %s", e)
                
        all_calendars = self.env['resource.calendar'].search([])

        if all_calendars:
            _logger.info("Kör automatisk synk av Global Leaves för testdata...")
            all_calendars.action_sync_public_holidays()

        return True