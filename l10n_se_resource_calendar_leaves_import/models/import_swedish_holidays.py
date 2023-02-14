import logging
import datetime
from modulefinder import IMPORT_NAME
from ics import Calendar
import requests
from odoo import fields, models, api, _
_logger = logging.getLogger(__name__)
IMPORT = '__import__'

#Swedish eves that dosent come with the ics file
eves = {
    'Nyårsdagen' : 'Nyårsafton',
    'Påsk': 'Påskafton',
    'Midsommardagen': 'Midsommarafton',
    'Juldagen': 'Julafton',
}


class ImportSwedishHolidays(models.Model):
    _inherit = 'calendar.event'
    # _description='Import Swedish eves'

    @api.model
    def eves_conf(self):
        _logger.error("GO")
        url = self.env['ir.config_parameter'].sudo().get_param('holiday.url.ics')
        calendar = Calendar(requests.get(url).text)
        responsible_id = self.env['res.users'].search([('login', '=', 'holidays')])[0].id

        for event in list(calendar.timeline):
            event_xmlid = f"{IMPORT}.calendar_{event.name.replace(' ', '_')}_{event.begin.date().strftime('%Y-%m-%d')}"

            #Event_id is needed as a refrens for eve_id, so the code knows at what date to add the eves
            event_id = {'name': event.name, 
                        'start': event.begin.date(), 
                        'stop': event.begin.date(), 
                        'allday': 'True',
                        'user_id': responsible_id
                        }

            #Creates the eves
            for key, value in eves.items():
                if event.name[3::] in key:
                    eve = {'name': eves[event.name[3::]],
                            'start': (event_id['start'] - datetime.timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'), 
                            'stop': (event_id['stop'] - datetime.timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'),
                            'allday': 'True',
                            'user_id': responsible_id
                            }
                    
                    eve_xmlid = f"{IMPORT}.calendar_{eve['name'].replace(' ', '_')}_{eve['start']}".replace(' ', '_')
                    if not self.env['ir.model.data'].search([('name','=',eve_xmlid.split('.')[-1])]):
                        eve_id = self.env["calendar.event"].create(eve)


                        #Adds the eves to the calendar module
                        external_uid = self.env['ir.model.data'].create({'module': IMPORT, 
                                                    'name': eve_xmlid.split('.')[-1], 
                                                    'model': 'calendar.event',
                                                    'res_id': f"{eve_id.id}"
                                                    })  
                        
            #The next part is to make sure that the days that is on work days are conted as leaves
            for resource_calendar in self.env['resource.calendar'].search_read([], ['id', 'hours_per_day']):  
                hours_week = (resource_calendar['hours_per_day'] * 5)
                uid = f"{hours_week}_{event.name.replace(' ', '_')}_{event.begin.date().strftime('%Y-%m-%d')}".replace('.','_')
                leave_xmlid = f"{IMPORT}.leaves_{uid}"
                
                #Refrens for leave_eve_id
                leave_id = {'name': event.name,
                            'calendar_id': resource_calendar['id'], 
                            'date_from': (event.begin.date()), 
                            'date_to': (event.begin.date() + datetime.timedelta(days=1))
                            }

                for key, value in eves.items():
                    if event.name[3::] == key:

                        leave_eve = {'name': eves[event.name[3::]],
                                        'calendar_id': resource_calendar['id'], 
                                        'date_from': (leave_id['date_from'] - datetime.timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'), 
                                        'date_to': (leave_id['date_to'] - datetime.timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
                                        }
                    
                        leave_eve_id = self.env["resource.calendar.leaves"].create(leave_eve)
                        
                        uid_eve = f"{hours_week}_{leave_eve_id['name'].replace(' ', '_')}_{leave_eve_id['date_from'].strftime('%Y-%m-%d')}".replace('.','_')
                        leave_eve_xmlid = f"{IMPORT}.leaves_eve_{uid_eve}"

                        if not self.env['ir.model.data'].search([('name','=',leave_eve_xmlid.split('.')[-1])]):

                        
                            external_uid = self.env['ir.model.data'].create({'module': IMPORT, 
                                                    'name': leave_eve_xmlid.split('.')[-1],
                                                    'model': 'resource.calendar.leaves',
                                                    'res_id': leave_eve_id.id
                                                    })   


