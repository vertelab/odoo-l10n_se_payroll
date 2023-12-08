# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import fields, models, api, _


class HrPayslipRun(models.Model):
    _inherit = "hr.payslip.run"

    name = fields.Char(
        required=True, readonly=True, states={"draft": [("readonly", False)]}
    )

    period_id = fields.Many2one(comodel_name='account.period', string="Period",
                                readonly=True,
                                required=True,
                                default=lambda self: self.env['account.period'].date2period(fields.Date.today()),
                                states={"draft": [("readonly", False)]},
                                tracking=1, )  # domain|context|ondelperiodete="'set null', 'restrict', 'cascade'"|auto_join|delegate
    date_start = fields.Date(related='period_id.date_start')
    date_end = fields.Date(related='period_id.date_stop')

    @api.onchange('period_id')
    def onchange_employee(self):
        self.name = _("Salary batch for %s") % (
            self.period_id.date_start.strftime('%B-%Y') if self.period_id else 'None',
        )
        return
