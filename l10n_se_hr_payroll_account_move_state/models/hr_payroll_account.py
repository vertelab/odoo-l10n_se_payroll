from odoo import models, _

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def action_payslip_done(self):
        res = super(HrPayslip, self).action_payslip_done()

        icp = self.env['ir.config_parameter'].sudo()
        state = icp.get_param('l10n_se_hr_payroll_account_move_state.slip_state_is_draft', default=False)

        if state:
            for slip in self:
                self.env['account.move'].search([('ref','=',slip.number)],limit=1).write({'state': 'draft'})
        return res
