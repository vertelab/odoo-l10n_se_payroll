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
    
    #~ @api.one
    #~ def get_days(self,employee_id):
        
        
        #~ result = dict((id, dict(max_leaves=0, leaves_taken=0, remaining_leaves=0,
                                #~ virtual_remaining_leaves=0)) for id in ids)
        #~ holiday_ids = self.env['hr.holidays'].search([('employee_id', '=', employee_id),
                                                                #~ ('state', 'in', ['confirm', 'validate1', 'validate']),
                                                                #~ ('holiday_status_id', 'in', ids)
                                                                #~ ])
                                                                
        #~ for holiday in self.pool['hr.holidays'].browse(cr, uid, holiday_ids, context=context):
            #~ status_dict = result[holiday.holiday_status_id.id]
            #~ if holiday.type == 'add':
                #~ status_dict['virtual_remaining_leaves'] += holiday.number_of_days_temp
                #~ if holiday.state == 'validate':
                    #~ status_dict['max_leaves'] += holiday.number_of_days_temp
                    #~ status_dict['remaining_leaves'] += holiday.number_of_days_temp
            #~ elif holiday.type == 'remove':  # number of days is negative
                #~ status_dict['virtual_remaining_leaves'] -= holiday.number_of_days_temp
                #~ if holiday.state == 'validate':
                    #~ status_dict['leaves_taken'] += holiday.number_of_days_temp
                    #~ status_dict['remaining_leaves'] -= holiday.number_of_days_temp
        #~ return result

    #~ def _user_left_days(self, cr, uid, ids, name, args, context=None):
        #~ employee_id = False
        #~ if context and 'employee_id' in context:
            #~ employee_id = context['employee_id']
        #~ else:
            #~ employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)], context=context)
            #~ if employee_ids:
                #~ employee_id = employee_ids[0]
        #~ if employee_id:
            #~ res = self.get_days(cr, uid, ids, employee_id, context=context)
        #~ else:
            #~ res = dict((res_id, {'leaves_taken': 0, 'remaining_leaves': 0, 'max_leaves': 0}) for res_id in ids)
        #~ return res

        #~ 'max_leaves': fields.function(_user_left_days, string='Maximum Allowed', help='This value is given by the sum of all holidays requests with a positive value.', multi='user_left_days'),
        #~ 'leaves_taken': fields.function(_user_left_days, string='Leaves Already Taken', help='This value is given by the sum of all holidays requests with a negative value.', multi='user_left_days'),
        #~ 'remaining_leaves': fields.function(_user_left_days, string='Remaining Leaves', help='Maximum Leaves Allowed - Leaves Already Taken', multi='user_left_days'),
        #~ 'virtual_remaining_leaves': fields.function(_user_left_days, string='Virtual Remaining Leaves', help='Maximum Leaves Allowed - Leaves Already Taken - Leaves Waiting Approval', multi='user_left_days'),


    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not context.get('employee_id',False):
            # leave counts is based on employee_id, would be inaccurate if not based on correct employee
            return super(hr_holidays_status, self).name_get(cr, uid, ids, context=context)

        res = []
        for record in self.browse(cr, uid, ids, context=context):
            name = record.name
            if not record.limit:
                name = name + ('  (%g/%g)' % (record.leaves_taken or 0.0, record.max_leaves or 0.0))
            res.append((record.id, name))
        return res

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




# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
