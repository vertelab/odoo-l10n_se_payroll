from odoo import models, fields, api, _


class PayrollTaxable(models.Model):
    _name = "payroll.taxable"

    name = fields.Char(string="Name")
    taxable_lines = fields.One2many("payroll.taxable.line", "payroll_taxable_id", string="Taxable Lines")


class PayrollTaxableLine(models.Model):
    _name = "payroll.taxable.line"

    year = fields.Integer(string="Year")
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
    payroll_taxable_id = fields.Many2one('payroll.taxable', string="Payroll Taxable")
