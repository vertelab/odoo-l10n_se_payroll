# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2004-2016 Vertel AB (<http://vertel.se>).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api, _
from openerp.exceptions import Warning
import re, base64
import datetime


class hr_contract(models.Model):
    _inherit = 'hr.contract'

    partner_close_company = fields.Boolean(string="Partner Close Company",help="Partner in a close held company")
    worksite_number = fields.Char(string="Worksite Number",help="Identifiaction number of worksite, SCB")

class report_ku10_form(models.TransientModel):
    _name = 'report_ku10.form'

    @api.multi
    def to_print(recs):

        date_from = '%s-01-01' % recs[0].year
        date_to = '%s-12-31' % recs[0].year
        
        ids = []
        for e in self.env['hr.employee'].browse(recs.env.context['active_ids']):
            c008 = c009 = ''
            if e.contract_id:
                if e.contract_id.date_start > date_from:
                    c008 = datetime.datetime.strptime(fields.Date.from_string(e.contract_id.date_start),'%m')
                    if e.contract_id.date_end:
                        c009 = datetime.datetime.strptime(fields.Date.from_string(e.contract_id.date_end),'%m')
                elif e.contract_id.trial_date_start > date_from:
                    c008 = datetime.datetime.strptime(fields.Date.from_string(e.contract_id.trial_date_start),'%m')
                    if e.contract_id.trial_date_end < date_to:
                        c009 = datetime.datetime.strptime(fields.Date.from_string(e.contract_id.trial_date_end),'%m')
                    
            ids.append(self.env['report_ku10.employee'].create({
                # Inkomsttagare
                'c215': e.identification_id,
                'c215_name': e.name,
                'c215_street': e.address_home_id.street if e.address_home_id else '',
                'c215_zip': e.address_home_id.zip if e.address_home_id else '',
                'c215_city': e.address_home_id.city if e.address_home_id else '',
                'c061': 'x' if e.contract_id and e.contract_id.partner_close_company else ' ',
                'c008': c008,
                'c009': c009,
                'c060': e.contract_id.worksite_number if e.contract_id else '',
                # Uppgiftslämnare
                'c201': e.company_id.company_registry,
                'c201_name': e.company_id.name,
                # Skatt 
                'c001': sum(e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line('prej')[0]['total'])),
                # Kontant lön mm
                'c011': sum(e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line('bl')[0]['total'])),
                'c025': sum(e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line('formon')[0]['total'])),
                #~ 'c031': sum(e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line('formon')[0]['total'])),
                'c093': ' ',
                # Kostnadsersättningar
                'c050': 'x' if e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line('711')) else ' ',
                'c051': 'x' if e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line('051')) else ' ',
                'c052': 'x' if e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line('052')) else ' ',
                'c055': 'x' if e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line('055')) else ' ',
                'c056': 'x' if e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line('056')) else ' ',
                'c053': 'x' if e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line('053')) else ' ',
                'c054': 'x' if e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line('054')) else ' ',
                #~ 'c020': 'x' if e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line('711') else ' ',
            
                # Tjänstepension, övriga avdrag
                # Skattereduktion för rut/rot
                'c021': 'x' if e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line('921')) else ' ',
                'c022': 'x' if e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line('022')) else ' ',
                # Förmåner mm
                'c012': sum(e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line('formon')[0]['total'])),
                'c041': 'x' if e.contract_id and e.contract_id.benefit_ids and e.contract_id.benefit_ids.filtered(lambda b: b.name == '041') else ' ',
                'c042': 'x' if e.contract_id and e.contract_id.benefit_ids and e.contract_id.benefit_ids.filtered(lambda b: b.name == '042') else ' ',
                'c043': 'x' if e.contract_id and e.contract_id.benefit_ids and e.contract_id.benefit_ids.filtered(lambda b: b.name == '043') else ' ',
                'c044': 'x' if e.contract_id and e.contract_id.benefit_ids and e.contract_id.benefit_ids.filtered(lambda b: b.name == '044') else ' ',
                'c045': 'x' if e.contract_id and e.contract_id.benefit_ids and e.contract_id.benefit_ids.filtered(lambda b: b.name == '045') else ' ',
                'c047': 'x' if e.contract_id and e.contract_id.benefit_ids and e.contract_id.benefit_ids.filtered(lambda b: b.name == '047') else ' ',
                'c049': 'x' if e.contract_id and e.contract_id.benefit_ids and e.contract_id.benefit_ids.filtered(lambda b: b.name == '049') else ' ',
                'c065': e.contract_id.benefit_ids.filtered(lambda b: b.name == '047').mapped('desc')[0] if e.contract_id and e.contract_id.benefit_ids and e.contract_id.benefit_ids.filtered(lambda b: b.name == '047') else ' ',
                'c013': sum(e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line('013')[0]['total'])),
                'c018': sum(e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line('018')[0]['total'])),
                'c014': e.contract_id.benefit_ids.filtered(lambda b: b.name == '013').mapped('desc')[0] if e.contract_id and e.contract_id.benefit_ids and e.contract_id.benefit_ids.filtered(lambda b: b.name == '013') else ' ',
                'c015': len(e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line('013')[0]['total'])),
                'c016': sum(e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line('013')[0]['total'])),
                'c017': sum(e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line('017')[0]['total'])),
            }))

        data = {
                'model': 'report_ku10.employee',
                'ids': ids,
                'id': ids[0],
                'template': base64.b64decode(recs[0].template),
                'report_type': 'glabels'
                }
        res =  {
                'type': 'ir.actions.report.xml',
                'report_name': 'l10n_se_hr_payroll.report_ku10',
                'datas': data,
                'context': recs.env.context
                }
        return res

    ### Fields
    year = fields.Char(string="Year",help="eg 2016",default='2017')


class report_ku10_employee(models.TransientModel):
    _name = 'report_ku10.employee'

    c570 = fields.Char()
    c210 = fields.Selection([(' ',' '),('X','x')],default=' ')
    c205 = fields.Selection([(' ',' '),('X','x')],default=' ')
    c201 = fields.Char()
    c201_name = fields.Char()
    c215 = fields.Char()
    c215_name = fields.Char()
    c215_street = fields.Char()
    c215_zip = fields.Char()
    c215_city = fields.Char()
    c061 = fields.Selection([(' ',' '),('X','x')],default=' ')
    c008 = fields.Char()
    c009 = fields.Char()
    c060 = fields.Char()
    c001 = fields.Integer()
    c011 = fields.Integer()
    c025 = fields.Integer()
    c031 = fields.Integer()
    c093 = fields.Selection([(' ',' '),('X','x')],default=' ')
    c050 = fields.Selection([(' ',' '),('X','x')],default=' ')
    c051 = fields.Selection([(' ',' '),('X','x')],default=' ')
    c052 = fields.Selection([(' ',' '),('X','x')],default=' ')
    c055 = fields.Selection([(' ',' '),('X','x')],default=' ')
    c056 = fields.Selection([(' ',' '),('X','x')],default=' ')
    c053 = fields.Selection([(' ',' '),('X','x')],default=' ')
    c054 = fields.Selection([(' ',' '),('X','x')],default=' ')
    c020 = fields.Char()
    c012 = fields.Integer()
    c041 = fields.Selection([(' ',' '),('X','x')],default=' ')
    c042 = fields.Selection([(' ',' '),('X','x')],default=' ')
    c043 = fields.Selection([(' ',' '),('X','x')],default=' ')
    c044 = fields.Selection([(' ',' '),('X','x')],default=' ')
    c045 = fields.Selection([(' ',' '),('X','x')],default=' ')
    c047 = fields.Selection([(' ',' '),('X','x')],default=' ')
    c048 = fields.Selection([(' ',' '),('X','x')],default=' ')
    c049 = fields.Selection([(' ',' '),('X','x')],default=' ')
    c065 = fields.Char()
    c013 = fields.Integer()
    c018 = fields.Integer()
    c014 = fields.Integer()
    c015 = fields.Integer()
    c016 = fields.Integer()
    c017 = fields.Integer()
    c030 = fields.Integer()
    c032 = fields.Integer()
    c037 = fields.Integer()
    c070 = fields.Char()
    c035 = fields.Integer()
    c039 = fields.Integer()
    c021 = fields.Integer()
    c022 = fields.Integer()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: