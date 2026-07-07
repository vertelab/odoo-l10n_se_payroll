# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

import logging

_logger = logging.getLogger(__name__)


class HrPayslip(models.Model):
    """Extend payslip to include approved bonus requests as input lines."""
    _inherit = 'hr.payslip'

    bonus_request_ids = fields.Many2many(
        'bonus.request', string='Bonus Requests',
        help='Approved bonus requests applied to this payslip.')

    def get_inputs(self, contracts, date_from, date_to):
        res = super().get_inputs(contracts, date_from, date_to)
        if not self.employee_id:
            return res

        # Find approved bonus requests for this employee in the payslip period
        bonuses = self.env['bonus.request'].search([
            ('employee_id', '=', self.employee_id.id),
            ('state', '=', 'accounting'),
            ('payslip_id', '=', False),
            ('manager_approved_date', '>=', self.date_from),
            ('manager_approved_date', '<=', self.date_to),
        ])
        if bonuses:
            self.bonus_request_ids = bonuses
            total_bonus = sum(bonuses.mapped('bonus_amount'))
            res.append({
                'name': _('Bonus'),
                'code': 'BONUS',
                'amount': total_bonus,
                'contract_id': self.contract_id.id,
            })
        return res

    def action_payslip_done(self):
        """Mark bonus requests as applied when payslip is confirmed."""
        if self.bonus_request_ids:
            self.bonus_request_ids.write({'payslip_id': self.id})
        return super().action_payslip_done()
