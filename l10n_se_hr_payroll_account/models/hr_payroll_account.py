from datetime import timedelta, date, datetime
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
            date = datetime.now()
            currency = slip.company_id.currency_id

            name = _('Payslip of %s') % (slip.employee_id.name)
            move_dict = {
                'narration': name,
                'ref': f"{slip.number} {slip.employee_id.name}",
                'journal_id': slip.journal_id.id,
                'date': date,
            }

            move = self.env['account.move'].create(move_dict)
            move.period_id.date2period(move.date)
            move.message_post(body=_(
                "This was created from:") + f"<a href=# data-oe-model=hr.payslip data-oe-id={slip.id}>{slip.name}</a>")
            for line in slip.details_by_salary_rule_category:
                amount = currency.round(slip.credit_note and -line.total or line.total)
                if currency.is_zero(amount):
                    continue

                # Hitta kontot för nyvarande företag
                debit_account_id = line.salary_rule_id.account_debit.id
                credit_account_id = line.salary_rule_id.account_credit.id

                if debit_account_id:
                    values = {
                        'move_id': move.id,
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
                    context_copy.update({'check_move_validity': False})
                    new_line = self.with_context(context_copy).env['account.move.line'].create(values)
                    new_line.write({
                                       'tax_line_id': line.salary_rule_id.account_tax_id.id})  # ~ won't set the correct tax_line_id if i try to set it during create

                    debit_sum += values['debit'] - values['credit']
                if credit_account_id:
                    values = {
                        'move_id': move.id,
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
                    context_copy.update({'check_move_validity': False})
                    new_line = self.with_context(context_copy).env['account.move.line'].create(values)
                    new_line.write({
                                       'tax_line_id': line.salary_rule_id.account_tax_id.id})  # ~ won't set the correct tax_line_id if i try to set it during create
                    credit_sum += values['credit'] - values['debit']

            if currency.compare_amounts(credit_sum, debit_sum) == -1:
                acc_id = slip.journal_id.default_credit_account_id.id
                if not acc_id:
                    raise UserError(_('The Expense Journal "%s" has not properly configured the Credit Account!') % (
                        slip.journal_id.name))
                values = {
                    'move_id': move.id,
                    'name': _('Adjustment Entry'),
                    'partner_id': False,
                    'account_id': acc_id,
                    'journal_id': slip.journal_id.id,
                    'date': date,
                    'debit': 0.0,
                    'credit': currency.round(debit_sum - credit_sum),
                }
                context_copy = self.env.context.copy()
                context_copy.update({'check_move_validity': False})
                new_line = self.with_context(context_copy).env['account.move.line'].create(values)
                new_line.write({
                                   'tax_line_id': line.salary_rule_id.account_tax_id.id})  # ~ won't set the correct tax_line_id if i try to set it during create


            elif currency.compare_amounts(debit_sum, credit_sum) == -1:
                acc_id = slip.journal_id.default_debit_account_id.id
                if not acc_id:
                    raise UserError(_('The Expense Journal "%s" has not properly configured the Debit Account!') % (
                        slip.journal_id.name))
                values = {
                    'move_id': move.id,
                    'name': _('Adjustment Entry'),
                    'partner_id': False,
                    'account_id': acc_id,
                    'journal_id': slip.journal_id.id,
                    'date': date,
                    'debit': currency.round(credit_sum - debit_sum),
                    'credit': 0.0,
                }
                context_copy = self.env.context.copy()
                context_copy.update({'check_move_validity': False})
                new_line = self.with_context(context_copy).env['account.move.line'].create(values)
                new_line.write({
                                   'tax_line_id': line.salary_rule_id.account_tax_id.id})  # ~ won't set the correct tax_line_id if i try to set it during create

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


class HrSalaryRule(models.Model):
    _inherit = "hr.salary.rule"

    account_tax_char = fields.Char()  # Used to save tax name until we know which company it is.
    account_debit_char = fields.Char()  # Used to save account code until we know which company it is.
    account_credit_char = fields.Char()  # Used to save account code until we know which company it is.

    analytic_account_id = fields.Many2one(
        "account.analytic.account", "Analytic Account", domain="[('company_id','=',company_id)]")
    account_tax_id = fields.Many2one("account.tax", "Tax", domain="[('company_id','=',company_id)]")
    account_debit = fields.Many2one("account.account", "Debit Account",
                                    domain="[('deprecated', '=', False),('company_id','=',company_id)]")
    account_credit = fields.Many2one("account.account", "Credit Account",
                                     domain="[('deprecated', '=', False),('company_id','=',company_id)]")

    def write(self, vals_list):
        res = super().write(vals_list)
        for record in self:
            record.check_company_fields()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for record in res:
            record.check_company_fields()
        return res

    def check_company_fields(self):
        all_errors = ""
        for record in self:
            error = ""
            if record.company_id and record.account_debit and record.company_id != record.account_debit.company_id:
                error = error + f"Salary rule {record.name} has a debit account from a different company. {record.account_debit.code}. \n"

            if record.company_id and record.account_credit and record.company_id != record.account_credit.company_id:
                error = error + f"Salary rule {record.name} has a credit account from a different company. {record.account_credit.code}. \n"

            if record.company_id and record.account_tax_id and record.company_id != record.account_tax_id.company_id:
                error = error + f"Salary rule {record.name} has a tax from a different company. {record.account_tax_id.name}. \n"
            if len(error) > 0:
                all_errors = all_errors + error + "\n"
        if len(all_errors) > 0:
            _logger.warning(f"{all_errors=}")
            # raise UserError(all_errors)

    @api.model
    def set_account_tax_using_char_fields(self):
        all_rules = self.env['hr.salary.rule'].search([])
        # Function that will be used for multicompany setups#

        for record in all_rules:
            if record.company_id and record.account_debit_char and not record.account_debit:
                record.account_debit = self.env["account.account"].search(
                    [("company_id", "=", record.company_id.id), ("code", "=", record.account_debit_char)])
            if record.company_id and record.account_credit_char and not record.account_credit:
                record.account_credit = self.env["account.account"].search(
                    [("company_id", "=", record.company_id.id), ("code", "=", record.account_credit_char)])
            if record.company_id and record.account_tax_char and not record.account_tax_id:
                record.account_tax_id = self.env["account.tax"].search(
                    [("company_id", "=", record.company_id.id), ("name", "=", record.account_tax_char)])

    def fix_company_fields(self):
        # If it uses the account or tax from another company then we try to find it for the current company#
        for record in self:
            if record.company_id and record.account_debit and record.company_id != record.account_debit.company_id:
                record.account_debit = self.env["account.account"].search(
                    [("company_id", "=", record.company_id.id), ("code", "=", record.account_debit.code)])
            if record.company_id and record.account_credit and record.company_id != record.account_credit.company_id:
                record.account_credit = self.env["account.account"].search(
                    [("company_id", "=", record.company_id.id), ("code", "=", record.account_credit.code)])
            if record.company_id and record.account_tax_id and record.company_id != record.account_tax_id.company_id:
                record.account_tax_id = self.env["account.tax"].search(
                    [("name", "=", record.account_tax_id.name), ("company_id", "=", record.company_id.id),
                     ("type_tax_use", "=", record.account_tax_id.type_tax_use),
                     ("amount", "=", record.account_tax_id.amount)])
