# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HrFlexRequestWizard(models.TransientModel):
    """Wizard för att snabbt ansöka om flextidsuttag."""
    _name = 'hr.flex.request.wizard'
    _description = 'Ansök om flextidsuttag'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Anställd',
        required=True,
        default=lambda self: self.env['hr.employee'].search([
            ('user_id', '=', self.env.uid),
        ], limit=1),
    )
    request_type = fields.Selection([
        ('leave', 'Ledighet'),
        ('salary', 'Löneutbetalning'),
    ], string='Typ', required=True, default='leave')
    hours = fields.Float(string='Timmar', required=True)
    available_hours = fields.Float(
        related='bank_id.balance_hours',
        string='Tillgängliga',
    )
    bank_id = fields.Many2one(
        'hr.flex.bank',
        string='Flextidspott',
        required=True,
        domain="[('employee_id', '=', employee_id), ('state', '=', 'active')]",
    )
    date_from = fields.Date(string='Från datum')
    date_to = fields.Date(string='Till datum')
    note = fields.Text(string='Notering')

    def action_create_request(self):
        """Skapa en hr.flex.request från wizard-datan."""
        self.ensure_one()
        if self.hours <= 0:
            raise UserError(_('Antal timmar måste vara större än 0.'))
        if self.hours > self.available_hours:
            raise UserError(_('Du har bara %(avail).1f timmar tillgängliga.',
                              avail=self.available_hours))

        vals = {
            'employee_id': self.employee_id.id,
            'request_type': self.request_type,
            'hours': self.hours,
            'bank_id': self.bank_id.id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'note': self.note,
        }
        request = self.env['hr.flex.request'].create(vals)
        request.action_submit()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.flex.request',
            'res_id': request.id,
            'view_mode': 'form',
            'target': 'current',
        }
