import logging
from odoo import fields, models, api, _
import time

_logger = logging.getLogger(__name__)
IMPORT = '__import__'

class ResCalendarSettings(models.TransientModel):
    _inherit = 'res.config.settings'
        
    ics_url_eve = fields.Char(string='Enter the URL of the ICS file', config_parameter='holiday.url.ics.eve', default="Test?")
    

    @api.model
    def create(self, vals_list):
        res = super().create(vals_list)
        _logger.error('ResCalendarSettings'*100)
        if (ics_url_eve := vals_list.get("ics_url_eve")):
            ics_xmlid = f"{IMPORT}.ics_{time.strftime('%Y-%m-%d_%H:%M:%S')}_{ics_url_eve.replace('.','_')}"
            try:
                ref_try = self.env.ref(ics_xmlid)  
            except ValueError:
                external_uid = self.env['ir.model.data'].create({'module': IMPORT, 
                                    'name': ics_xmlid.split('.')[-1] + '1', 
                                    'model': 'ir.cron'})                               

                cron_name = 'Update swedish holidays'
                calendar_event_cron_model = self.env['ir.model'].search([('model', '=', 'calendar.event')]).id

                if not self.env['ir.cron'].search([('name', '=', cron_name)]):
                    _logger.error("yoooo")
                    self.env['ir.cron'].create([{'name': cron_name,
                                            'model_id': calendar_event_cron_model, 'user_id': 3, 'interval_number': 1,  
                                            'interval_type': 'months', 'code': 'model._holiday_cron()', 
                                            'numbercall': -1}])
                    _logger.error("whot")


                #secound cron jobb                            

                # cron_name_swe = 'Update swedish holidays'
                # calendar_event_cron_model_swe = self.env['ir.model'].search([('model', '=', 'import.swedish.holidays')]).id
                # import_swedish_holidays_model = self.env['ir.model'].search([('model', '=', 'import.swedish.holidays')]).id
                # if not self.env['ir.cron'].search([('name', '=', cron_name_swe)]):
                #     _logger.error("Helloooooo")
                #     self.env['ir.cron'].create([{'name': cron_name_swe,
                #                             'model_id': import_swedish_holidays_model, 'user_id': 2, 'interval_number': 1,  
                #                             'interval_type': 'months', 'code': 'model.eves_conf()', 
                #                             'numbercall': -1}])

        if not self.env['res.users'].search([('login', '=', "holidays2")]):
            self.env['res.users'].sudo().create({'name': "Holidays2", 'login': "holidays2"})
        return res
    