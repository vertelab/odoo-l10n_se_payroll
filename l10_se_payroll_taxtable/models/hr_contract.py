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
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'payroll.taxtable.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('l10_se_payroll_taxtable.view_payroll_taxtable_wizard_form').id,
            'target': 'new',
        }

    def l10_sum_columns_taxtable_line(self, date, wage):
        year = datetime.strptime(date, '%M/%d/%Y').year
        taxable_lines = self.env['payroll.taxtable.line'].search([
            ('table_number', '=', self.table_number),
            ('income_from', '>=', wage),
            ('income_to', '<=', wage),
            ('year', '=', str(year))
        ])
        return sum([line[self.column_number].name for line in taxable_lines])
