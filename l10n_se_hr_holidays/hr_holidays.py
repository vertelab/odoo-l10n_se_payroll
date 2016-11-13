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
import openerp.exceptions
from openerp import models, fields, api, _

import logging
_logger = logging.getLogger(__name__)

class hr_holidays(models.Model):
    _inherit = "hr.holidays"

    earning_id = fields.Many2one(comodel_name='hr.holidays.earning')
    



class hr_holidays_status(models.Model):
    _inherit = "hr.holidays.status"

    payslip_rule = fields.Text(string='Earning Rule',help="Python Code")
    payslip_condition = fields.Text(string='Earning Condition',help="Python Code")
    
    
    @api.one
    def _holidays_allowed(self):
        holidays_allowed = not (self.date_earing_start and self.date_earing_end) or fields.Date.today() > self.date_earing_end
    holidays_allowed = fields.Boolean(string="Allowed",compute='_holidays_allowed')
    
    @api.model
    def get_earning_holiday(self):
        holidays = self.env['hr.holidays.status'].search([('date_earning_start','>',fields.Date.today()),('date_earning_end','<',fields.Date.today())]) 
        return holidays[0] if len(holidays)>0 else None
        
    date_earning_start = fields.Date(string='Earning year starts')
    date_earning_end = fields.Date(string='Earning year ends')
    
    
    @api.one
    def earn_leaves_days(self):
        for employee in self.env['hr.employee'].search([]):
            earning_days = self.env['hr.payslip'].get_leaves_earnings_days(employee,self.date_earning_start,self.date_earning_end)
            if earning_days['employed_days'] - earning_days['absent_days'] > 0:
                holiday = self.env['hr.holidays'].create({
						'name': '%s earned days' % self.name,
						'employee_id': employee.id,
						'holiday_status_id': self.id,
                        'type': 'add',
                        'state': 'validate',
						'number_of_days_temp': round(((earning_days['employed_days'] - earning_days['absent_days']) * employee.get_leaves_days(self.date_earning_start,self.date_earning_end) / 365) + 0.5,0),
				})
                self.env['mail.message'].create({
                    'body': _("Earn days %s: %s (%s)" % (earning_days,holiday.number_of_days_temp,employee.get_leaves_days(self.date_earning_start,self.date_earning_end))),
                    'subject': "Calculation",
                    'author_id': self.env['res.users'].browse(self.env.uid).partner_id.id,
                    'res_id': holiday.id,
                    'model': holiday._name,
                    'type': 'notification',})

class hr_holidays_earning(models.Model):
    _name = "hr.holidays.earning"

    employee_id = fields.Many2one(comodel_name='hr.employee')
    holiday_status_id = fields.Many2one(comodel_name='hr.holidays.status')
  
    @api.one
    def get_holidays_ids(self):
        return self.env['hr.holidays'].search([('employee_id', '=', self.employee_id),('state', 'in', ['confirm', 'validate1', 'validate']),('holiday_status_id', '=', self.holiday_status_id.id)])
    @api.one
    def get_payslips_ids(self):
        return self.env['hr.payslip'].search([('employee_id', '=', self.employee_id),('state', 'in', ['confirm', 'validate1', 'validate'])])

    @api.model
    def earn_leaves(self,payslip):
        return 1.0

    @api.one
    def _calc_leaves(self):
        self.leaves_taken = sum([h.number_of_days_temp for h in self.get_holidays_ids()])
        self.max_leaves = sum([self.earn_leaves(p) for p in self.get_payslips_ids()])
        self.remaining_leaves = self.max_leaves - leaves_taken
        self.virtual_remaining_leaves = 0.0
    max_leaves = fields.Float(string='Max Leaves',compute="_calc_leaves")    
    leaves_take  = fields.Float(string='Leaves Take',compute="_calc_leaves")
    remaining_leaves  = fields.Float(string='Remaining Leaves',compute="_calc_leaves")
    virtual_remaining_leaves  = fields.Float(string='Virtual remaining Leaves',compute="_calc_leaves")

            
class hr_employee(models.Model):
    _inherit = 'hr.employee'

    holidays_earning_ids = fields.Many2many(string='Holiday Earnings',comodel_name="hr.holidays.earning")
    
    @api.model
    def get_leaves_days(self,date_from,date_to):
		return self.contract_id.vacation_days
		#employee.contract_ids.filtered(lambda c: c.date_end == None or c.date_end > leaves.date_earning_start).leaves_days

class hr_payslip(models.Model):
    _inherit = 'hr.payslip'
    
    @api.model
    def get_leaves_earnings_days(self,employee,date_from,date_to):
        employed_days = worked_days = absent_days = 0
        for slip in self.env['hr.payslip'].search([('employee_id','=',employee.id),('date_from','>=',date_from),('date_to','<=',date_to)]):
            employed_days += (fields.Date.from_string(slip.date_to) - fields.Date.from_string(slip.date_from)).days
            worked_days += slip.worked_days_line_ids.filtered(lambda l: l.code == 'WORK100').number_of_days if slip.worked_days_line_ids.filtered(lambda l: l.code == 'WORK100') else 0.0
            absent_days += sum(a.number_of_days for a in slip.worked_days_line_ids.filtered(lambda l: l.code != 'WORK100'))
        return {'employed_days' : employed_days, 'absent_days': absent_days, 'worked_days': worked_days}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
