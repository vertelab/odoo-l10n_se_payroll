import urllib.request
import pandas as pd
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)


class HRContract(models.Model):
    _inherit = 'hr.contract'

    table_number = fields.Integer(string="Tax Table")
    is_church_deductible = fields.Boolean(string="Deductible")
    # ~ column_number = fields.Many2one('ir.model.fields', domain=[
        # ~ ('model_id.model', '=', 'payroll.taxtable.line'), ('ttype', '=', 'float')
    # ~ ])
    column_number = fields.Selection([ ('column1', "Column 1"),('column2', "Column 2"),('column3', "Column 3"),('column4', "Column 4"),('column5', "Column 5"),('column6', "Column 6")],'Tax Column')

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
        _logger.warning(f"{self}")
        _logger.warning(f"{date}")
        _logger.warning(f"{wage}")
        fails = [key for key, value in (('date', date), ('wage', wage), ('column_number', self.column_number),
                                        ('self.table_number', self.table_number)) if not value]
        if fails:
            _logger.warning(f"Please fill these values{fails}")
            return
            
        year = date.year
        taxable_line = self.env['payroll.taxtable.line'].search([
            ('table_number', '=', self.table_number),
            ('income_from', '<=', float(wage)),
            ('income_to', '>=', float(wage)),
            ('year', '=', year)
        ])
        
        return getattr(taxable_line, self.column_number)
     
        # ~ _logger.warning(f"{self.table_number}")
        # ~ _logger.warning(f"{wage}")
        # ~ _logger.warning(f"{taxable_lines}")
        # ~ return sum([line[self.column_number].name for line in taxable_lines])
