# odoo-l10n_payroll
Swedish payroll and accounting module

## P-filer

Modulerna är p-filade. `*.p.py` / `*.p.xml` är **originalet** och finns på alla
utgåvegrenar; den genererade filen (`*.py` / `*.xml`) committas per gren och
redigeras aldrig för hand.

```bash
# Expandera för den utgåva du testar — bara den
rm -f modul/models/x.py && preprocess -f -D VERSION=19.0 -o modul/models/x.py modul/models/x.p.py
```

Använd alltid `-D VERSION=<utgåva>`. `preprocess --version` skriver verktygets
egen version och expanderar ingenting — en STALE-kontroll skriven så ger
falskt grönt.

Manifestet heter `__manifest__.p.py` och anger `'version': '1.0'` **utan**
utgåveprefix; Odoo lägger själv till serien (`adapt_version`: `1.0` → `18.0.1.0`).

## Porteringsstatus

Mätt 2026-11-26 mot `pfile_18.0`, `pfile_19.0`, `pfile_20.0`. Status är
`ir_module_module.state` — aldrig grennamn. `installed` = porterad och testad.

| Modul | 18.0 | 19.0 | 20.0 | Blockerare |
|---|---|---|---|---|
| `hr_leave_dashboard` | installed | installed | installed | — |
| `hr_work_anniversary_reminder` | installed | installed | installed | — (migrerad till `hr.version`) |
| `l10n_se_hr_payroll` | installed | uninstalled | uninstalled | `payroll` (klass 1/2), `hr_timesheet_sheet` (klass 1), `cron_tick` (uppströms) |
| `l10n_se_hr_payroll_benefits` | uninstalled | uninstalled | uninstalled | `l10n_se_hr_payroll` |
| `l10n_se_hr_payroll_collective` | uninstalled | uninstalled | uninstalled | `l10n_se_hr_payroll` |
| `l10n_se_hr_payroll_fk` | uninstalled | uninstalled | uninstalled | `l10n_se_hr_payroll` |
| `l10n_se_hr_payroll_lop` | uninstalled | uninstalled | uninstalled | `l10n_se_hr_payroll` |
| `l10n_se_hr_payroll_bonus_workflow` | uninstalled | uninstalled | uninstalled | `l10n_se_hr_payroll` |
| `l10n_se_hr_payroll_tiichri` | uninstalled | uninstalled | uninstalled | `l10n_se_hr_payroll_benefits` |
| `l10n_se_hr_payroll_tiichri_26` | uninstalled | uninstalled | uninstalled | `l10n_se_hr_payroll_tiichri` |
| `l10n_se_hr_payroll_account` | uninstalled | uninstalled | uninstalled | `l10n_se_hr_payroll`, `payroll_account` (klass 2) |
| `l10n_se_hr_payroll_ags` | uninstalled | uninstalled | uninstalled | `l10n_se_hr_payroll`, `payroll` |
| `l10n_se_hr_payroll_pension` | uninstalled | uninstalled | uninstalled | `l10n_se_hr_payroll`, `payroll` |
| `l10n_se_hr_payroll_union` | uninstalled | uninstalled | uninstalled | `l10n_se_hr_payroll`, `payroll` |
| `l10n_se_hr_payroll_flex` | uninstalled | uninstalled | uninstalled | `l10n_se_hr_payroll`, `hr_timesheet_sheet` |
| `l10n_se_hr_payroll_kontrolluppgift` | uninstalled | uninstalled | uninstalled | `l10n_se_hr_payroll`, `payroll` |
| `l10n_se_payroll_agd` | uninstalled | uninstalled | uninstalled | `l10n_se_hr_payroll`, `payroll` |
| `l10n_se_payroll_fora` | uninstalled | uninstalled | uninstalled | `l10n_se_hr_payroll`, `payroll` |
| `l10n_se_payroll_growth_support` | uninstalled | uninstalled | uninstalled | `l10n_se_hr_payroll`, `payroll` |
| `l10n_se_payroll_sn_report` | uninstalled | uninstalled | uninstalled | `l10n_se_hr_payroll` |
| `l10n_se_payroll_taxtable` | uninstalled | uninstalled | uninstalled | `l10n_se_hr_payroll` |
| `l10n_se_hr_holidays` | uninstalled | uninstalled | uninstalled | `l10n_se_hr_payroll`, `hr_work_entry_holidays` (klass 3, 20.0) |
| `l10n_se_hr_holidays_account` | uninstalled | uninstalled | uninstalled | `l10n_se_hr_holidays` |
| `l10n_se_arbetsgivarintyg` | uninstalled | uninstalled | uninstalled | `l10n_se_hr_payroll` |
| `l10n_se_payroll_demo` | uninstalled | uninstalled | uninstalled | `l10n_se_demo_company` (klass 2), `l10n_se_hr_payroll_account` |
| `l10n_se_resource_calendar_leaves_import` | uninstalled | uninstalled | uninstalled | `cron_tick` (uppströms), `ics_import_holidays` |

### Blockerarklasser

En blockerare är inte "något som fattas i vår kod". Klassningen avgör vem som
äger åtgärden:

| Klass | Betydelse | Exempel |
|---|---|---|
| **1** | Grenen finns men innehållet är en tomstubbe | `payroll` (OCA/payroll 20.0: **0 moduler**), `hr_timesheet_sheet` (OCA/timesheet 20.0 saknar modulen) |
| **2** | Gren eller modul saknas | `payroll_account`, `l10n_se_demo_company` |
| **3** | Kärnmodul borttagen eller ersatt | `hr_contract` → `hr.version`; `hr_work_entry_contract` → in i `hr_work_entry`; `hr_work_entry_holidays` (borta i 20.0) |

### Miljöfel utanför detta repo

Dessa blockerar installation men ägs inte av `odoo-l10n_se_payroll`:

| Modul | Repo | Fel |
|---|---|---|
| `cron_tick` | `odoo-base` (19.0) | `type='json'` borttaget i 19.0 → ImportError. Blockerar `account_fiscal_year_vrtl` → `l10n_se_hr_payroll` |
| `hr_payroll_employeefund` | `odoo-payroll` (19.0) | kraschar vid laddning |
| `payroll_driving_record` | `odoo-payroll` (19.0) | `security/ir_rule.xml` ParseError |
| `communication_center_sip` | (20.0) | `res_users_views.xml` ParseError |
| `payroll` | `OCA/payroll` | 20.0-grenen är tom (0 moduler) — klass 1 |
| `hr_timesheet_sheet` | `OCA/timesheet` | saknas i 20.0-grenen — klass 1 |

### Vad som bevisats

`hr_leave_dashboard` och `hr_work_anniversary_reminder` är installerade i alla
tre utgåvor. De bevisar att p-fils-arbetet och `hr_contract` → `hr.version`-
migreringen fungerar. Resten är blockerat av beroenden som inte är våra.

Två riktiga buggar hittades och fixades på vägen:

- `hr_work_anniversary_reminder` hade `<odoo><data>` i två XML-filer. Den
  strukturen är **ogiltig även i 18.0** — modulen hade aldrig kunnat
  installeras. Wrappern är borttagen (giltigt i alla utgåvor).
- Samma moduls `subject`-fält innehöll `<t t-out="..."/>`, vilket RelaxNG-
  schemat inte tillåter i ett textfält. Personaliseringen finns kvar i
  `body_html`.

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
