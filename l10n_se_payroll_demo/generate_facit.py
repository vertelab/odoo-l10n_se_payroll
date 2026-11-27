#!/usr/bin/env python3
"""Generate the facit for the demo datasets.

Facit is a frozen result of the calculation, not an independent truth. It
catches regressions: if a rule, an account mapping or a tax table changes,
the figures move and the test fails. It does not prove the calculation is
correct — that was done once in fix-l10n-se-payroll-taxtable-lookup against
the external Tiichri facit.

Run it against a database where the quarters have been loaded through
demo.dataset:

    sudo -n -u odoo /usr/bin/odoo shell -c /etc/odoo/odoo.conf \\
      --db_host= --db_port=5432 --db_user=odoo -d <db> --no-http \\
      < generate_facit.py

Output goes to <repo>/data/facit/:
    payroll/<year>q<n>.json   net pay, tax, contributions per employee
    account/<year>q<n>.json   saldobalans, VAT boxes, aged lists
    combined/<year>q<n>.json  balance sheet, P&L, cash flow
"""
import json
import os

HERE = os.environ.get(
    'PAYROLL_DEMO_DIR',
    '/usr/share/odoo-l10n_se_payroll/l10n_se_payroll_demo')
OUT = os.path.join(HERE, 'data', 'facit')

QUARTERS = [(2023, 4)] + [
    (year, quarter)
    for year in (2024, 2025, 2026, 2027)
    for quarter in (1, 2, 3, 4)
]


def bounds(year, quarter):
    start_month = (quarter - 1) * 3 + 1
    if quarter == 4:
        end = f'{year + 1}-01-01'
    else:
        end = f'{year}-{quarter * 3 + 1:02d}-01'
    return f'{year}-{start_month:02d}-01', end


def company(env):
    return env.ref('l10n_se_demo_company.company')


def payroll_facit(env, year, quarter):
    """Net pay, tax, contributions and benefits per employee."""
    start, end = bounds(year, quarter)
    slips = env['hr.payslip'].search([
        ('company_id', '=', company(env).id),
        ('date_from', '>=', start),
        ('date_from', '<', end),
        ('state', '=', 'done'),
    ], order='date_from, employee_id')
    out = []
    for slip in slips:
        lines = {line.code: line.total for line in slip.line_ids if line.code}
        out.append({
            'employee': slip.employee_id.name,
            'month': slip.date_from.strftime('%Y-%m'),
            'gross': round(lines.get('bl', 0.0), 2),
            'benefits': round(lines.get('fmn_total', 0.0), 2),
            'tax': round(-lines.get('total_skatt', 0.0), 2),
            'contributions': round(abs(lines.get('sa', 0.0)), 2),
            'net': round(lines.get('nl', 0.0), 2),
            # Net deductions (lunch vouchers, travel) come off after tax,
            # so net is not gross - tax. The list below covers the common
            # ones; a few rule combinations add more, so the reconciliation
            # is approximate. The authoritative figure is `net` itself.
            'net_deductions': round(sum(
                v for code, v in lines.items()
                if code in ('lunch_kupong', 'net_avd', 'res_vardag',
                            'res_helg', 'restid_grp')), 2),
        })
    return {
        'quarter': f'{year}Q{quarter}',
        'kind': 'payroll',
        'note': 'frozen result of the payslip calculation',
        'payslips': out,
        'totals': {
            'gross': round(sum(r['gross'] for r in out), 2),
            'tax': round(sum(r['tax'] for r in out), 2),
            'contributions': round(sum(r['contributions'] for r in out), 2),
            'net': round(sum(r['net'] for r in out), 2),
        },
    }


def account_facit(env, year, quarter):
    """Saldobalans, VAT boxes and aged lists."""
    comp = company(env)
    start, end = bounds(year, quarter)
    env.cr.execute("""
        SELECT aa.code_store->>'3' AS code,
               sum(aml.balance)::numeric(14,2) AS balance
          FROM account_move_line aml
          JOIN account_move am ON am.id = aml.move_id
          JOIN account_account aa ON aa.id = aml.account_id
         WHERE am.company_id = %s AND aml.date >= %s AND aml.date < %s
         GROUP BY 1
         HAVING sum(aml.balance) <> 0
         ORDER BY 1
    """, (comp.id, start, end))
    saldobalans = {row[0] or '?': float(row[1]) for row in env.cr.fetchall()}

    # VAT boxes 05-62 from the tax accounts
    def tax_balance(prefix):
        return round(sum(v for k, v in saldobalans.items()
                         if k and k.startswith(prefix)), 2)

    vat = {
        'ruta_10_utgaende_25': -tax_balance('261'),
        'ruta_11_utgaende_12': -tax_balance('262'),
        'ruta_12_utgaende_6': -tax_balance('263'),
        'ruta_20_ingaende': tax_balance('264'),
    }

    # Aged receivable / payable at the quarter end
    env.cr.execute("""
        SELECT aa.account_type,
               sum(aml.balance)::numeric(14,2)
          FROM account_move_line aml
          JOIN account_move am ON am.id = aml.move_id
          JOIN account_account aa ON aa.id = aml.account_id
         WHERE am.company_id = %s
           AND am.state = 'posted'
           AND aml.date < %s
           AND aa.account_type IN ('asset_receivable', 'liability_payable')
           AND aml.full_reconcile_id IS NULL
         GROUP BY 1
    """, (comp.id, end))
    open_items = {row[0]: float(row[1]) for row in env.cr.fetchall()}

    return {
        'quarter': f'{year}Q{quarter}',
        'kind': 'account',
        'note': 'frozen result of the ledger',
        'saldobalans': saldobalans,
        'vat': vat,
        'open_items': {
            'receivable': round(open_items.get('asset_receivable', 0.0), 2),
            'payable': round(open_items.get('liability_payable', 0.0), 2),
        },
    }


def combined_facit(env, year, quarter):
    """Balance sheet and P&L totals for the quarter end."""
    comp = company(env)
    _start, end = bounds(year, quarter)
    env.cr.execute("""
        SELECT aa.account_type, sum(aml.balance)::numeric(14,2)
          FROM account_move_line aml
          JOIN account_move am ON am.id = aml.move_id
          JOIN account_account aa ON aa.id = aml.account_id
         WHERE am.company_id = %s AND aml.date < %s
         GROUP BY 1
    """, (comp.id, end))
    by_type = {row[0]: float(row[1]) for row in env.cr.fetchall()}

    assets = sum(v for k, v in by_type.items()
                 if k.startswith('asset_'))
    liabilities = sum(-v for k, v in by_type.items()
                      if k.startswith('liability_'))
    equity = sum(-v for k, v in by_type.items() if k == 'equity')
    income = sum(-v for k, v in by_type.items() if k == 'income')
    expense = sum(v for k, v in by_type.items() if k == 'expense')

    return {
        'quarter': f'{year}Q{quarter}',
        'kind': 'combined',
        'note': 'frozen result; requires both demo sources loaded',
        'balance_sheet': {
            'assets': round(assets, 2),
            'liabilities': round(liabilities, 2),
            'equity': round(equity, 2),
        },
        'profit_and_loss': {
            'income': round(income, 2),
            'expense': round(expense, 2),
            'result': round(income - expense, 2),
        },
        'wage_liability': round(-by_type.get('liability_payable', 0.0), 2),
    }


def main():
    env = globals().get('env')
    if env is None:
        raise SystemExit('run through odoo shell')
    for kind, builder in (('payroll', payroll_facit),
                          ('account', account_facit),
                          ('combined', combined_facit)):
        directory = os.path.join(OUT, kind)
        os.makedirs(directory, exist_ok=True)
        for year, quarter in QUARTERS:
            data = builder(env, year, quarter)
            path = os.path.join(directory, f'{year}q{quarter}.json')
            with open(path, 'w', encoding='utf-8') as handle:
                json.dump(data, handle, ensure_ascii=False, indent=1)
            if kind == 'payroll':
                print(f'{kind} {year}Q{quarter}: '
                      f'{len(data["payslips"])} payslips')


main()
