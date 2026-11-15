# odoo-l10n_se_payroll — gren 19.0

> **Denna gren är avsiktligt tom.** Modulerna är INTE portade till Odoo 19.
> Grenen finns så att dev-miljöer (`hansolo19`) kan klona den utan att falla,
> men den påstår ingenting om att koden är portad.

## Baseline

| | |
|---|---|
| Källa | `20.0` |
| Moduler | **24** |
| Grenar i repot | `10.0`, `12.0`, `12.0-porting`, `14.0`, `16.0`, `18.0`, `18.0new_hr`, `20.0`, `8.0`, `l10_se_payroll_taxtable_dev`, `master`, `master10` |

## Moduler

- `hr_leave_dashboard`
- `hr_work_anniversary_reminder`
- `l10n_se_arbetsgivarintyg`
- `l10n_se_hr_holidays`
- `l10n_se_hr_holidays_account`
- `l10n_se_hr_payroll`
- `l10n_se_hr_payroll_account`
- `l10n_se_hr_payroll_ags`
- `l10n_se_hr_payroll_benefits`
- `l10n_se_hr_payroll_bonus_workflow`
- `l10n_se_hr_payroll_collective`
- `l10n_se_hr_payroll_fk`
- `l10n_se_hr_payroll_flex`
- `l10n_se_hr_payroll_kontrolluppgift`
- `l10n_se_hr_payroll_lop`
- `l10n_se_hr_payroll_pension`
- `l10n_se_hr_payroll_tiichri`
- `l10n_se_hr_payroll_tiichri_26`
- `l10n_se_hr_payroll_union`
- `l10n_se_payroll_agd`
- `l10n_se_payroll_fora`
- `l10n_se_payroll_growth_support`
- `l10n_se_payroll_sn_report`
- `l10n_se_payroll_taxtable`

## Blockerare

**7 externa beroenden saknas** i Odoo 19-kärnan och OCA 19.0:

| Beroende | Behövs av |
|---|---|
| `account_period_vrtl` | `l10n_se_hr_payroll` |
| `base_recompute_field` | `l10n_se_hr_payroll` |
| `hr_contract` | `hr_work_anniversary_reminder`, `l10n_se_arbetsgivarintyg`, `l10n_se_hr_payroll_pension`, `l10n_se_hr_payroll_union` … |
| `hr_timesheet_sheet` | `l10n_se_hr_payroll`, `l10n_se_hr_payroll_flex` |
| `hr_work_entry_contract` | `l10n_se_hr_payroll`, `l10n_se_hr_payroll_flex` |
| `payroll` | `l10n_se_hr_payroll`, `l10n_se_hr_payroll_account`, `l10n_se_hr_payroll_ags`, `l10n_se_hr_payroll_kontrolluppgift` … |
| `payroll_account` | `l10n_se_hr_payroll_account` |

### Prioritering

Ett beroende som blockerar många moduler ger mest nytta att lösa först:

- `payroll` — frisläpper **9** modul(er)
- `hr_contract` — frisläpper **5** modul(er)
- `hr_timesheet_sheet` — frisläpper **2** modul(er)
- `hr_work_entry_contract` — frisläpper **2** modul(er)
- `account_period_vrtl` — frisläpper **1** modul(er)

## Nästa steg

Portering sker på `*-pfile`-maskin med versionsagnostisk kod
(`.p.py` / `.p.xml`). Se `/skill:odoo-pfiles`.
