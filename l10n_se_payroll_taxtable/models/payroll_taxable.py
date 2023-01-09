import urllib.request
import pandas as pd
from odoo import models, fields, api, _
from datetime import datetime


class PayrollTaxableWizard(models.Model):
    _name = "payroll.taxtable.wizard"
    _description=" "

    taxable_url = fields.Char(string="Taxable URL")

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


class PayrollTaxable(models.Model):
    _name = "payroll.taxtable"
    _description=" "

    name = fields.Char(string="Name")
    taxable_lines = fields.One2many("payroll.taxtable.line", "payroll_taxable_id", string="Taxable Lines")


class PayrollTaxableLine(models.Model):
    _name = "payroll.taxtable.line"
    _description=" "

    year = fields.Char(string="Year")
    number_of_days = fields.Char(string="Number of Days")
    table_number = fields.Integer(string="Table Number")
    income_from = fields.Float(string="Income From")
    income_to = fields.Float(string="Income To")
    column1 = fields.Float(string="Column 1")
    column2 = fields.Float(string="Column 2")
    column3 = fields.Float(string="Column 3")
    column4 = fields.Float(string="Column 4")
    column5 = fields.Float(string="Column 5")
    column6 = fields.Float(string="Column 6")

    @api.depends('column1', 'column2', 'column3', 'column4', 'column5', 'column6')
    def _sum_columns(self):
        for rec in self:
            rec.total_amount = rec.column1 + rec.column2 + rec.column3 + rec.column4 + rec.column5 + rec.column6

    total_amount = fields.Float(string="Total", compute=_sum_columns)
    payroll_taxable_id = fields.Many2one('payroll.taxtable', string="Payroll Taxable",  ondelete="cascade")
