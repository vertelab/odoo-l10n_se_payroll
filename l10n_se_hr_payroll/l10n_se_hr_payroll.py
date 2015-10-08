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
import logging
_logger = logging.getLogger(__name__)


import openerp.addons.decimal_precision as dp

class hr_contract(models.Model):
    _inherit = 'hr.contract'

    prel_tax_amount      = fields.Float(string="Prel skatt kr", digits_compute=dp.get_precision('Payroll'),help="Ange preleminär skatt i kronor" )
    
    def _wage_tax_base(self):
        self.wage_tax_base = (self.wage - self.aws_amount) + self.ded_amount 
        
    wage_tax_base        = fields.Float(string="Lönunderlag",digits_compute=dp.get_precision('Payroll'),help="Uträknat löneunderlag för beräkning av preleminär skatt" )
    prel_tax_tabel       = fields.Char(string="Prel skatt info", help="Ange skattetabell/kolumn/ev jämkning som ligger till grund för angivet preleminärskatteavdrag")
    prel_tax_url         = fields.Char(string="Skattetabeller SKV", default="http://www.skatteverket.se/privat/skatter/arbeteinkomst/vadblirskattenskattetabellermm/skattetabeller/",readonly=True, help="Ange skattetabell/kolumn/ev jämkning som ligger till grund för angivet preleminärskatteavdrag")
    #~ car_company_amount     = fields.Float('Bruttolöneavdrag för bil', digits_compute=dp.get_precision('Payroll'), help="Bruttolöneavdraget för företagsbil, dvs företagets kostnad för företagsbilen")
    #~ car_employee_deduction = fields.Float(string='Förmånsvärde för bil', digits_compute=dp.get_precision('Payroll'), help="Beräknat förmånsvärde för bil från skatteverket",) 
    #~ car_deduction_url      = fields.Char(string='Förmånsvärdesberäkning SKV', default="http://www.skatteverket.se/privat/skatter/biltrafik/bilformansberakning", readonly=True,help="Beräknat förmånsvärde för bil från skatteverket") 
    vacation_days = fields.Float(string='Semesterdagar', digits_compute=dp.get_precision('Payroll'), help="Sparad semester i dagar",) 
    #~ office_fund = fields.Float(string='Office fund', digits_compute=dp.get_precision('Payroll'), help="Fund for personal office supplies",) 

    def _get_param(self,param,value):
        if not self.env['ir.config_parameter'].get_param(param):
            self.env['ir.config_parameter'].set_param(param,value)
        return self.env['ir.config_parameter'].get_param(param)


# Skapa semesterdagar månad för månad 12,85% (?) som en logg. I loggen skall aktuell månadslön lagras för semesterlönberäkning
# Förbruka semester LIFO  
# Semsterintjänandeperioden == april - mars, LIFO förra intjänandeåret. Får ej använda aktuellt intjänande år (== ej betald semester)


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



class hr_employee(models.Model):
    _inherit = 'hr.employee'

    @api.one
    def _age(self):
       self.age=date.today().year - self.birthdate.year 
    age = fields.Integer(string="Age", compute=_age, help="Age to calculate social security deduction")
    
#~ class smart_salary_simulator_payslip(model.TransientModel):
    #~ _name = "smart_salary_simulator.payslip"
    #~ _description = "Simulated payslip"
    #~ _inherit = 'hr.payslip'
#~ 
    #~ def simulate_sheet(self, cr, uid, ids, employee, contract, context=None):
        #~ 
        #~ self.create({
            #~ 'struct_id': contract.struct_id.id,
            #~ 'employee_id': employee.id,
            #~ 'date_from': fields.Date.today(),
            #~ 'date_to': fields.Date.today(),
            #~ 'state': 'draft',
            #~ 'contract_id': contract.id,
            #~ 'input_line_ids': [
                #~ (0, _, {
                    #~ 'name': 'Salary Base',
                    #~ 'code': 'SALARY',
                    #~ 'contract_id': contract.id,
                    #~ 'amount': values['salary'],
                #~ }),
                #~ (0, _, {
                    #~ 'name': 'Year of Birth',
                    #~ 'code': 'YOB',
                    #~ 'contract_id': contract.id,
                    #~ 'amount': values['yob'],
                #~ }),
                #~ (0, _, {
                    #~ 'name': 'Withholding Tax Rate',
                    #~ 'code': 'WT',
                    #~ 'contract_id': contract.id,
                    #~ 'amount': values['tax'],
                #~ }),
                #~ (0, _, {
                    #~ 'name': 'Expenses',
                    #~ 'code': 'EXPENSES',
                    #~ 'contract_id': contract.id,
                    #~ 'amount': values['expenses'],
                #~ }),
                #~ (0, _, {
                    #~ 'name': 'Current Year',
                    #~ 'code': 'YEAR',
                    #~ 'contract_id': contract.id,
                    #~ 'amount': fields.Date.from_string(fields.Date.today()).year,
                #~ }),
                #~ ]
        #~ })
        #~ 
        #~ 
        #~ slip_line_pool = self.pool.get('hr.payslip.line')
        #~ sequence_obj = self.pool.get('ir.sequence')
        #~ for payslip in self.browse(cr, uid, ids, context=context):
            #~ #payslip.number = Reference (t.ex. SLIP/001)
            #~ number = payslip.number or sequence_obj.get(cr, uid, 'salary.slip')
            #~ #delete old payslip lines
            #~ old_slipline_ids = slip_line_pool.search(cr, uid, [('slip_id', '=', payslip.id)], context=context)
#~ #            old_slipline_ids
            #~ if old_slipline_ids:
                #~ slip_line_pool.unlink(cr, uid, old_slipline_ids, context=context)
            #~ if payslip.contract_id:
                #~ #set the list of contract for which the rules have to be applied
                #~ contract_ids = [payslip.contract_id.id]
            #~ else:
                #~ #if we don't give the contract, then the rules to apply should be for all current contracts of the employee
                #~ contract_ids = self.get_contract(cr, uid, payslip.employee_id, payslip.date_from, payslip.date_to, context=context)
            #~ lines = [(0,0,line) for line in self.pool.get('hr.payslip').get_payslip_lines(cr, uid, contract_ids, payslip.id, context=context)]
            #~ #self.write(cr, uid, [payslip.id], {'line_ids': lines, 'number': number,}, context=context)
        #~ return lines
#~ 
#~ """
#~ hr.payslip.get_payslip_lines returnerar en dict som besrkiver alla
#~ hr.payslip.lines som ska genereras:
#~ 
#~ result_dict[key] = {
                        #~ 'salary_rule_id': rule.id,
                        #~ 'contract_id': contract.id,
                        #~ 'name': rule.name,
                        #~ 'code': rule.code,
                        #~ 'category_id': rule.category_id.id,
                        #~ 'sequence': rule.sequence,
                        #~ 'appears_on_payslip': rule.appears_on_payslip,
                        #~ 'condition_select': rule.condition_select,
                        #~ 'condition_python': rule.condition_python,
                        #~ 'condition_range': rule.condition_range,
                        #~ 'condition_range_min': rule.condition_range_min,
                        #~ 'condition_range_max': rule.condition_range_max,
                        #~ 'amount_select': rule.amount_select,
                        #~ 'amount_fix': rule.amount_fix,
                        #~ 'amount_python_compute': rule.amount_python_compute,
                        #~ 'amount_percentage': rule.amount_percentage,
                        #~ 'amount_percentage_base': rule.amount_percentage_base,
                        #~ 'register_id': rule.register_id.id,
                        #~ 'amount': amount,
                        #~ 'employee_id': contract.employee_id.id,
                        #~ 'quantity': qty,
                        #~ 'rate': rate,
                    #~ }
#~ 
#~ 
#~ 
#~ key = rule.code + '-' + str(contract.id)
#~ """
#~ 


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
