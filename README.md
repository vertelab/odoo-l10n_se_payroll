# odoo-l10n_payroll
Swedish payroll and accounting module

Ported modules:

Module name |Description
--- | ---
 l10n_se_hr_payroll         | Ported
 l10n_se_hr_holidays        | 
 l10n_se_hr_payroll_account | Ported
 l10n_se_hr_holidays_account| 

## Demo data

`l10n_se_payroll_demo` gives the shared demo company payroll runs for
2023Q4–2027Q4: 392 payslips in 51 monthly runs, all computed, posted in
the payroll journal and paid from the bank. It depends on
`l10n_se_demo_company` (the company, the employees, the journals) and on
`l10n_se_hr_payroll_account` for the posting.

The quarters are loaded through the demo data wizard in
`l10n_se_demo_company`, in the same sequence as the accounting demo — both
sources share the `demo.dataset` model, so the two stay in step.

### The Tiichri template

`l10n_se_hr_payroll_tiichri` is **course material and is left untouched**.
It holds seven employees, twelve months of 2022 and external facit PDFs,
and it is the template the demo timeline is drawn from. The demo builds its
own salary structure and its own contracts; it reads Tiichri's data, it does
not modify it.

2024 is the anchor year: its wages, payslip inputs, leaves and benefits are
Tiichri's own, moved to 2024. 2025–2027 follow the same shape with wages
rising and the variations the plan asks for.

### Facit

`l10n_se_payroll_demo/data/facit/` holds a frozen result per quarter. It
catches regressions, not correctness — see the note in the main repo's
README.

Two things worth knowing before you change a salary rule:

- The Swedish leave types carry the work entry type codes the rules match
  on (`sjk`, `vab`, `tjl`). Odoo's own types use `LEAVE90`/`LEAVE110` and
  never match, so a leave on the wrong type silently produces no absence.
- `slip.journal_id` is related to `contract_id.journal_id`, so the contract
  must carry the payroll journal or nothing can be posted.
