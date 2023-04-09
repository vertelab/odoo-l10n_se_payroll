import urllib.request
import urllib.parse
import json
import sys
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from urllib.error import URLError, HTTPError
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


    def fetch_taxtable_data(self):
        all_payslips_for_employee = self.env["hr.payslip"].search([('employee_id', '=', self.employee_id.id),])

        for payslip in all_payslips_for_employee:
            self.fetch_entire_tablenumber_SKV_data(payslip.date_from.year)

    
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
        taxtable_id = self.env['payroll.taxtable'].search([ ('name', 'like', f'%{year}%') ])

        taxtable_line = self.env['payroll.taxtable.line'].search([
            ('payroll_taxable_id.name', 'like', f'%{year}%'),
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

        self.fetch_entire_tablenumber_SKV_data(payslip.date_from.year)

        taxtable_line = self.env['payroll.taxtable.line'].search([
            ('payroll_taxable_id.name', 'like', f'%{year}%'),
            ('table_number', '=', self.table_number),
            ('income_from', '<=', float(wage)),
            ('income_to', '>=', float(wage)),
        ])

        return taxtable_line


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


    def url_open(self, request_url):
        
        try:
            response = urllib.request.urlopen(request_url)
        except HTTPError as e:
            raise Warning(f"felkod: {e.code}, self.table_number: {self.table_number}, reg_ex_income_to: {reg_ex_income_to}, year: {year}, reg_ex_income_from: {reg_ex_income_from}")
        except URLError as e:
            raise Warning(f"felkod: {e.reason}, self.table_number: {self.table_number}, reg_ex_income_to: {reg_ex_income_to}, year: {year}, reg_ex_income_from: {reg_ex_income_from}")
        else:
            response = response.read()
            return json.loads(response)


    def fetch_entire_tablenumber_SKV_data(self, year):

        url_offset = 0
        url_limit = 500
        skip_once = True #--do while, kind of
        
        taxtable_url = "https://skatteverket.entryscape.net/rowstore/dataset/88320397-5c32-4c16-ae79-d36d95b17b95?"
        request_url = f"{taxtable_url}tabellnr={self.table_number}&%C3%A5r={year}&_limit=500&_offset={url_offset}"
        response = self.url_open(request_url)

        results = response["results"]
        results_count = response["resultCount"]
        url_offset += url_limit

        next_search = "check it later"

        taxtable_name = f"Skattetabell {year}"
        taxtable_id = self.env['payroll.taxtable'].search([ ('name', 'like', f'%{year}%') ])

        if not taxtable_id:
            taxtable_id = self.env['payroll.taxtable'].create({'name': taxtable_name})

        while next_search is not None:

            if skip_once is False:
                
                if results_count - response['offset'] > url_limit:
                    request_url = f"{taxtable_url}tabellnr={self.table_number}&%C3%A5r={year}&_limit=500&_offset={url_offset}"
                    response = self.url_open(request_url)
                    results = response["results"]
                    url_offset += url_limit
                else:
                    next_search = None

            skip_once = False


            for item in results:
                #--changes percentages to currency if necessary
                if float(item['inkomst fr.o.m.']) > 60000 and float(item['kolumn 3']) < 100:
                    for index in range(1,8):
                        if index == 7 and item['kolumn 7'] == "":
                            item['kolumn 7'] = "0"
                        else:
                            #--float during calculations, int to get decimals to .00, and then back to string.
                            item[f'kolumn {index}'] = str(int(float(item['inkomst fr.o.m.']) * float(item[f'kolumn {index}']) / 100))

                taxtable_line = self.env['payroll.taxtable.line'].search([
                                                                        ('year', '=', item['år']),
                                                                        ('number_of_days', '=', item['antal dgr']),
                                                                        ('table_number', '=', item['tabellnr']),
                                                                        ('income_from', '=', item['inkomst fr.o.m.']),
                                                                        ('income_to', '=', item['inkomst t.o.m.']),
                                                                        ('column1', '=', item['kolumn 1']),
                                                                        ('column2', '=', item['kolumn 2']),
                                                                        ('column3', '=', item['kolumn 3']),
                                                                        ('column4', '=', item['kolumn 4']),
                                                                        ('column5', '=', item['kolumn 5']),
                                                                        ('column6', '=', item['kolumn 6']),
                                                                        ('column7', '=', item['kolumn 7']),
                                                                        ])

                if not taxtable_line:

                    self.env['payroll.taxtable.line'].create({

                                                            'year': item['år'],
                                                            'number_of_days': item['antal dgr'],
                                                            'table_number': item['tabellnr'],
                                                            'income_from': item['inkomst fr.o.m.'],
                                                            'income_to': item['inkomst t.o.m.'],
                                                            'column1': item['kolumn 1'],
                                                            'column2': item['kolumn 2'],
                                                            'column3': item['kolumn 3'],
                                                            'column4': item['kolumn 4'],
                                                            'column5': item['kolumn 5'],
                                                            'column6': item['kolumn 6'],
                                                            'column7': item['kolumn 7'],
                                                            'payroll_taxable_id': taxtable_id.id,
                                                            })


    def fetch_SKV_data(self, wage, year):

            reg_ex_income_to, readable_income_to = self.build_regex(wage, True)
            reg_ex_income_from, readable_income_from = self.build_regex(wage, False)

            taxtable_url = "https://skatteverket.entryscape.net/rowstore/dataset/88320397-5c32-4c16-ae79-d36d95b17b95?"
            request_url = f"{taxtable_url}tabellnr={self.table_number}&inkomst%20t.o.m.={reg_ex_income_to}&%C3%A5r={year}&inkomst%20fr.o.m.={reg_ex_income_from}&_limit=500&_offset=0"

            try:
                response = urllib.request.urlopen(request_url)
            except HTTPError as e:
                raise Warning(f"felkod: {e.code}, self.table_number: {self.table_number}, reg_ex_income_to: {reg_ex_income_to}, year: {year}, reg_ex_income_from: {reg_ex_income_from}")
            except URLError as e:
                raise Warning(f"felkod: {e.reason}, self.table_number: {self.table_number}, reg_ex_income_to: {reg_ex_income_to}, year: {year}, reg_ex_income_from: {reg_ex_income_from}")
            else:
                response = response.read()

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

                if item["inkomst t.o.m."] == "" and wage >= float(item["inkomst fr.o.m."]):
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


        return urllib.parse.quote(reg_ex_build), reg_ex_build


    def add_column_data(self, item):
        
        columns = []

        for col in range(1,8):
            columns.append(item[f"kolumn {col}"])

        return columns


