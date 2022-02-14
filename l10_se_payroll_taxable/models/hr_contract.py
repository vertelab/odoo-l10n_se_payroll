import base64
import logging
import urllib.request
from contextlib import closing
import requests
import pandas as pd
import csv
import os
from io import StringIO

from odoo import models, fields, api, _


class HRContract(models.Model):
    _inherit = 'hr.contract'

    def action_sync_taxable(self):
        taxable_url = self.env['ir.config_parameter'].sudo().get_param('taxable_url')
        taxable_file = urllib.request.urlopen(taxable_url)
        file_name = taxable_file.info().get_filename()

        try:
            data = pd.read_csv(taxable_url, encoding='latin-1', sep=";")
            data_dict = data.to_dict('index')
            taxable_id = self.env['payroll.taxable'].create({
                'name': file_name
            })
            for tuple_vals in data_dict.values():
                self.env['payroll.taxable.line'].create({
                    'year': tuple_vals.get('År'),
                    'number_of_days': tuple_vals.get('Antal dgr'),
                    'table_number': tuple_vals.get('Tabellnr'),
                    'income_from': tuple_vals.get('Inkomst fr.o.m.'),
                    'income_to': tuple_vals.get('Inkomst t.o.m.'),
                    'column1': tuple_vals.get('Kolumn 1'),
                    'column2': tuple_vals.get('Kolumn 2'),
                    'column3': tuple_vals.get('Kolumn 3'),
                    'column4': tuple_vals.get('Kolumn 4'),
                    'column5': tuple_vals.get('Kolumn 5'),
                    'column6': tuple_vals.get('Kolumn 6'),
                    'payroll_taxable_id': taxable_id.id,
                })
        except Exception as e:
            pass


