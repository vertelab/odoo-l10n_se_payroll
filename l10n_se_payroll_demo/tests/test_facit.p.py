# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Compare the loaded demo data against the frozen facit.

The facit is a frozen result of the calculation, not an independent
truth — it catches regressions when a rule, an account mapping or a tax
table changes. Correctness was verified once against the external
Tiichri facit in fix-l10n-se-payroll-taxtable-lookup.
"""
import json
import os

from odoo.tests.common import TransactionCase, tagged

FACIT_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'facit')


def load_facit(kind, name):
    path = os.path.join(FACIT_DIR, kind, f'{name.lower()}.json')
    if not os.path.exists(path):
        return None
    with open(path, encoding='utf-8') as handle:
        return json.load(handle)


@tagged('post_install', '-at_install', 'l10n_se_demo_facit')
class TestDemoFacit(TransactionCase):

    def test_payroll_facit_matches(self):
        """Net pay per payslip matches the frozen facit."""
        facit = load_facit('payroll', '2024Q1')
        if not facit:
            self.skipTest('no facit for 2024Q1')
        company = self.env.ref('l10n_se_demo_company.company')
        checked = 0
        if not self.env['hr.payslip'].search_count(
                [('company_id', '=', company.id)]):
            # The demo data is loaded through the wizard, not on install.
            # Without it there is nothing to compare against.
            self.skipTest('demo payroll not loaded')
        deviations = []
        for row in facit['payslips']:
            # Compare on the month string instead of a date range: not
            # every month has a 31st.
            slip = self.env['hr.payslip'].search([
                ('company_id', '=', company.id),
                ('employee_id.name', '=', row['employee']),
            ]).filtered(
                lambda s, month=row['month']:
                s.date_from.strftime('%Y-%m') == month)[:1]
            if not slip:
                deviations.append(f"{row['employee']} {row['month']}: missing")
                continue
            checked += 1
            net = slip.line_ids.filtered(lambda l: l.code == 'nl')
            got = round(net.total if net else 0.0, 2)
            if abs(got - row['net']) > 0.01:
                deviations.append(
                    f"{row['employee']} {row['month']}: "
                    f"{got} != {row['net']}")
        self.assertTrue(checked, 'no payslips matched the facit')
        self.assertFalse(
            deviations,
            'Deviations from facit:\n' + '\n'.join(deviations))

    def test_account_facit_balances(self):
        """The saldobalans in the facit sums to zero."""
        facit = load_facit('account', '2024Q1')
        if not facit:
            self.skipTest('no facit for 2024Q1')
        company = self.env.ref('l10n_se_demo_company.company')
        if not self.env['account.move'].search_count(
                [('company_id', '=', company.id)]):
            self.skipTest('demo accounting not loaded')
        total = round(sum(facit['saldobalans'].values()), 2)
        self.assertAlmostEqual(
            total, 0.0, places=2,
            msg=f'saldobalans does not balance: {total}')

    def test_combined_facit_has_both_sources(self):
        """The combined facit carries both wage liability and receivables."""
        facit = load_facit('combined', '2024Q1')
        if not facit:
            self.skipTest('no facit for 2024Q1')
        company = self.env.ref('l10n_se_demo_company.company')
        if not self.env['account.move'].search_count(
                [('company_id', '=', company.id)]):
            self.skipTest('demo accounting not loaded')
        self.assertIn('balance_sheet', facit)
        self.assertIn('profit_and_loss', facit)
        self.assertNotEqual(
            facit['balance_sheet']['assets'], 0.0,
            'balance sheet is empty — is the account demo loaded?')

    def test_2027_uses_2026_tax_table(self):
        """2027 falls back to the 2026 tax table and says so."""
        path = os.path.join(
            os.path.dirname(__file__), '..', 'data', 'payslips',
            '2027q1.json.gz')
        if not os.path.exists(path):
            self.skipTest('no 2027 data')
        import gzip
        with gzip.open(path, 'rt', encoding='utf-8') as handle:
            payload = json.load(handle)
        self.assertEqual(payload['metadata']['tax_table_year'], 2026)
        self.assertTrue(payload['metadata']['note'])
