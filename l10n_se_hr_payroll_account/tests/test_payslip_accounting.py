# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Verify that marking a payslip done produces a balanced accounting entry.

The Tiichri tests only assert compute_sheet() results (net pay). They never
call action_payslip_done, so they cannot prove that the accounting side
works. These tests do exactly that.
"""
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'l10n_se_payroll_accounting')
class TestPayslipAccounting(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.journal = cls.env['account.journal'].create({
            'name': 'Lönejournal Test',
            'code': 'LÖNT',
            'type': 'general',
            'company_id': cls.company.id,
        })
        cls.debit_account = cls.env['account.account'].search([
            ('account_type', '=', 'expense'),
            ('company_ids', 'in', cls.company.id),
        ], limit=1)
        cls.credit_account = cls.env['account.account'].search([
            ('account_type', '=', 'liability_current'),
            ('company_ids', 'in', cls.company.id),
        ], limit=1)
        if not (cls.debit_account and cls.credit_account):
            cls.skipTest("Chart of accounts lacks expense/liability accounts")

        cls.rule = cls.env['hr.salary.rule'].create({
            'name': 'Test Salary',
            'code': 'TSTBASE',
            'sequence': 1,
            'amount_select': 'code',
            'amount_python_compute': 'result = 1000.0',
            'account_debit': cls.debit_account.id,
            'account_credit': cls.credit_account.id,
        })
        cls.structure = cls.env['hr.payroll.structure'].create({
            'name': 'Test Structure',
            'code': 'TST',
            'company_id': cls.company.id,
            'rule_ids': [(6, 0, cls.rule.ids)],
        })
        # hr.payslip.period_id is required when the period module is installed
        cls.period = cls.env['account.period'].search([
            ('date_start', '<=', '2026-03-31'),
            ('date_stop', '>=', '2026-03-31'),
        ], limit=1)
        if not cls.period:
            fy = cls.env['account.fiscal.year'].create({
                'name': '2026',
                'date_from': '2026-01-01',
                'date_to': '2026-12-31',
                'company_id': cls.company.id,
            })
            rtype = cls.env['date.range.type'].create({
                'name': 'Month 2026',
                'company_id': cls.company.id,
            })
            dr = cls.env['date.range'].with_company(cls.company).create({
                'name': '03/2026',
                'type_id': rtype.id,
                'date_start': '2026-03-01',
                'date_end': '2026-03-31',
                'company_id': cls.company.id,
            })
            cls.period = cls.env['account.period'].create({
                'name': '03/2026',
                'date_range_id': dr.id,
                'fiscalyear_id': fy.id,
                'company_id': cls.company.id,
            })

        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Employee',
            'company_id': cls.company.id,
        })
        cls.contract = cls.env['hr.contract'].create({
            'name': 'Test Contract',
            'employee_id': cls.employee.id,
            'wage': 1000.0,
            'company_id': cls.company.id,
            'struct_id': cls.structure.id,
            'journal_id': cls.journal.id,
            'date_start': '2026-03-01',
        })

    def _make_payslip(self):
        return self.env['hr.payslip'].create({
            'name': 'Test Payslip',
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'struct_id': self.structure.id,
            'journal_id': self.journal.id,
            'company_id': self.company.id,
            'date_from': '2026-03-01',
            'date_to': '2026-03-31',
            'date': '2026-03-31',
            'period_id': self.period.id,
        })

    def test_payslip_done_creates_move(self):
        """Marking a payslip done must create an accounting entry."""
        slip = self._make_payslip()
        slip.compute_sheet()
        slip.action_payslip_done()
        self.assertTrue(slip.move_id, "No account.move was created")
        self.assertTrue(slip.move_id.line_ids, "The move has no lines")

    def test_move_balances(self):
        """The generated entry must balance."""
        slip = self._make_payslip()
        slip.compute_sheet()
        slip.action_payslip_done()
        move = slip.move_id
        debit = sum(move.line_ids.mapped('debit'))
        credit = sum(move.line_ids.mapped('credit'))
        self.assertAlmostEqual(debit, credit, places=2,
                               msg=f"Unbalanced move: debit {debit} credit {credit}")

    def test_move_uses_payslip_date(self):
        """The entry is dated with the payslip period, not today."""
        slip = self._make_payslip()
        slip.compute_sheet()
        slip.action_payslip_done()
        self.assertEqual(str(slip.move_id.date), '2026-03-31')

    def test_move_uses_salary_rule_accounts(self):
        """Debit and credit come from the salary rule."""
        slip = self._make_payslip()
        slip.compute_sheet()
        slip.action_payslip_done()
        accounts = slip.move_id.line_ids.mapped('account_id')
        self.assertIn(self.debit_account, accounts)
        self.assertIn(self.credit_account, accounts)

    def test_post_setting_off_leaves_draft(self):
        """With payroll_account_post off the entry stays in draft."""
        self.env['ir.config_parameter'].sudo().set_param(
            'l10n_se_hr_payroll_account.payroll_account_post', False)
        slip = self._make_payslip()
        slip.compute_sheet()
        slip.action_payslip_done()
        self.assertEqual(slip.move_id.state, 'draft')

    def test_post_setting_on_posts(self):
        """With payroll_account_post on the entry is posted."""
        self.env['ir.config_parameter'].sudo().set_param(
            'l10n_se_hr_payroll_account.payroll_account_post', True)
        slip = self._make_payslip()
        slip.compute_sheet()
        slip.action_payslip_done()
        self.assertEqual(slip.move_id.state, 'posted')
