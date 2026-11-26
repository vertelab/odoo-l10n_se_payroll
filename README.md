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
| `l10n_se_hr_payroll` | installed | **installed** | uninstalled | migrerad |
| `l10n_se_hr_payroll_benefits` | uninstalled | **installed** | uninstalled | migrerad |
| `l10n_se_hr_payroll_collective` | uninstalled | **installed** | uninstalled | migrerad |
| `l10n_se_hr_payroll_fk` | uninstalled | uninstalled | uninstalled | `l10n_se_hr_payroll` |
| `l10n_se_hr_payroll_lop` | uninstalled | uninstalled | uninstalled | `l10n_se_hr_payroll` |
| `l10n_se_hr_payroll_bonus_workflow` | uninstalled | uninstalled | uninstalled | `l10n_se_hr_payroll` |
| `l10n_se_hr_payroll_tiichri` | uninstalled | uninstalled | uninstalled | `l10n_se_hr_payroll_benefits` |
| `l10n_se_hr_payroll_tiichri_26` | uninstalled | uninstalled | uninstalled | `l10n_se_hr_payroll_tiichri` |
| `l10n_se_hr_payroll_account` | uninstalled | uninstalled | uninstalled | `l10n_se_hr_payroll`, `payroll_account` (klass 2) |
| `l10n_se_hr_payroll_ags` | uninstalled | uninstalled | uninstalled | `l10n_se_hr_payroll`, `payroll` |
| `l10n_se_hr_payroll_pension` | uninstalled | uninstalled | uninstalled | migrerad; `l10n_se_hr_payroll` → `cron_tick` |
| `l10n_se_hr_payroll_union` | uninstalled | **installed** | uninstalled | migrerad |
| `l10n_se_hr_payroll_flex` | uninstalled | **installed** | uninstalled | migrerad |
| `l10n_se_hr_payroll_kontrolluppgift` | uninstalled | uninstalled | uninstalled | `l10n_se_hr_payroll`, `payroll` |
| `l10n_se_payroll_agd` | uninstalled | uninstalled | uninstalled | `l10n_se_hr_payroll`, `payroll` |
| `l10n_se_payroll_fora` | uninstalled | uninstalled | uninstalled | `l10n_se_hr_payroll`, `payroll` |
| `l10n_se_payroll_growth_support` | uninstalled | uninstalled | uninstalled | `l10n_se_hr_payroll`, `payroll` |
| `l10n_se_payroll_sn_report` | uninstalled | **installed** | uninstalled | migrerad |
| `l10n_se_payroll_taxtable` | uninstalled | uninstalled | uninstalled | migrerad; `l10n_se_hr_payroll` → `cron_tick` |
| `l10n_se_hr_holidays` | uninstalled | **installed** | uninstalled | migrerad |
| `l10n_se_hr_holidays_account` | uninstalled | uninstalled | uninstalled | `l10n_se_hr_holidays` |
| `l10n_se_arbetsgivarintyg` | uninstalled | **installed** | uninstalled | migrerad |
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
| `cron_tick` | `odoo-base` (19.0) | `views/cron_task_views.xml` har `<group expand="0">` i `<search>`. Attributet togs bort i 19.0 (`common.rng`) → `RELAXNG_ERR_INVALIDATTR`, ParseError. Blockerar `account_fiscal_year_vrtl` → `l10n_se_hr_payroll` → alla 24 löpande moduler. **Hård blockerare.** |
| `hr_payroll_employeefund` | `odoo-payroll` (19.0) | kraschar vid laddning |
| `payroll_driving_record` | `odoo-payroll` (19.0) | `security/ir_rule.xml` ParseError |
| `communication_center_sip` | (20.0) | `res_users_views.xml` ParseError |
| `payroll` | `OCA/payroll` | 20.0-grenen är tom (0 moduler) — klass 1 |
| `odoo-l10n_se` | `vertelab/odoo-l10n_se` | **19.0-grenen är 18.0-kod** — 0 p-filer, alla manifest säger `18.0.x`. Blockerar `l10n_se_payroll_agd` → `_fora`, `_ags`, `_pension`, `_kontrolluppgift` |
| `hr_timesheet_sheet` | `OCA/timesheet` | saknas i 20.0-grenen — klass 1 |

### `expand` på `<group>` i `<search>`

Attributet finns i 18.0 och togs bort i **19.0** (`common.rng`). Åtta av våra
egna vyer bar det; de är nu p-filade så att `expand="0"` bara emitteras för
18.0. Samma fel finns kvar i externa moduler (`cron_tick` i `odoo-base`,
`account_billing`, `account_commodity_price`, …) och är därför en
systemomfattande uppströmsfråga.

### Fältdiff — vad som flyttade i 19.0

Migrationen krävde mer än modellnamnet. Verifierat mot kärnkällan:

| 18.0 | 19.0 | Åtgärd |
|---|---|---|
| `hr.employee.contract_id` | `current_version_id` | döps |
| `hr.employee.contract_ids` | `version_ids` | döps |
| `hr.employee.gender` | **borttagen** | könräkning nollställs, related-fält villkoras bort |
| `hr.contract.state` | `is_current` / `is_past` / `is_future` | tidsbaserat |
| `hr.contract.first_contract_date` | `hr.version.date_start` | härleds |
| `account.account.deprecated` | **borttagen** | domän töms |
| `odoo.addons.decimal_precision` | **borttagen** | död import villkoras bort |
| `<group expand="0" string="...">` i `<search>` | **båda attributen borta** | villkoras |
| `<odoo><data>` | ogiltigt i alla utgåvor | wrappern borttagen |

### `account_codes_formula` — kommalistor fungerar inte

`account_codes_formula` är ett **kärnfält** i 19.0 (`account.report.line`), och
kärnans `_check_formula` godkänner bara `+`/`-`, inte kommalistor. Två rader i
`account_dynamic_reports/data/balance_sheet.xml` använde `16,17,18` och
`10,11,12`; de är ändrade till `16+17+18` och `10+11+12` — samma fix som redan
fanns på 20.0-grenen (commit `41f92af1`).

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
