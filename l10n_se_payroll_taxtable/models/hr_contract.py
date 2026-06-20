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
    pay_period_days = fields.Selection(
        [('1', 'Daily (1 day)'), ('7', 'Weekly (7 days)'), ('14', 'Bi-weekly (14 days)'), ('31', 'Monthly (31 days)')],
        string="Pay Period",
        default='31',
        required=True,
        help="Tax table period. Must match the employee's pay frequency.\n"
             "Monthly employees use 31, weekly use 7, etc.\n"
             "Using the wrong period gives incorrect tax withholding.")
    is_church_deductible = fields.Boolean(string="Church Deductible")
    column_number = fields.Selection(
        [('column1', "Column 1"), ('column2', "Column 2"), ('column3', "Column 3"), ('column4', "Column 4"),
         ('column5', "Column 5"), ('column6', "Column 6"), ('column7', "Column 7")], 'Tax Column')
    has_tax_equalization = fields.Boolean(string="Has Tax Equalization")
    tax_equalization = fields.Float(string="Tax Equalization")
    tax_equalization_start = fields.Date(string="Start")
    tax_equalization_end = fields.Date(string="End")

    has_one_off_tax = fields.Boolean(string="Has One-off Tax")
    one_off_tax = fields.Float(string="One-off Tax")

    def l10_sum_columns_one_off_tax(self, wage):
        if self.has_one_off_tax:
            return wage * self.one_off_tax

    def fetch_taxtable_data(self):
        all_payslips_for_employee = self.env["hr.payslip"].search([
            ('employee_id', '=', self.employee_id.id),
        ])
        # Deduplicate: fetch each unique year only once
        years = set(p.date_from.year for p in all_payslips_for_employee)
        for year in sorted(years):
            self.fetch_entire_tablenumber_SKV_data(year)

    def l10_sum_columns_taxtable_line(self, payslip, wage):

        if self.has_tax_equalization and self.tax_equalization_start <= payslip.date_from <= self.tax_equalization_end:
            return wage * self.tax_equalization

        fails = [key for key, value in
                 (('date', payslip.date_from), ('wage', wage), ('column_number', self.column_number),
                  ('self.table_number', self.table_number)) if not value]

        if fails:
            _logger.warning(f"Please fill these values{fails}")
            return

        year = str(payslip.period_id.date_start.year)
        period_days = str(self.pay_period_days or '31')

        taxtable_name = f"Skattetabell {year}"
        taxtable_id = self.env['payroll.taxtable'].search([('name', 'like', f'%{year}%')])

        taxtable_line = self.env['payroll.taxtable.line'].search([
            ('year', '=', year),
            ('number_of_days', '=', period_days),
            ('table_number', '=', self.table_number),
            ('income_from', '<=', float(wage)),
            ('income_to', '>=', float(wage)),
        ], limit=1)

        if not taxtable_line:
            taxtable_line = self.do_api_call(taxtable_id, taxtable_name, wage, year, payslip)

        return getattr(taxtable_line, self.column_number)

    def do_api_call(self, taxtable_id, taxtable_name, wage, year, payslip):

        if not taxtable_id:
            taxtable_id = self.env['payroll.taxtable'].create({'name': taxtable_name})

        self.fetch_entire_tablenumber_SKV_data(year)

        period_days = str(self.pay_period_days or '31')
        taxtable_line = self.env['payroll.taxtable.line'].search([
            ('year', '=', str(year)),
            ('number_of_days', '=', period_days),
            ('table_number', '=', self.table_number),
            ('income_from', '<=', float(wage)),
            ('income_to', '>=', float(wage)),
        ], limit=1)

        return taxtable_line

    def create_taxtable_line(self, taxtable_id, wage, year, payslip):

        income_from, income_to, columns = self.fetch_SKV_data(wage, year)

        worked_day_lines = payslip.get_worked_day_lines(payslip.contract_id, payslip.date_from, payslip.date_to)
        number_of_days = 31
        for line in worked_day_lines:
            if line.get('number_of_days'):
                number_of_days = int(line['number_of_days'])
                break

        # --check to see if we get the tax columns in percentage, if so convert to currency.
        if wage > 80000:
            for index, tax_amount in enumerate(columns):
                if tax_amount == "":
                    tax_amount = 0
                else:
                    tax_amount = float(tax_amount)
                if tax_amount < 100:
                    percentage = tax_amount / 100
                    columns[index] = wage * percentage

        return self.env['payroll.taxtable.line'].create({
            'year': str(year),
            'number_of_days': str(number_of_days),
            'table_number': self.table_number,
            'income_from': income_from,
            'income_to': income_to,
            'column1': float(columns[0] or 0),
            'column2': float(columns[1] or 0),
            'column3': float(columns[2] or 0),
            'column4': float(columns[3] or 0),
            'column5': float(columns[4] or 0),
            'column6': float(columns[5] or 0),
            'column7': float(columns[6] or 0),
            'payroll_taxable_id': taxtable_id,
        })

    def url_open(self, request_url):
        try:
            response = urllib.request.urlopen(request_url, timeout=30)
        except HTTPError as e:
            raise UserError(
                _("Skatteverket API error: HTTP %(code)s — table %(table)s, URL: %(url)s",
                  code=e.code, table=self.table_number, url=request_url))
        except URLError as e:
            raise UserError(
                _("Skatteverket API unreachable: %(reason)s — table %(table)s, URL: %(url)s",
                  reason=e.reason, table=self.table_number, url=request_url))
        else:
            return json.loads(response.read())

    def fetch_entire_tablenumber_SKV_data(self, year):

        url_offset = 0
        url_limit = 500
        skip_once = True  # --do while, kind of

        taxtable_url = "https://skatteverket.entryscape.net/rowstore/dataset/88320397-5c32-4c16-ae79-d36d95b17b95?"
        request_url = f"{taxtable_url}tabellnr={self.table_number}&%C3%A5r={year}&_limit=500&_offset={url_offset}"
        response = self.url_open(request_url)

        results = response["results"]
        results_count = response["resultCount"]
        url_offset += url_limit

        next_search = "check it later"

        taxtable_name = f"Skattetabell {year}"
        taxtable_id = self.env['payroll.taxtable'].search([('name', 'like', f'%{year}%')])

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
                # --changes percentages to currency if necessary
                if float(item['inkomst fr.o.m.']) > 60000 and float(item['kolumn 3']) < 100:
                    for index in range(1, 8):
                        if index == 7 and item['kolumn 7'] == "":
                            item['kolumn 7'] = "0"
                        else:
                            # --float during calculations, int to get decimals to .00, and then back to string.
                            item[f'kolumn {index}'] = str(
                                int(float(item['inkomst fr.o.m.']) * float(item[f'kolumn {index}']) / 100))

                taxtable_line = self.env['payroll.taxtable.line'].search([
                    ('year', '=', str(item['år'])),
                    ('number_of_days', '=', str(item['antal dgr'])),
                    ('table_number', '=', int(item['tabellnr'])),
                    ('income_from', '=', float(item['inkomst fr.o.m.'])),
                ])

                if not taxtable_line:
                    self.env['payroll.taxtable.line'].create({

                        'year': str(item['år']),
                        'number_of_days': str(item['antal dgr']),
                        'table_number': int(item['tabellnr']),
                        'income_from': float(item['inkomst fr.o.m.']),
                        'income_to': float(item['inkomst t.o.m.'] or 999999999),
                        'column1': float(item['kolumn 1']),
                        'column2': float(item['kolumn 2']),
                        'column3': float(item['kolumn 3']),
                        'column4': float(item['kolumn 4']),
                        'column5': float(item['kolumn 5']),
                        'column6': float(item['kolumn 6']),
                        'column7': float(item.get('kolumn 7') or 0),
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
            raise UserError(
                f"felkod: {e.code}, self.table_number: {self.table_number}, reg_ex_income_to: {reg_ex_income_to}, year: {year}, reg_ex_income_from: {reg_ex_income_from}")
        except URLError as e:
            raise UserError(
                f"felkod: {e.reason}, self.table_number: {self.table_number}, reg_ex_income_to: {reg_ex_income_to}, year: {year}, reg_ex_income_from: {reg_ex_income_from}")
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

            # --the search is not exact enough to find only the closest amounts
            if res_to <= pay_up and res_from >= pay_down:
                columns = self.add_column_data(item)

        return pay_down, pay_up, columns

    def build_regex(self, wage, build_to):

        # --parameter build_to decides if it's a regex for income_to (True) or income_from (False)
        reg_ex_build = f"(^"

        wage_as_text = str(wage)
        wage_trim = wage_as_text.replace('.0', '')

        wage_length = len(wage_trim)
        wage_indexed = [*wage_trim]

        for index in range(2):

            counter = wage_length

            for char in wage_indexed:

                # --First number from the salary.
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
                                    # --extend the range when the amount is in the hundreds of thousands.
                                    reg_ex_build += f"[{num - 1}-{num}]"


                elif counter > 2:

                    if index == 0:

                        if build_to is True:

                            if counter != wage_length - 1:
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

                counter -= 1

            if index == 0:
                reg_ex_build += f"$|^"
            else:
                if build_to is True:
                    if wage_length > 3:
                        if wage_length >= 6:
                            reg_ex_build += f"$|[0-9][0-9][0-9][0-9][0-9][0-9][0-9]"

                        # --amounts over the largest income to is an empty string.
                        reg_ex_build += f"$|^$)"


                    else:
                        # --salary under 1000, so include all thousands.
                        reg_ex_build += f"$|[0-9][0-9][0-9][0-9]|^$)"


                else:
                    # --wide search if salary is 600.000+
                    if build_to is False and wage >= 600000:
                        reg_ex_build += f"$|[0-9][0-9][0-9][0-9][0-9][0-9][0-9]"
                    # --lowest amount from the API is 1.
                    reg_ex_build += f"$|^[0-9]$)"

        return urllib.parse.quote(reg_ex_build), reg_ex_build

    def add_column_data(self, item):

        columns = []

        for col in range(1, 8):
            columns.append(item[f"kolumn {col}"])

        return columns
