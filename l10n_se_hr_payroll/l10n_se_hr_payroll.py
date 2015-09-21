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
        
    wage_tax_base        = fields.Float(string="Lönunderlag", compute=_wage_tax_base,digits_compute=dp.get_precision('Payroll'),help="Uträknat löneunderlag för beräkning av preleminär skatt" )
    
    prel_tax_tabel       = fields.Char(string="Prel skatt info", help="Ange skattetabell/kolumn/ev jämkning som ligger till grund för angivet preleminärskatteavdrag")
    prel_tax_url         = fields.Char(string="Skattetabeller SKV", default="http://www.skatteverket.se/privat/skatter/arbeteinkomst/vadblirskattenskattetabellermm/skattetabeller/",readonly=True, help="Ange skattetabell/kolumn/ev jämkning som ligger till grund för angivet preleminärskatteavdrag")
    car_company_amount     = fields.Float('Bruttolöneavdrag för bil', digits_compute=dp.get_precision('Payroll'), help="Bruttolöneavdraget för företagsbil, dvs företagets kostnad för företagsbilen")
    car_employee_deduction = fields.Float(string='Förmånsvärde för bil', digits_compute=dp.get_precision('Payroll'), help="Beräknat förmånsvärde för bil från skatteverket",) 
    car_deduction_url      = fields.Char(string='Förmånsvärdesberäkning SKV', default="http://www.skatteverket.se/privat/skatter/biltrafik/bilformansberakning", readonly=True,help="Beräknat förmånsvärde för bil från skatteverket") 
    vacation_days = fields.Float(string='Semesterdagar', digits_compute=dp.get_precision('Payroll'), help="Sparad semester i dagar",) 
    office_fund = fields.Float(string='Office fund', digits_compute=dp.get_precision('Payroll'), help="Fund for personal office supplies",) 

    def _get_param(self,param,value):
        if not self.env['ir.config_parameter'].get_param(param):
            self.env['ir.config_parameter'].set_param(param,value)
        return self.env['ir.config_parameter'].get_param(param)

    @api.one
    def _sa_deduction(self):
        if self.employee_id.age <= 26:
            self.sa_deduction = self._get_param('sa.26',25.46)
        if self.employee_id.age > 26 and self.employee_id.age <= 65:
            self.sa_deduction = self._get_param('sa.26-65',31.42)
        if self.employee_id.age > 65 and self.employee_id.age <= 77:
            self.sa_deduction = self._get_param('sa.66-77',10.21)
        if self.employee_id.age > 77:
            self.sa_deduction = self._get_param('sa.78',0)             
    sa_deduction = fields.Float(compute=_sa_deduction)

# Skapa semesterdagar månad för månad 12,85% (?) som en logg. I loggen skall aktuell månadslön lagras för semesterlönberäkning
# Förbruka semester LIFO  
# Semsterintjänandeperioden == april - mars, LIFO förra intjänandeåret. Får ej använda aktuellt intjänande år (== ej betald semester)

    @api.one
    def _compute_sheet(self):
        slip_id = self.env['hr.payslip'].create()
        for line in self.env['hr.payslip'].get_payslip_lines(self.id, slip_id):
            if line.aws:
                pass
#        self.aws_amount = 
#        self.awf_amount = 
#        self.ded_amount = 
        return True
    aws_amount = fields.Float(string="Skattepliktiga förmåner", compute=_compute_sheet,digits_compute=dp.get_precision('Payroll'),help="Skattepliktiga förmånsvärden och andra tillägg")
    awf_amount = fields.Float(string="Skattefria ersättningar", compute=_compute_sheet,digits_compute=dp.get_precision('Payroll'),help="Skattefria ersättningar")
    ded_amount = fields.Float(string="Bruttolöneavdrag", compute=_compute_sheet,digits_compute=dp.get_precision('Payroll'),help="Avdrag från bruttolönen")



class hr_employee(models.Model):
    _inherit = 'hr.employee'

    @api.one
    def _age(self):
       self.age=date.today().year - self.birthdate.year 
    age = fields.Integer(string="Age", compute=_age, help="Age to calculate social security deduction")
    



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
