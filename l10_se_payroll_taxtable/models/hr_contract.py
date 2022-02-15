import urllib.request
import pandas as pd
from odoo import models, fields, api, _
from datetime import datetime


class HRContract(models.Model):
    _inherit = 'hr.contract'

    table_number = fields.Integer(string="Tax Table")
    is_church_deductible = fields.Boolean(string="Deductible")
    column_number = fields.Many2one('ir.model.fields', domain=[
        ('model_id.model', '=', 'payroll.taxtable.line'), ('ttype', '=', 'float')
    ])

    def action_sync_taxable(self):
        taxable_url = self.env['ir.config_parameter'].sudo().get_param('taxable_url')
        taxable_file = urllib.request.urlopen(taxable_url)
        file_name = taxable_file.info().get_filename()

        try:
            data = pd.read_csv(taxable_url, encoding='latin-1', sep=";")
            data_dict = data.to_dict('index')
            taxable_id = self.env['payroll.taxtable'].create({
                'name': file_name
            })
            for tuple_vals in data_dict.values():
                self.env['payroll.taxtable.line'].create({
                    'year': tuple_vals.get('År'),
                    'number_of_days': tuple_vals.get('Antal dgr'),
                    'table_number': 0 if tuple_vals.get('Tabellnr') == 'null' else tuple_vals.get('Tabellnr'),
                    'income_from': 0 if tuple_vals.get('Inkomst fr.o.m.') == 'null' else tuple_vals.get(
                        'Inkomst fr.o.m.'),
                    'income_to': 0 if tuple_vals.get('Inkomst t.o.m.') == 'null' else tuple_vals.get('Inkomst t.o.m.'),
                    'column1': 0 if tuple_vals.get('Kolumn 1') == 'null' else float(tuple_vals.get('Kolumn 1')),
                    'column2': 0 if tuple_vals.get('Kolumn 2') == 'null' else float(tuple_vals.get('Kolumn 2')),
                    'column3': 0 if tuple_vals.get('Kolumn 3') == 'null' else float(tuple_vals.get('Kolumn 3')),
                    'column4': 0 if tuple_vals.get('Kolumn 4') == 'null' else float(tuple_vals.get('Kolumn 4')),
                    'column5': 0 if tuple_vals.get('Kolumn 5') == 'null' else float(tuple_vals.get('Kolumn 5')),
                    'column6': 0 if tuple_vals.get('Kolumn 6') == 'null' else float(tuple_vals.get('Kolumn 6')),
                    'payroll_taxable_id': taxable_id.id,
                })
        except Exception as e:
            pass

    def l10_sum_columns_taxtable_line(self, date):
        year = datetime.strptime(date, '%M/%d/%Y').year
        taxable_lines = self.env['payroll.taxtable.line'].search([
            ('table_number', '=', self.table_number),
            ('income_from', '>=', self.wage),
            ('income_to', '<=', self.wage),
            ('year', '=', str(year))
        ])
        return sum([line[self.column_number].name for line in taxable_lines])
