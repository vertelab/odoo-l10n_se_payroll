from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class HrPayrollStructure(models.Model):
    _inherit = "hr.payroll.structure"
    const_ids = fields.One2many(comodel_name = "hr_payroll.structure.const", inverse_name = "structure_id", string = "Constant")

    def get_constant(self, code):
        #pass
        filtered_constants = self.const_ids.filtered(lambda c: c.code == code).mapped('constant')
        return filtered_constants[0] if filtered_constants else 0.0


class HrPayrollStructureConst(models.Model):
    _name = "hr_payroll.structure.const"
    structure_id = fields.Many2one(comodel_name = "hr.payroll.structure", string = "Structure")
    name = fields.Char(string = "Name")
    constant = fields.Float(string = "Constant")
    code = fields.Char(string = "Code")