from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class HrPayrollStructure(models.Model):
    _inherit = "hr.payroll.structure"
    const_ids = fields.One2many(comodel_name = "hr_payroll.structure.const", inverse_name = "structure_id", string = "Constant")

    def get_constant(self, code):
        pass
    #mapped const_ids.filtered, (lambda c: c.code == code)
    #return filtered


class HrPayrollStructureConst(models.Model):
    _name = "hr_payroll.structure.const"
    structure_id = fields.Many2one(comodel_name = "hr.payroll.structure", string = "Structure")
    constant = fields.Float(string = "Constant")
    code = fields.Char(string = "Code")