import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    def action_payslip_done(self):
        """Odoo 18: the accounting entry is created by OCA's payroll_account.

        This module used to duplicate that logic (written for Odoo 14) and
        never called super(), so OCA's implementation never ran and the
        local copy crashed on `period_id`, `move.post()` and
        `details_by_salary_rule_category`. The Swedish contribution is the
        account/tax validation on hr.salary.rule, not the posting itself.
        """
        res = super().action_payslip_done()
        self._l10n_se_set_period_on_moves()
        self._l10n_se_apply_post_setting()
        return res

    def _l10n_se_apply_post_setting(self):
        """Honour payroll_account_post (OCA always posts).

        OCA's implementation calls action_post() unconditionally. When the
        Swedish setting is off the entry must stay in draft, so reset it to
        draft afterwards.
        """
        post = self.env['ir.config_parameter'].sudo().get_param(
            'l10n_se_hr_payroll_account.payroll_account_post')
        if post:
            return
        for slip in self.filtered('move_id'):
            move = slip.move_id
            if move.state == 'posted':
                move.button_draft()

    def _l10n_se_set_period_on_moves(self):
        """Set account.period when the period module is installed.

        `account.period` comes from account_fiscal_year_vrtl. Without it
        there is no period model and nothing to set.
        """
        if 'account.period' not in self.env.registry:
            return
        if 'period_id' not in self.env['account.move']._fields:
            return
        Period = self.env['account.period']
        for slip in self.filtered('move_id'):
            move_date = slip.date or slip.date_to
            if not move_date:
                continue
            period = Period.search([
                ('date_start', '<=', move_date),
                ('date_stop', '>=', move_date),
                ('company_id', 'in', [False, slip.company_id.id]),
            ], limit=1)
            if period:
                slip.move_id.period_id = period


class HrSalaryRule(models.Model):
    _inherit = "hr.salary.rule"

    account_tax_char = fields.Char()  # Used to save tax name until we know which company it is.
    account_debit_char = fields.Char()  # Used to save account code until we know which company it is.
    account_credit_char = fields.Char()  # Used to save account code until we know which company it is.

    # account_debit, account_credit, account_tax_id and analytic_account_id
    # are declared by OCA's payroll_account. Do not redeclare them here —
    # the local declarations used to shadow OCA's fields (and their
    # company_dependent behaviour).

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
        """Warn when a salary rule points at another company's account/tax.

        account.account has company_ids (many2many), account.tax has
        company_id (many2one). The previous version compared a many2one
        against a many2many, which is always true and produced no useful
        warning.
        """
        all_errors = ""
        for record in self:
            error = ""
            if record.company_id and record.account_debit \
                    and record.company_id not in record.account_debit.company_ids:
                error += (f"Salary rule {record.name} has a debit account from a "
                          f"different company. {record.account_debit.code}. \n")

            if record.company_id and record.account_credit \
                    and record.company_id not in record.account_credit.company_ids:
                error += (f"Salary rule {record.name} has a credit account from a "
                          f"different company. {record.account_credit.code}. \n")

            if record.company_id and record.account_tax_id \
                    and record.account_tax_id.company_id \
                    and record.company_id != record.account_tax_id.company_id:
                error += (f"Salary rule {record.name} has a tax from a different "
                          f"company. {record.account_tax_id.name}. \n")
            if error:
                all_errors += error + "\n"
        if all_errors:
            _logger.warning(all_errors)

    @api.model
    def set_account_tax_using_char_fields(self):
        all_rules = self.env['hr.salary.rule'].search([])
        # Function that will be used for multicompany setups#

        for record in all_rules:
            if record.company_id and record.account_debit_char and not record.account_debit:
                record.account_debit = self.env["account.account"].search(
                    [("company_ids", "in", record.company_id.id), ("code", "=", record.account_debit_char)])
            if record.company_id and record.account_credit_char and not record.account_credit:
                record.account_credit = self.env["account.account"].search(
                    [("company_ids", "in", record.company_id.id), ("code", "=", record.account_credit_char)])
            if record.company_id and record.account_tax_char and not record.account_tax_id:
                record.account_tax_id = self.env["account.tax"].search(
                    [("company_id", "=", record.company_id.id), ("name", "=", record.account_tax_char)])

    def fix_company_fields(self):
        # If it uses the account or tax from another company then we try to find it for the current company#
        for record in self:
            if record.company_id and record.account_debit and record.company_id != record.account_debit.company_id:
                record.account_debit = self.env["account.account"].search(
                    [("company_ids", "in", record.company_id.id), ("code", "=", record.account_debit.code)])
            if record.company_id and record.account_credit and record.company_id != record.account_credit.company_id:
                record.account_credit = self.env["account.account"].search(
                    [("company_ids", "in", record.company_id.id), ("code", "=", record.account_credit.code)])
            if record.company_id and record.account_tax_id and record.company_id != record.account_tax_id.company_id:
                record.account_tax_id = self.env["account.tax"].search(
                    [("name", "=", record.account_tax_id.name), ("company_id", "=", record.company_id.id),
                     ("type_tax_use", "=", record.account_tax_id.type_tax_use),
                     ("amount", "=", record.account_tax_id.amount)])
