import urllib.request
import json
from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import UserError    

class PayrollTaxableWizard(models.Model):
    _name = "payroll.taxtable.wizard"
    _description=" "

    taxable_url = fields.Char(string="Taxable URL")

    def action_sync_taxable(self):

        raise UserError(_(f"action_sync_taxable is no longer implemented, odoo-l10n_se_payroll/l10n_se_payroll_taxtable/." ))


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
    column7 = fields.Float(string="Column 7")

    
    name = f"Skattetabell {year}" 

    payroll_taxable_id = fields.Many2one('payroll.taxtable', string="Payroll Taxable",  ondelete="cascade")


