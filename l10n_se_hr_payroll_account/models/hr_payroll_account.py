
from datetime import timedelta, date
from odoo import models, fields, api, _
from odoo.exceptions import UserError


import logging
_logger = logging.getLogger(__name__)


class HrPayslip(models.Model):
    _inherit = "hr.payslip"
    
    
    def action_payslip_done(self):
        self.compute_sheet()
        res = self.write({'state': 'done'})

        for slip in self:
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            date = slip.date or slip.date_to
            currency = slip.company_id.currency_id

            name = _('Payslip of %s') % (slip.employee_id.name)
            move_dict = {
                'narration': name,
                'ref': f"{slip.number}: {slip.employee_id.name}",
                'journal_id': slip.journal_id.id,
                'date': date,
            }

            move = self.env['account.move'].create(move_dict)
            move.period_id.date2period(move.date)
            move.message_post(body=_("This was created from:") + f"<a href=# data-oe-model=hr.payslip data-oe-id={slip.id}>{slip.name}</a>")
            for line in slip.details_by_salary_rule_category:
                amount = currency.round(slip.credit_note and -line.total or line.total)
                if currency.is_zero(amount):
                    continue
                debit_account_id = line.salary_rule_id.account_debit.id
                credit_account_id = line.salary_rule_id.account_credit.id

                if debit_account_id:
                    values =  {
                        'move_id':move.id,
                        'name': line.name,
                        'partner_id': line._get_partner_id(credit_account=False),
                        'account_id': debit_account_id,
                        'journal_id': slip.journal_id.id,
                        'date': date,
                        'debit': amount > 0.0 and amount or 0.0,
                        'credit': amount < 0.0 and -amount or 0.0,
                        'analytic_account_id': line.salary_rule_id.analytic_account_id.id,
                        # ~ 'tax_line_id': line.salary_rule_id.account_tax_id.id,
                    }
                    context_copy = self.env.context.copy()
                    context_copy.update({'check_move_validity':False})
                    new_line = self.with_context(context_copy).env['account.move.line'].create(values)  
                    new_line.write({'tax_line_id':line.salary_rule_id.account_tax_id.id})# ~ won't set the correct tax_line_id if i try to set it during create
                    
                    
                    debit_sum += values['debit'] -  values['credit']
                if credit_account_id:
                    values = {
                        'move_id':move.id,
                        'name': line.name,
                        'partner_id': line._get_partner_id(credit_account=True),
                        'account_id': credit_account_id,
                        'journal_id': slip.journal_id.id,
                        'date': date,
                        'debit': amount < 0.0 and -amount or 0.0,
                        'credit': amount > 0.0 and amount or 0.0,
                        'analytic_account_id': line.salary_rule_id.analytic_account_id.id,
                        # ~ 'tax_line_id': line.salary_rule_id.account_tax_id.id,
                    }
                    context_copy = self.env.context.copy()
                    context_copy.update({'check_move_validity':False})
                    new_line = self.with_context(context_copy).env['account.move.line'].create(values)  
                    new_line.write({'tax_line_id':line.salary_rule_id.account_tax_id.id})# ~ won't set the correct tax_line_id if i try to set it during create
                    credit_sum += values['credit'] - values['debit']

            if currency.compare_amounts(credit_sum, debit_sum) == -1:
                acc_id = slip.journal_id.default_credit_account_id.id
                if not acc_id:
                    raise UserError(_('The Expense Journal "%s" has not properly configured the Credit Account!') % (
                        slip.journal_id.name))
                values={
                    'move_id':move.id,
                    'name': _('Adjustment Entry'),
                    'partner_id': False,
                    'account_id': acc_id,
                    'journal_id': slip.journal_id.id,
                    'date': date,
                    'debit': 0.0,
                    'credit': currency.round(debit_sum - credit_sum),
                }
                context_copy = self.env.context.copy()
                context_copy.update({'check_move_validity':False})
                new_line = self.with_context(context_copy).env['account.move.line'].create(values)  
                new_line.write({'tax_line_id':line.salary_rule_id.account_tax_id.id})# ~ won't set the correct tax_line_id if i try to set it during create


            elif currency.compare_amounts(debit_sum, credit_sum) == -1:
                acc_id = slip.journal_id.default_debit_account_id.id
                if not acc_id:
                    raise UserError(_('The Expense Journal "%s" has not properly configured the Debit Account!') % (
                        slip.journal_id.name))
                values = {
                    'move_id':move.id,
                    'name': _('Adjustment Entry'),
                    'partner_id': False,
                    'account_id': acc_id,
                    'journal_id': slip.journal_id.id,
                    'date': date,
                    'debit': currency.round(credit_sum - debit_sum),
                    'credit': 0.0,
                }
                context_copy = self.env.context.copy()
                context_copy.update({'check_move_validity':False})
                new_line = self.with_context(context_copy).env['account.move.line'].create(values)  
                new_line.write({'tax_line_id':line.salary_rule_id.account_tax_id.id})# ~ won't set the correct tax_line_id if i try to set it during create
                

            # ~ move_dict['line_ids'] = line_ids
            # ~ move = self.env['account.move'].create(move_dict)
            slip.write({'move_id': move.id, 'date': date})
            print(move)
            print(move.line_ids)
            if not move.line_ids:
                raise UserError(_("As you installed the payroll accounting module you have to choose Debit and Credit"
                                  " account for at least one salary rule in the choosen Salary Structure."))
           
            if self.env["ir.config_parameter"].sudo().get_param("l10n_se_hr_payroll_account.payroll_account_post"):
                move.post()
        return res
