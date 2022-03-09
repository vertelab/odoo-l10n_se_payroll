from odoo import models, fields, _
from odoo.exceptions import UserError


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    linked_payslip = fields.Many2one('hr.payslip',readonly=True, states={'draft': [('readonly', False)]})

    def refund_sheet(self):
        for payslip in self:
            if payslip.linked_payslip:
                raise UserError(_('Payslip is already refunded!'))
            else:
                # Create a link between the original payslip and the credited payslip
                credited_payslip = payslip.copy({'credit_note': True, 'name': _('Refund: ') + payslip.number, 'linked_payslip': payslip.id})
                payslip.linked_payslip = credited_payslip.id
                credited_payslip.compute_sheet()
                credited_payslip.action_payslip_done()

                accountmoves = self.env['account.move'].search_read([],['id'])
                for move in accountmoves:
                    move_id = move['id']
                    journal = self.env['account.move'].browse(move_id)
                    if journal.ref == credited_payslip.number:
                        credit_journal = journal
                    elif journal.ref == payslip.number:
                        original_journal = journal
                # Create a link between the credited journal to the original journal
                if credit_journal:
                    credit_journal.payment_move_id = original_journal.id
                if original_journal:
                    original_journal.payment_move_id = credit_journal.id

            formview_ref = self.env.ref('hr_payroll_community.view_hr_payslip_form', False)
            treeview_ref = self.env.ref('hr_payroll_community.view_hr_payslip_tree', False)
            return {
                'name': ("Refund Payslip"),
                'view_mode': 'tree, form',
                'view_id': False,
                'res_model': 'hr.payslip',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'domain': "[('id', 'in', %s)]" % credited_payslip.ids,
                'views': [(treeview_ref and treeview_ref.id or False, 'tree'),
                        (formview_ref and formview_ref.id or False, 'form')],
                'context': {}
            }

    # Extra safety to ensure that linked_payslip is not overwritten elsewhere
    def write(self,vals):
        for payslip in self:
            if 'linked_payslip' in vals:
                if payslip.linked_payslip:
                    vals.pop('linked_payslip')
        return super().write(vals)
