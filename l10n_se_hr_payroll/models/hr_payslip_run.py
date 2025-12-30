import logging

from odoo import fields, models, api, _

_logger = logging.getLogger(__name__)

class HrPayslipRun(models.Model):
    _inherit = "hr.payslip.run"

    name = fields.Char(
        required=True, readonly=True, states={"draft": [("readonly", False)]}
    )

    period_id = fields.Many2one(comodel_name='account.period', string="Period",
                                readonly=False,
                                required=True,
                                default=lambda self: self.env['account.period'].date2period(fields.Date.today()),
                                states={"draft": [("readonly", False)]},
                                tracking=1, 
                                check_company=True)
    date_start = fields.Date(related="period_id.date_start",store=True)
    date_end = fields.Date(related="period_id.date_end",store=True)

    @api.onchange('period_id')
    def onchange_name(self):
        _logger.error(f"{self.date_start=}")
        _logger.error(f"{self.date_end=}")
        self.name = _("Salary batch for %s") % (
            self.period_id.date_start.strftime('%B-%Y') if self.period_id else 'None',
        )
        return
