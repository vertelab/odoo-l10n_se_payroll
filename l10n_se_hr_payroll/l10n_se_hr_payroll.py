# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2004-2015 Vertel AB (<http://vertel.se>).
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
from openerp.modules.registry import RegistryManager
import openerp.exceptions
from openerp import models, fields, api, _
from openerp import http
from openerp.http import request
from openerp import tools

import random

import logging
_logger = logging.getLogger(__name__)



from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from datetime import timedelta, date, datetime

import openerp.addons.decimal_precision as dp

class hr_contract(models.Model):
    _inherit = 'hr.contract'

    prel_tax_amount      = fields.Float(string="Prel skatt kr", digits_compute=dp.get_precision('Payroll'),help="Ange preleminär skatt i kronor" )

    def _wage_tax_base(self):
        self.wage_tax_base = (self.wage - self.aws_amount) + self.ded_amount

    wage_tax_base        = fields.Float(string="Lönunderlag",digits_compute=dp.get_precision('Payroll'),help="Uträknat löneunderlag för beräkning av preleminär skatt" )
    prel_tax_tabel       = fields.Char(string="Prel skatt info", help="Ange skattetabell/kolumn/ev jämkning som ligger till grund för angivet preleminärskatteavdrag")
    prel_tax_url         = fields.Char(string="Skattetabeller SKV", default="http://www.skatteverket.se/privat/skatter/arbeteochinkomst/skattetabeller.4.18e1b10334ebe8bc80005221.html",readonly=True, help="Ange skattetabell/kolumn/ev jämkning som ligger till grund för angivet preleminärskatteavdrag")
    #~ car_company_amount     = fields.Float('Bruttolöneavdrag för bil', digits_compute=dp.get_precision('Payroll'), help="Bruttolöneavdraget för företagsbil, dvs företagets kostnad för företagsbilen")
    #~ car_employee_deduction = fields.Float(string='Förmånsvärde för bil', digits_compute=dp.get_precision('Payroll'), help="Beräknat förmånsvärde för bil från skatteverket",)
    #~ car_deduction_url      = fields.Char(string='Förmånsvärdesberäkning SKV', default="http://www.skatteverket.se/privat/skatter/biltrafik/bilformansberakning", readonly=True,help="Beräknat förmånsvärde för bil från skatteverket")
    vacation_days = fields.Float(string='Semesterdagar', digits_compute=dp.get_precision('Payroll'), help="Sparad semester i dagar",)
    #~ office_fund = fields.Float(string='Office fund', digits_compute=dp.get_precision('Payroll'), help="Fund for personal office supplies",)
    benefit_ids = fields.One2many(comodel_name="hr.contract.benefit",inverse_name='contract_id')


    def _get_param(self,param,value):
        if not self.env['ir.config_parameter'].get_param(param):
            self.env['ir.config_parameter'].set_param(param,value)
        return self.env['ir.config_parameter'].get_param(param)

    def logthis(self,message):
        _logger.error(message)

    def evalthis(self,code,variables):
        #~ _logger.error(code)
        from openerp.tools.safe_eval import safe_eval as eval
        eval(code,variables,mode='exec',nocopy=True)

    #~ def get_account_install(self, code): # Leif Robin
        #~ return self.env['account.account'].search([('code','=',code)], limit=1)[0]



    #~ def _compute_sheet(self):
        #~ return
        #~ slip_id = self.env['hr.payslip'].create({'employee_id': self.employee_id.id})
        #~ _logger.warning('Lines %s' % self.env['hr.payslip'].get_payslip_lines([self.id], slip_id))
        #~ for line in self.env['hr.payslip'].get_payslip_lines([self.id], slip_id):
            #~ if line.aws:
                #~ pass
        #~ self.aws_amount = 0.0
        #~ self.awf_amount = 0.0
        #~ self.ded_amount = 0.0
        #~ return True
    #~ aws_amount = fields.Float(string="Skattepliktiga förmåner", compute=_compute_sheet,digits_compute=dp.get_precision('Payroll'),help="Skattepliktiga förmånsvärden och andra tillägg")
    #~ awf_amount = fields.Float(string="Skattefria ersättningar", compute=_compute_sheet,digits_compute=dp.get_precision('Payroll'),help="Skattefria ersättningar")
    #~ ded_amount = fields.Float(string="Bruttolöneavdrag", compute=_compute_sheet,digits_compute=dp.get_precision('Payroll'),help="Avdrag från bruttolönen")

    def raisethis(self,message):
        raise Warning(message)

    def is_rule(self,rules,code):
        return rules.dict.get(code, False)
        #~ try:
            #~ rules.dict[code]
            #~ return True
        #~ except:
            #~ return False

class hr_contract_benefit(models.Model):
    _name = 'hr.contract.benefit'

    contract_id = fields.Many2one(comodel_name="hr.contract")
    name = fields.Char(string="Code")
    desc = fields.Char(string="Description")
    value = fields.Float(string="Value",digits_compute=dp.get_precision('Payroll'),)

class hr_employee(models.Model):
    _inherit = 'hr.employee'

    @api.one
    def _age(self):
        #raise Warning('birthday %s today  year s' % (date.today().year))
        self.age= -1 if not self.birthday else date.today().year - datetime.strptime(self.birthday, DEFAULT_SERVER_DATE_FORMAT).year
    age = fields.Integer(string="Age", compute=_age, help="Age to calculate social security deduction")

    @api.one
    def _income_statement_count(self):
        self.income_statement_count = len(set([i.year for i in self.env['hr.employee.income_statement'].search([('employee_id','=',self.id)])]))
    income_statement_count = fields.Integer(compute="_income_statement_count")

    @api.one
    def test_attendance(self):
        import datetime
        from datetime import timedelta 
        
        
        #~ raise Warning(self.contract_id.working_hours.attendance_ids.mapped('dayofweek','hour_from'))
        self.env['hr.attendance'].search([('employee_id','=',self.id)]).unlink()
        self.env['hr.holidays'].search([('employee_id','=',self.id)]).unlink()
        
        hours_from={a.dayofweek: a.hour_from for a in self.contract_id.working_hours.attendance_ids}
        hours_to={a.dayofweek: a.hour_to for a in self.contract_id.working_hours.attendance_ids}
        date = datetime.datetime(2016, 1, 1)
        self.env['hr.holidays'].create({
                'employee_id': self.id,
                'date_from': '2016-07-04',
                'date_to': '2016-07-27',
                'status': 'validate',
                'type': 'remove',
                'holiday_status_id': 15, 
            })
        for day in range(365):
            date += timedelta(days=1)
            _logger.error('date %s start %s end %s' % (date,hours_from.get(str(date.weekday()),None),hours_to.get(str(date.weekday()),None)))
            if hours_from.get(str(date.weekday()),None) and not self.env['hr.holidays'].search([('date_from','>=',(date + timedelta(minutes=hours_from[str(date.weekday())])).strftime('%Y-%m-%d %H:%M:%S')),('date_to','<=',(date + timedelta(minutes=hours_from[str(date.weekday())])).strftime('%Y-%m-%d %H:%M:%S'))]):
                _logger.error(date + timedelta(minutes=hours_from[str(date.weekday())] * 60 + random.randint(-60,60)))
                self.with_context({'action_date': (date + timedelta(minutes=hours_from[str(date.weekday())] * 60 + random.randint(-60,60))).strftime('%Y-%m-%d %H:%M:%S')}).attendance_action_change()
                self.with_context({'action_date': (date + timedelta(minutes=hours_to[str(date.weekday())] * 60 + random.randint(-60,60))).strftime('%Y-%m-%d %H:%M:%S')}).attendance_action_change()
                
                #~ self.get_working_hours += self.env['resource.calendar'].get_working_hours(self.employee_id.contract_ids[0].working_hours.id,
                    #~ datetime.strptime(start.name, tools.DEFAULT_SERVER_DATETIME_FORMAT),
                    #~ datetime.strptime(end.name, tools.DEFAULT_SERVER_DATETIME_FORMAT))

   
    #~ def schedule_days_get_date(self, cr, uid, id, days, day_date=None, compute_leaves=False,
                               #~ resource_id=None, default_interval=None, context=None):
        #~ """ Wrapper on _schedule_days: return the beginning/ending datetime of
        #~ a days scheduling. """
        #~ res = self._schedule_days(cr, uid, id, days, day_date, compute_leaves, resource_id, default_interval, context)
        #~ return res and res[-1][1] or False   
   
            
        #~ self.income_statement_count = len(set([i.year for i in self.env['hr.employee.income_statement'].search([('employee_id','=',self.id)])]))
    #~ income_statement_count = fields.Integer(compute="_income_statement_count")
  #def generate_resources(self, cr, uid, user_ids, calendar_id, context=None):
   


#~ class hr_employee_income_statement(models.Model):
    #~ _name = 'hr.employee.income_statement'
    #~ _order = 'year, area_no_id'

    #~ employee_id = fields.Many2one('hr.employee',required=True)
    #~ year = fields.Selection([('2014','2014'),('2015','2015'),('2016','2016'),('2017','2017')],string="Year",required=True)
    #~ area_no_id = fields.Many2one('hr.income_statement.area_no',required=True)
    #~ amount = fields.Float(string="Amount")
    #~ checked = fields.Boolean(string="Checked")
    #~ code = fields.Char(string="code")
    #~ @api.one
    #~ def _value(self):
        #~ if self.area_no_id.type == 'amount':
            #~ self.value = '%4.2f' % self.amount
        #~ elif self.area_no_id.type == 'checkbox':
            #~ self.value = 'X' if self.checked else ''
        #~ elif self.area_no_id.type == "text":
            #~ self.value = self.code
        #~ elif self.area_no_id.type == "rule" and self.area_no_id.salary_rule_id:
            #~ self.value = self.area_no_id.salary_rule_id.name
    #~ value = fields.Char(string="Value",compute="_value")

#~ class hr_income_statement_area_no(models.Model):
    #~ _name = 'hr.income_statement.area_no'
    #~ _description = "Area numbers in the Income Statement form"

    #~ @api.multi
    #~ def name_get(self):
        #~ result = []
        #~ for i in self:
            #~ result.append((i.id, "(%s) %s" % (i.area_no, i.name)))
        #~ return result

    #~ name = fields.Char(string="Name",required=True)
    #~ area_no = fields.Char('Area no',required=True)
    #~ type = fields.Selection([('code','Code'),('amount','Amount'),('checkbox','Checkbox'),('rule','Rule')],string="Type",required=True)
    #~ salary_rule_id =fields.Many2one('hr.salary.rule', 'Rule',)
    #~ element_name = fields.Char(string="Element name",help="Name in XML-file")

class hr_salary_rule(models.Model):
    _inherit = 'hr.salary.rule'

    salary_art = fields.Char(string='Salary art',help="Code to interchange payslip rows with other systems")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
