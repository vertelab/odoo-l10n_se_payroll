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

class hr_employee(models.Model):
    _inherit = 'hr.employee'

    @api.multi
    def check_slip_line(self,date_from,date_to,code):
        return 'X' if self.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line(code)) else ' '
    @api.multi
    def get_slip_line_total(self,date_from,date_to,code):
        return sum(self.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line_total(code)))


    @api.multi
    def check_benefit(self,code):
        #~ if code == '043':
            #~ raise Warning(self,code,'X' if self.contract_id and self.contract_id.benefit_ids and self.contract_id.benefit_ids.filtered(lambda b: b.display_name == code) else 'Y')
        return 'X' if self.contract_id and self.contract_id.benefit_ids and self.contract_id.benefit_ids.filtered(lambda b: b.display_name == code) else ' '
    @api.multi
    def get_benefit_desc(self,code):
        return self.contract_id.benefit_ids.filtered(lambda b: b.display_name == code).mapped('desc')[0] if self.contract_id and self.contract_id.benefit_ids and self.contract_id.benefit_ids.filtered(lambda b: b.display_name == code) else ' '

        
class report_ku10_form(models.TransientModel):
    _name = 'report_ku10.form'

    @api.multi
    def to_print(self):

        date_from = '%s-01-01' % self[0].year
        date_to = '%s-12-31' % self[0].year
        
        ids = []
        for e in self.env['hr.employee'].browse(self.env.context['active_ids']):
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
                'year': self[0].year,
                'c570': '%s-%03d' % (self[0].year,e.id),
                'c210': 'X' if self[0].c210 else '', 
                'c205': 'X' if self[0].c205 else '',
                #~ # Inkomsttagare
                'c215': 'none' or e.identification_id,
                'c215_name': e.name,
                'c215_street': e.address_home_id.street if e.address_home_id else '',
                'c215_zip': e.address_home_id.zip if e.address_home_id else '',
                'c215_city': e.address_home_id.city if e.address_home_id else '',
                'c061': 'X' if e.contract_id and e.contract_id.partner_close_company else ' ',
                'c008': c008,
                'c009': c009,
                'c060': e.contract_id.worksite_number if e.contract_id and e.contract_id.worksite_number else '',
                #~ # Uppgiftslämnare
                'c201': e.company_id.company_registry,
                'c201_name': e.company_id.name,
                #~ # Skatt 
                'c001': e.get_slip_line_total(date_from,date_to,'prej'),
                #~ # Kontant lön mm
                'c011': e.get_slip_line_total(date_from,date_to,'bl'),
                #~ 'c011': sum(e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line_total('bl'))),
                'c025': sum(e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line_total('formon'))),
                #~ #'c031': sum(e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line_total('formon')[0]['total'])),
                'c093': ' ',
                #~ # Kostnadsersättningar
                'c050': e.check_slip_line(date_from,date_to,'711'),
                'c051': 'X' if e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line('051')) else ' ',
                'c052': 'X' if e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line('052')) else ' ',
                'c055': 'X' if e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line('055')) else ' ',
                'c056': 'X' if e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line('056')) else ' ',
                'c053': 'X' if e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line('053')) else ' ',
                'c054': 'X' if e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line('054')) else ' ',
                'c020': 'X' if e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line('711')) else ' ',
                #~ # Tjänstepension, övriga avdrag
                # Skattereduktion för rut/rot
                #~ 'c021': 'X' if e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line('021')) else ' ',
                #~ 'c022': 'X' if e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line('022')) else ' ',
                #~ # Förmåner mm
                'c012': sum(e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line_total('formon'))),
                'c041': e.check_benefit('041'),
                'c042': e.check_benefit('042'),
                'c043': e.check_benefit('043'),
                'c044': e.check_benefit('044'),
                'c045': e.check_benefit('045'),
                'c047': e.check_benefit('047'),
                'c048': e.check_benefit('048'),
                'c049': e.check_benefit('049'),
                'c065': e.get_benefit_desc('047'),
                'c013': sum(e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line_total('013'))),
                'c018': sum(e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line_total('018'))),
                #~ 'c014': e.contract_id.benefit_ids.filtered(lambda b: b.name == '013').mapped('desc')[0] if e.contract_id and e.contract_id.benefit_ids and e.contract_id.benefit_ids.filtered(lambda b: b.name == '013') else ' ',
                'c015': len(e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line_total('013'))),
                'c016': sum(e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line_total('013'))),
                'c017': sum(e.slip_ids.filtered(lambda s: s.date_from >= date_from and s.date_from < date_to).mapped(lambda s: s.get_slip_line_total('017'))),
            }).id)

        report = self.env['ir.actions.report.xml'].search([('report_name','=','l10n_se_hr_payroll_ku10.report_ku10')])[0]
        data = {
                'model': 'report_ku10.employee',
                'ids': ids,
                'id': ids[0],
                'template': report.glabels_template,
                #~ 'template': base64.b64decode(report.glabels_template),
                'report_type': 'glabels'
                }
        res =  {
                'type': 'ir.actions.report.xml',
                'report_name': 'l10n_se_hr_payroll_ku10.report_ku10',
                'datas': data,
                'context': self.env.context
                }
        return res

    ### Fields
    year = fields.Char(string="Year",help="eg 2016",default='2017')
    c210 = fields.Boolean(default=False,string="Rättning",help="Rättning av tidigare inlämnad kontrolluppgift")
    c205 = fields.Boolean(default=False,string="Ta bort",help="Ta bort tidigare inlämnad kontrolluppgift")

class report_ku10_employee(models.TransientModel):
    _name = 'report_ku10.employee'

    year = fields.Char()
    c570 = fields.Char()
    c210 = fields.Char() # Selection X/' '
    c210 = fields.Char() # Selection X/' '
    c205 = fields.Char() # Selection X/' '
    c201 = fields.Char()
    c201_name = fields.Char()
    c215 = fields.Char()
    c215_name = fields.Char()
    c215_street = fields.Char()
    c215_zip = fields.Char()
    c215_city = fields.Char()
    c061 = fields.Char() # Selection X/' '
    c008 = fields.Char()
    c009 = fields.Char()
    c060 = fields.Char()
    c001 = fields.Integer()
    c011 = fields.Integer()
    c025 = fields.Integer()
    c031 = fields.Integer()
    c093 = fields.Char() # Selection X/' '
    c050 = fields.Char() # Selection X/' '
    c051 = fields.Char() # Selection X/' '
    c052 = fields.Char() # Selection X/' '
    c055 = fields.Char() # Selection X/' '
    c056 = fields.Char() # Selection X/' '
    c053 = fields.Char() # Selection X/' '
    c054 = fields.Char() # Selection X/' '
    c020 = fields.Char()
    c012 = fields.Integer()
    c041 = fields.Char() # Selection X/' '
    c042 = fields.Char() # Selection X/' '
    c043 = fields.Char() # Selection X/' '
    c044 = fields.Char() # Selection X/' '
    c045 = fields.Char() # Selection X/' '
    c047 = fields.Char() # Selection X/' '
    c048 = fields.Char() # Selection X/' '
    c049 = fields.Char() # Selection X/' '
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