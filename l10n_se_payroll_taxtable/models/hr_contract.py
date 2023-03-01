import urllib.request
import urllib.parse
import json
import sys
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)


class HRContract(models.Model):
    _inherit = 'hr.contract'

    table_number = fields.Integer(string="Tax Table")
    is_church_deductible = fields.Boolean(string="Church Deductible")
    column_number = fields.Selection([ ('column1', "Column 1"),('column2', "Column 2"),('column3', "Column 3"),('column4', "Column 4"),('column5', "Column 5"),('column6', "Column 6"),('column7', "Column 7")],'Tax Column')
    has_tax_equalization = fields.Boolean(string="Tax Equalization")
    tax_equalization = fields.Float(string="Tax Equalization")
    tax_equalization_start = fields.Date(string="Start")
    tax_equalization_end = fields.Date(string="End")

    has_one_off_tax = fields.Boolean(string="One-off Tax")
    one_off_tax = fields.Float(string="One-off Tax")


    def action_sync_taxable(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'payroll.taxtable.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('l10_se_payroll_taxtable.view_payroll_taxtable_wizard_form').id,
            'target': 'new',
        }


    def l10_sum_columns_one_off_tax(self, wage):
        if self.has_one_off_tax:
            return wage * self.one_off_tax

    
    def l10_sum_columns_taxtable_line(self, payslip, wage):

        

        if self.has_tax_equalization and payslip.date_from >= self.tax_equalization_start and payslip.date_from <= self.tax_equalization_end:
            return wage * self.tax_equalization


        fails = [key for key, value in (('date', payslip.date_from), ('wage', wage), ('column_number', self.column_number),
                                        ('self.table_number', self.table_number)) if not value]

        if fails:
            _logger.warning(f"Please fill these values{fails}")
            return

        year = payslip.date_from.year

        taxtable_name = f"Skattetabell {year}"
        taxtable_id = self.env['payroll.taxtable'].search([ ('name', '=', taxtable_name) ])

        taxtable_line = self.env['payroll.taxtable.line'].search([
            ('payroll_taxable_id', '=', taxtable_id.id),
            ('table_number', '=', self.table_number),
            ('income_from', '<=', float(wage)),
            ('income_to', '>=', float(wage)),
        ])


        if not taxtable_line:
            taxtable_line = self.do_api_call(taxtable_id, taxtable_name, wage, year, payslip)

        return getattr(taxtable_line, self.column_number)



    def do_api_call(self, taxtable_id, taxtable_name, wage, year, payslip):

        if not taxtable_id:
            taxtable_id = self.env['payroll.taxtable'].create({ 'name': taxtable_name })

        return self.create_taxtable_line(taxtable_id.id, wage, year, payslip)



    def create_taxtable_line(self, taxtable_id, wage, year, payslip):

        income_from, income_to, columns = self.fetch_SKV_data(wage, year)

        worked_day_lines = payslip.get_worked_day_lines(payslip.contract_id, payslip.date_from, payslip.date_to)

        for line in worked_day_lines:
            number_of_days = line['number_of_days']

        #--check to see if we get the tax columns in percentage, if so convert to currency.
        if wage > 80000:
            for index, tax_amount in enumerate(columns):

                #--Column 7 is an empty string before 2023.
                if tax_amount == "":
                    tax_amount = 0
                else:
                    tax_amount = float(tax_amount)


                if tax_amount < 100:
                    percentage = tax_amount / 100
                    columns[index] = wage * percentage


        return self.env['payroll.taxtable.line'].create({

            'year': year,
            'number_of_days': number_of_days,
            'table_number': self.table_number,
            'income_from': income_from,
            'income_to': income_to,
            'column1': columns[0],
            'column2': columns[1],
            'column3': columns[2],
            'column4': columns[3],
            'column5': columns[4],
            'column6': columns[5],
            'column7': columns[6],
            'payroll_taxable_id': taxtable_id,
        })



    def fetch_SKV_data(self, wage, year):

            reg_ex_income_to = self.build_regex(wage, True)
            reg_ex_income_from = self.build_regex(wage, False)

            taxtable_url = "https://skatteverket.entryscape.net/rowstore/dataset/88320397-5c32-4c16-ae79-d36d95b17b95?"
            request_url = f"{taxtable_url}tabellnr={self.table_number}&inkomst%20t.o.m.={reg_ex_income_to}&%C3%A5r={year}&inkomst%20fr.o.m.={reg_ex_income_from}&_limit=500&_offset=0"
            response = urllib.request.urlopen(request_url).read()

            json_response = json.loads(response)

            results = json_response["results"]

            if len(results) == 0:
                raise UserError(_(f"""An error occured, no match for the search.\n
                                        Table number:{self.table_number} (most likely to be the reason for the error.)\n
                                        Year:{year}\n
                                        Wage:{wage}\n
                                    """))

            highest_value = 0
            lowest_value = sys.maxsize

            pay_up = sys.maxsize
            pay_down = 0

            
            for item in results:

                if item["inkomst t.o.m."] == "":
                    res_to = wage
                else:
                    res_to = float(item["inkomst t.o.m."])


                res_from = float(item["inkomst fr.o.m."])

                highest_value = max(res_to, highest_value)
                lowest_value = min(res_from, lowest_value)


                if wage <= res_to and wage >= res_from:
                    if res_to < pay_up:
                        pay_up = res_to
                    if res_from > pay_down:
                        pay_down = res_from
              

            columns = []
            for item in results:

                if item["inkomst t.o.m."] == "":
                    res_to = wage
                    pay_up = wage
                else:
                    res_to = float(item["inkomst t.o.m."])

                res_from = float(item["inkomst fr.o.m."])

                #--the search is not exact enough to find only the closest amounts
                if res_to <= pay_up and res_from >= pay_down:
                    columns = self.add_column_data(item)


            return pay_down, pay_up, columns



    def build_regex(self, wage, build_to):

        #--parameter build_to decides if it's a regex for income_to (True) or income_from (False)
        reg_ex_build = f"(^"

        wage_as_text = str(wage)
        wage_trim = wage_as_text.replace('.0', '')

        wage_length = len(wage_trim)
        wage_indexed = [*wage_trim]

        for index in range(2):

            counter = wage_length

            for char in wage_indexed:

                #--First number from the salary.
                if counter == wage_length:
                    
                    if index == 0:
                        reg_ex_build += f"[{char}]"
                        
                    else:
                        if build_to is True:
                            num = int(char)
                            num += 1
                            if num < 10:
                                reg_ex_build += f"[{num}]"
                            else:
                                reg_ex_build += f"[1][0-9]"
                        else:
                            num = int(char)
                            num -= 1
                            
                            if num > 0:
                                if wage_length <= 5:
                                    reg_ex_build += f"[{num}]"
                                else:
                                    #--extend the range when the amount is in the hundreds of thousands.
                                    reg_ex_build += f"[{num-1}-{num}]"
                        
                    
                elif counter > 2:
                    
                    if index == 0:
                        
                        if build_to is True:
                            
                            if counter != wage_length -1:
                                reg_ex_build += f"[0-9]"
                            else:
                                reg_ex_build += f"[{char}-9]"
                                
                        else:
                            
                            if char == "0" or counter == 3:
                                reg_ex_build += f"[0-9]"
                            else:
                                reg_ex_build += f"[0-{char}]"
                                
                    else:
                        
                        reg_ex_build += f"[0-9]"
                            
                else:
                    
                    reg_ex_build += f"[0-9]"

                counter-=1

            if index == 0:
                reg_ex_build += f"$|^"
            else:
                if build_to is True:
                    if wage_length > 3:
                        if wage_length >= 6:
                            reg_ex_build += f"$|[0-9][0-9][0-9][0-9][0-9][0-9][0-9]"
                            
                        #--amounts over the largest income to is an empty string.
                        reg_ex_build += f"$|^$)"
                        
                        
                    else:
                        #--salary under 1000, so include all thousands.
                        reg_ex_build += f"$|[0-9][0-9][0-9][0-9]|^$)"
                    
                    
                else:
                    #--wide search if salary is 600.000+ 
                    if build_to is False and wage >= 600000:
                        reg_ex_build += f"$|[0-9][0-9][0-9][0-9][0-9][0-9][0-9]"
                    #--lowest amount from the API is 1.
                    reg_ex_build += f"$|^[0-9]$)"


        return urllib.parse.quote(reg_ex_build)



    def add_column_data(self, item):
        
        columns = []

        for col in range(1,8):
            columns.append(item[f"kolumn {col}"])

        return columns


