# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    flex_payout_hours = fields.Float(
        string='Flextidsutbetalning (timmar)',
        compute='_compute_flex_payout',
    )

    def _compute_flex_payout(self):
        for slip in self:
            slip.flex_payout_hours = 0.0

    def compute_sheet(self):
        res = super().compute_sheet()
        self._apply_flex_payouts()
        return res

    def _apply_flex_payouts(self):
        """Applicera godkända flextids-utbetalningar som lönekorrigeringar.
        
        Detta körs som en del av compute_sheet() och skapar
        hr.payroll.correction-poster för alla godkända salary requests.
        Lönearten FLEXP i lönesystemet kommer sedan att summera dessa.
        """
        for slip in self:
            if not slip.employee_id:
                continue

            requests = self.env['hr.flex.request'].search([
                ('employee_id', '=', slip.employee_id.id),
                ('request_type', '=', 'salary'),
                ('state', '=', 'approved'),
            ])

            if not requests:
                continue

            for req in requests:
                if not req.correction_id:
                    continue

                # Applicera korrigeringen på lönespecen
                correction = req.correction_id
                if correction.state == 'draft':
                    correction._apply_to_payslip(slip)

                # Markera ansökan som utförd
                req.state = 'done'

            # Uppdatera lönespecens flextidsinformation
            slip.flex_payout_hours = sum(requests.mapped('hours'))
