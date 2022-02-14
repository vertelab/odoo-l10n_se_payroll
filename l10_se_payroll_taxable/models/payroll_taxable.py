from odoo import models, fields, api, _


class PayrollTaxable(models.Model):
    _name = "payroll.taxable"

    name = fields.Char(string="Name")
    taxable_lines = fields.One2many("payroll.taxable.line", "payroll_taxable_id", string="Taxable Lines")


class PayrollTaxableLine(models.Model):
    _name = "payroll.taxable.line"

    year = fields.Char(string="Year")
    number_of_days = fields.Char(string="Number of Days")
    table_number = fields.Char(string="Table Number")
    income_from = fields.Char(string="Income From")
    income_to = fields.Char(string="Income To")
    column1 = fields.Char(string="Column 1")
    column2 = fields.Char(string="Column 2")
    column3 = fields.Char(string="Column 3")
    column4 = fields.Char(string="Column 4")
    column5 = fields.Char(string="Column 5")
    column6 = fields.Char(string="Column 6")
    payroll_taxable_id = fields.Many2one('payroll.taxable', string="Payroll Taxable")
