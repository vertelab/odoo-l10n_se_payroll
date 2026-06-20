# l10n_se_hr_payroll_flex — Flextid / Timpott

Svensk flextidsmodul för Odoo, utvecklad av Vertel AB.

## Funktionalitet

| Funktion | Beskrivning |
|----------|-------------|
| **Övertidsdetektion** | Jämför rapporterad tid på veckotidrapporten mot arbetsschema |
| **Undertidsdetektion** | Visar differens när rapporterad tid < schema |
| **Beordrad övertid** | Manager kan markera övertid som beordrad → bonusfaktor (1.5x, 2.0x) |
| **Timpott** | Flexbank med full transaktionshistorik, liknar semesterallokering |
| **Projektkoppling** | Övertidstimmar kopplas till projektet de rapporterades på |
| **Uttag som ledighet** | Flexade timmar → ledighetsansökan → frånvaro på tidrapporten |
| **Uttag som lön** | Anställd ansöker → godkänns → lönekorrigering på nästa lönespec |
| **Flexårsskifte** | Konfigurerbart flexår med överföringsregler |

## Arkitektur

```
Tidrapport (hr_timesheet_sheet)
    │
    ├─ Rapporterad tid (account.analytic.line)
    ├─ Schema (resource.calendar)
    │
    ▼
Flextidsberäkning (denna modul)
    │
    ├─ Övertid/Undertid → hr.flex.bank.line
    ├─ Beordrad övertid → bonusfaktor
    │
    ▼
Timpott (hr.flex.bank)
    │
    ├─ Uttag som ledighet → hr.leave
    └─ Uttag som lön → hr.payroll.correction → lönespec
```

## Design

Se [PLAN.md](./PLAN.md) för full teknisk designspecifikation.

## Status

🚧 Under utveckling — se [PLAN.md](./PLAN.md) för implementationssteg.
