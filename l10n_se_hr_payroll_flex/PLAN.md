# Flextidsmodul — Teknisk Designplan
## `l10n_se_hr_payroll_flex`

### 🎯 Syfte
Komplett svensk flextidshantering för Odoo, integrerad med tidrapportering
(OCA `hr_timesheet_sheet`) och lönesystemet (`l10n_se_hr_payroll`).

---

## 1. Arkitekturöversikt

```
┌─────────────────────────────────────────────────────────────────┐
│                   hr_timesheet_sheet (OCA)                       │
│  Tidrapport: anställd rapporterar tid per dag/projekt           │
│  Schema från resource.calendar → förväntad arbetstid/vecka      │
│                         ↓                                       │
│              l10n_se_hr_payroll_flex (NY)                        │
│  • Jämför rapporterad tid ↔ schema → övertid/undertid            │
│  • Beordrad övertid → bonusfaktor (1.5x, 2.0x) → timpott        │
│  • Timpott: intjänande likt semesterallokering                  │
│  • Uttag: ledighet ELLER löneutbetalning                        │
│                         ↓                                       │
│              l10n_se_hr_payroll (befintlig)                      │
│  • Lönekorrigering (hr.payroll.correction) vid utbetalning      │
│  • Löneart för flextidsuttag                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Datamodeller

### 2.1 `hr.flex.bank` — Timpotten (huvudmodell)
*Mönster: liknar `hr.leave.allocation` fast med timmar istället för dagar*

| Fält | Typ | Beskrivning |
|------|-----|-------------|
| `name` | Char | Namn, t.ex "Flextidspott 2026" |
| `employee_id` | Many2one→hr.employee | Anställd |
| `company_id` | Many2one→res.company | Företag |
| `balance_hours` | Float (compute) | Aktuellt saldo (summa line_ids.hours) |
| `accrued_hours` | Float (compute) | Totala intjänade timmar |
| `used_hours` | Float (compute) | Totalt uttagna timmar |
| `date_from` | Date | Pottens startdatum |
| `date_to` | Date | Pottens slutdatum (t.ex. flexår) |
| `max_hours` | Float | Tak för potten (t.ex. 100h) |
| `state` | Selection | draft, active, expired, closed |
| `line_ids` | One2many→hr.flex.bank.line | Transaktioner |
| `overtime_rate` | Float | Default-faktor för övertid (1.0) |
| `ordered_overtime_rate` | Float | Faktor för beordrad övertid (1.5 eller 2.0) |

### 2.2 `hr.flex.bank.line` — Transaktioner i potten
| Fält | Typ | Beskrivning |
|------|-----|-------------|
| `bank_id` | Many2one→hr.flex.bank | Tillhör pott |
| `date` | Date | Transaktionsdatum |
| `hours` | Float | Timmar (positivt = intjäning, negativt = uttag) |
| `transaction_type` | Selection | overtime, ordered_overtime, undertime, leave_taken, salary_payout, adjustment |
| `rate_factor` | Float | Multiplikator (1.0, 1.5, 2.0) |
| `source_sheet_id` | Many2one→hr_timesheet.sheet | Tidrapport som genererade transaktionen |
| `source_leave_id` | Many2one→hr.leave | Ledighetsuttag |
| `source_correction_id` | Many2one→hr.payroll.correction | Lönekorrigering vid utbetalning |
| `note` | Text | Notering |

### 2.3 `hr.flex.request` — Anställds ansökan om uttag
*Mönster: blandning av `hr.leave` och `hr.payroll.correction`*

| Fält | Typ | Beskrivning |
|------|-----|-------------|
| `name` | Char | Beskrivning |
| `employee_id` | Many2one→hr.employee | Anställd |
| `bank_id` | Many2one→hr.flex.bank | Vilken pott |
| `request_type` | Selection | leave (ledighet), salary (lön) |
| `hours` | Float | Antal timmar att ta ut |
| `date_from` | Date | Från-datum (vid ledighet) |
| `date_to` | Date | Till-datum (vid ledighet) |
| `state` | Selection | draft, submitted, approved, rejected, done |
| `approved_by` | Many2one→res.users | Godkänd av |
| `leave_id` | Many2one→hr.leave | Resulterande ledighet |
| `correction_id` | Many2one→hr.payroll.correction | Resulterande lönekorrigering |
| `note` | Text | Notering |

### 2.4 `hr.flex.settings` — Företagsinställningar
*Mönster: `res.config.settings` transient*

| Fält | Typ | Beskrivning |
|------|-----|-------------|
| `flex_enabled` | Boolean | Aktivera flextid |
| `flex_year_start` | Date | Flexårets start (t.ex. 1 april) |
| `default_overtime_rate` | Float | Standardfaktor (1.0 = timme för timme) |
| `ordered_overtime_rate` | Float | Beordrad övertid (1.5 = +50%) |
| `max_bank_hours` | Float | Max timmar i potten |
| `allow_salary_payout` | Boolean | Tillåt utbetalning som lön |
| `salary_payout_rule_id` | Many2one→hr.salary.rule | Löneart för utbetalning |

---

## 3. Utökningar av befintliga modeller

### 3.1 `hr_timesheet.sheet` (extends)
```python
# Nya fält på tidrapporten
overtime_hours = fields.Float(compute='_compute_overtime')
undertime_hours = fields.Float(compute='_compute_overtime')
expected_hours = fields.Float(compute='_compute_overtime')
flex_bank_line_ids = fields.One2many('hr.flex.bank.line', 'source_sheet_id')
is_overtime_ordered = fields.Boolean(string='Beordrad övertid')

# Overtime visas som extra rader i matrisen
# Hook: _matrix_key_attributes() → lägg till 'is_overtime'
```

**Beräkning av övertid:**
1. Hämta anställds schema (`resource.calendar`) → förväntad arbetstid/vecka
2. Summera rapporterad tid från `timesheet_ids` (account.analytic.line)
3. Dra bort frånvarotid (sjuk, semester etc)
4. `overtime_hours = max(0, reported - expected)`
5. `undertime_hours = max(0, expected - reported)`

### 3.2 `hr.payslip` (extends)
```python
flex_payout_hours = fields.Float(compute='_compute_flex_payout')

def _apply_flex_payouts(self):
    """Applicera godkända flextids-utbetalningar som lönekorrigeringar"""
    for slip in self:
        requests = self.env['hr.flex.request'].search([
            ('employee_id', '=', slip.employee_id.id),
            ('request_type', '=', 'salary'),
            ('state', '=', 'approved'),
        ])
        for req in requests:
            correction = self.env['hr.payroll.correction'].create({...})
            correction._apply_to_payslip(slip)
            req.state = 'done'
```

### 3.3 `hr.employee` (extends)
```python
flex_bank_ids = fields.One2many('hr.flex.bank', 'employee_id')
flex_balance_hours = fields.Float(compute='_compute_flex_balance')
```

### 3.4 `hr.contract` (extends)
```python
flex_overtime_rate = fields.Float(default=1.0)
flex_ordered_overtime_rate = fields.Float(default=1.5)
```

---

## 4. Gränssnitt / Vyer

### 4.1 Tidrapport — förbättrad matris
- Ny kolumn/sektion: **Övertid/Undertid**
- Visar differensen per dag mot schema
- **"Beordra övertid"**-knapp för manager → ändrar rate_factor
- **Projekt-koppling**: övertidstimmar kan knytas till projekt precis som vanlig tid
- Färgkodning: grönt = flextid+, rött = undertid, blått = beordrad

### 4.2 Timpott-vy (form)
- Sammanställning per anställd: saldo, intjänat, uttaget
- Transaktionshistorik (line_ids)
- Knappar: "Ta ut som ledighet", "Ta ut som lön"

### 4.3 Anställds vy
- Ny flik: **Flextid** — visar aktuell pott, historik
- Nytt fält i headern: **Flexsaldo: +12.5h**

### 4.4 Ansökningsvy
- Wizard: "Ansök om flextidsuttag"
  - Välj typ: Ledighet / Löneutbetalning
  - Antal timmar
  - Datum (vid ledighet)
  - Orsak/notering

---

## 5. Flöde / Tillståndsmaskin

### 5.1 Intjäning (automatisk)
```
Tidrapport skapas → anställd fyller i tid
  → Rapporterad tid > Schema: övertid
     → Är beordrad? 
        JA → timmar × 1.5 (eller 2.0) → Timpott
        NEJ → timmar × 1.0 → Timpott
  → Rapporterad tid < Schema: undertid
     → Differens dras från Timpott
  → Vid godkännande av tidrapport (state=done):
     → Transaktioner låses
```

### 5.2 Uttag som ledighet
```
Anställd → Ansök om flextid som ledighet (hr.flex.request)
  → Chef godkänner
  → hr.leave skapas (kopplas till flex bank line)
  → Timpott debiteras
  → Tidrapporten visar frånvaron
```

### 5.3 Uttag som lön
```
Anställd → Ansök om utbetalning (hr.flex.request, type=salary)
  → Chef godkänner
  → hr.payroll.correction skapas (pending)
  → Vid nästa lönekörning: correction appliceras på lönespec
  → Timpott debiteras
  → Transaktion markeras som done
```

### 5.4 Flexårsskifte (likt semesterår)
```
Vid flexårsslut (config.flex_year_end):
  → Aktiv pott stängs (state=expired)
  → Ny pott skapas för nästa år
  → Eventuellt överskott hanteras enligt regler:
     • Överförs till nya potten (upp till max_hours)
     • Överskjutande betalas ut ELLER fryser inne
```

---

## 6. Lönearts-struktur

Nya löneartskoder att definiera i `hr_salary_rule_data.xml`:

| Kod | Namn | Typ |
|-----|------|-----|
| `FLEXP` | Flextidsuttag, lön | Tillägg (brutto) |
| `FLEXN` | Flextidsuttag, nettolöneavdrag | Avdrag (netto) |
| `FLEXR` | Flextidsreglering (årsskifte) | Korrigering |
| `OT01` | Övertid, enkel (beordrad) | Tillägg |
| `OT02` | Övertid, kval (beordrad) | Tillägg |

---

## 7. Beroenden & Kompatibilitet

### 7.1 Hårda beroenden
```
l10n_se_hr_payroll              (lön, lönekorrigeringar)
hr_timesheet_sheet (OCA)        (tidrapportering)
hr_work_entry_contract (OCA)    (schema mot kontrakt)
```

### 7.2 Mjuka beroenden
```
l10n_se_hr_holidays             (semester som frånvarotyp)
l10n_se_hr_payroll_benefits     (förmånsvärde på flextid?)
l10n_se_hr_payroll_collective   (kollektivavtal kan påverka övertidsregler)
hr_timesheet_sheet_attendance   (stämplingstid jämfört med rapporterad tid)
```

---

## 8. Filstruktur

```
l10n_se_hr_payroll_flex/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── hr_flex_bank.py              # hr.flex.bank + hr.flex.bank.line
│   ├── hr_flex_request.py           # hr.flex.request
│   ├── hr_flex_settings.py          # res.config.settings
│   ├── hr_employee.py               # extends hr.employee
│   ├── hr_contract.py               # extends hr.contract
│   ├── hr_timesheet_sheet.py        # extends hr_timesheet.sheet
│   └── hr_payslip.py                # extends hr.payslip
├── data/
│   ├── hr_flex_data.xml             # Demo/init-data (löneartskoder etc)
│   └── hr_salary_rule_data_flex.xml # Löneartskoder
├── security/
│   ├── ir.model.access.csv
│   └── hr_flex_security.xml         # Grupp: flex_user, flex_manager
├── views/
│   ├── hr_flex_bank_views.xml       # Timpott formulär + lista
│   ├── hr_flex_request_views.xml    # Ansökan formulär
│   ├── hr_employee_views.xml        # Utökad anställd-vy
│   ├── hr_timesheet_sheet_views.xml # Utökad tidrapport
│   ├── hr_contract_views.xml        # Kontraktsinställningar
│   └── res_config_settings_views.xml# Företagsinställningar
├── wizard/
│   └── hr_flex_request_wizard.py    # Wizard för ansökan
├── report/
│   └── hr_flex_report.xml           # Flexsaldo-rapport
├── static/
│   └── description/
│       ├── banner.png
│       └── icon.png
├── tests/
│   ├── __init__.py
│   └── test_flex_bank.py
└── i18n/
    └── sv_SE.po
```

---

## 9. Jämförelse — Hur gör andra?

### Odoo Enterprise
Odoo EE har **ingen** inbyggd flextidsmodul. Det som finns är:
- **Time Off** (`hr_holidays`) — endast frånvarohantering, inget övertidssaldo
- **Timesheets** — rapporterar tid men beräknar inte övertid mot schema
- **Attendances** — stämpling men ingen koppling till flextidspott

EE-användare som behöver flextid köper tredjepartsmoduler eller bygger eget.

### Fortnox Lön
- **Flexbank**: separat saldo per anställd
- Övertid sparas i flexbank med faktor (1.5x, 2x)
- Uttag: ledighet (reducerar flexbank) eller utbetalning (nollställer)
- Tydlig separation: **komptid** (ledighet), **övertidsersättning** (pengar)

### Visma Lön
- **Tidbank**: ackumulerar +/– tid
- Brytpunkt vid 100h (enligt kollektivavtal)
- Automatisk utbetalning över brytpunkt
- **Beordrad övertid**: separat ersättningsnivå

### Hogia Lön
- **Arbetstidskonto**: flexram ±40h (standard), går att konfigurera
- Tydlig koppling till kollektivavtal (ITP, SAF-LO etc)
- **Övertidsersättning**: enkel/kval, med/utan beordring

---

## 10. Implementation — Steg-för-steg

| Fas | Aktivitet | Prioritet |
|-----|-----------|-----------|
| **1** | Skapa `__manifest__.py` med korrekta beroenden | 🔴 Omgående |
| **2** | Implementera `hr.flex.bank` + `hr.flex.bank.line` modeller | 🔴 Kärnan |
| **3** | Implementera `hr.flex.request` modell med tillståndsmaskin | 🔴 Kärnan |
| **4** | Skapa säkerhetsregler (`ir.model.access.csv`) | 🔴 Säkerhet |
| **5** | Utöka `hr_timesheet.sheet` — övertidsberäkning | 🟡 Efter kärna |
| **6** | Utöka `hr.payslip` — applicera flextids-utbetalningar | 🟡 Efter kärna |
| **7** | Utöka `hr.employee` + `hr.contract` | 🟡 Efter kärna |
| **8** | Bygg vyer: tidrapport-förbättring, timpott, ansökan | 🟢 GUI |
| **9** | Wizard för ansökan om uttag | 🟢 GUI |
| **10** | Företagsinställningar (`res.config.settings`) | 🟢 GUI |
| **11** | Löneartskoder (datafiler) | 🟢 Data |
| **12** | Flexårsskifte — automatiserad cron/action | 🔵 Finess |
| **13** | Tester (`tests/`) | 🔵 QA |
| **14** | Svensk översättning (`sv_SE.po`) | 🔵 i18n |
| **15** | Dokumentation (denna plan → README) | 🔵 Docs |

---

## 11. Designbeslut & Rekommendationer

### Varför `hr.flex.bank` istället för att återanvända `hr.leave.allocation`?
- Semestern är dag-baserad, flextid är **tim-baserad**
- Flextid har **olika rate factors** (1.0, 1.5, 2.0) — semestern har inte det
- Flextid kan **betalas ut som lön** — semestern följer semesterlagens komplicerade regler
- Separat modell = renare kod, färre edge cases

### Varför `hr.flex.request` istället för att direkt skapa `hr.leave` / `hr.payroll.correction`?
- Ansökan → godkännande-flöde speglar svensk arbetsrätt (chef måste godkänna)
- Spårbarhet: vem godkände, när
- Möjlighet att neka med motivering

### Hur knyts övertid till projekt?
- Vid tidrapportering: användaren väljer projekt+tidsåtgång som vanligt
- Om total tid för en dag överstiger schemat → överskottet flaggas som övertid
- Övertidstimmar kopplas automatiskt till det projekt där de registrerades
- På lönearten: löneart OT01/OT02 kopplas till kostnadsställe/projekt från tidrapporten
