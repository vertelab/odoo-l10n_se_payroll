import logging
from odoo import fields, models, api, _
import time

_logger = logging.getLogger(__name__)
IMPORT = '__import__'

class ResCalendarSettings(models.TransientModel):
    _inherit = 'res.config.settings'
        
    ics_url_eve = fields.Char(string='Enter the URL of the ICS file', config_parameter='holiday.url.ics', default='https://www.webcal.guru/sv-SE/ladda_ner_kalendern?calendar_instance_id=86')
        
    @api.model
    def create(self, vals_list):
        res = super().create(vals_list)
        if (ics_url_eve := vals_list.get("ics_url_eve")):
            ics_xmlid = f"{IMPORT}.ics_{time.strftime('%Y-%m-%d_%H:%M:%S')}_{ics_url_eve.replace('.','_')}"
            try:
                ref_try = self.env.ref(ics_xmlid)  
            except ValueError:
                external_uid = self.env['ir.model.data'].create({'module': IMPORT, 
                                    'name': ics_xmlid.split('.')[-1], 
                                    'model': 'ir.cron'})                               

                cron_name = 'Update holidays URL: ' + ics_url_eve
                cron_name_swe = 'Update swedish holidays URL: ' + ics_url_eve
                calendar_event_cron_model = self.env['ir.model'].search([('model', '=', 'calendar.event')]).id

                if not self.env['ir.cron'].search([('name', '=', cron_name)]):
                    self.env['ir.cron'].create([{'name': cron_name,
                                            'model_id': calendar_event_cron_model, 'user_id': 2, 'interval_number': 1,  
                                            'interval_type': 'months', 'code': 'model._holiday_cron()', 
                                            'numbercall': -1}])

                if not self.env['ir.cron'].search([('name', '=', cron_name_swe)]):
                    self.env['ir.cron'].create([{'name': cron_name_swe,
                                            'model_id': calendar_event_cron_model, 'user_id': 2, 'interval_number': 1,  
                                            'interval_type': 'months', 'code': 'model.eves_conf()', 
                                            'numbercall': -1}])

            if not self.env['res.users'].search([('login', '=', "holidays")]):
                self.env['res.users'].sudo().create({'name': "Holidays", 'login': "holidays"})

        return res
    
    
    