#!/usr/bin/env python3
"""Extract Tiichri 2022 into quarterly payloads, shifted to 2024.

Tiichri is course material: seven employees, twelve months, verified
against external facit PDFs. Using its numbers for 2024 makes the facit
usable as a reference for the demo, which is the whole point of calling
2024 the anchor year.

What is read from the Tiichri XML:
- wages and contract terms per employee
- payslip inputs per month (bonus, overtime, mileage, net deductions)
- leaves per employee and month

What is written: data/payslips/2024qN.json.gz in the same shape
generate_payroll_data.py produces, so the loader does not care where the
data came from.
"""
import calendar
import gzip
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, 'data', 'payslips')
TIICHRI = os.path.join(
    os.path.dirname(HERE), 'l10n_se_hr_payroll_tiichri', 'data')

SOURCE_YEAR = 2022
TARGET_YEAR = 2024

# Tiichri employee xmlid suffix -> demo employee xmlid in demo_company
EMPLOYEE_MAP = {
    'asse': 'emp_asse',
    'camilla': 'emp_camilla',
    'doris': 'emp_doris',
    'frans': 'emp_frans',
    'gustav': 'emp_gustav',
    'helmer': 'emp_helmer',
    'karin': 'emp_karin',
}

# Contract structure: the hourly paid ones use arb_tim
HOURLY = {'helmer', 'karin'}

# Tiichri references the Swedish leave types from l10n_se_hr_payroll. They
# carry the work entry type codes the salary rules match on (sjk, vab, tjl,
# f_led) — Odoo's own types use LEAVE90/LEAVE110 and would never match.
LEAVE_TYPE_MAP = {
    'leave_type_sick': 'l10n_se_hr_payroll.leave_type_sick',
    'leave_type_vab': 'l10n_se_hr_payroll.leave_type_vab',
    'leave_type_parental': 'l10n_se_hr_payroll.leave_type_f_led',
    'leave_type_holiday': 'l10n_se_hr_payroll.leave_type_loa',
    'leave_type_unpaid': 'l10n_se_hr_payroll.leave_type_loa',
    'leave_type_tjl': 'l10n_se_hr_payroll.leave_type_loa',
    'leave_type_loa': 'l10n_se_hr_payroll.leave_type_loa',
}


def read_files():
    """All Tiichri demo XML, as one string per file."""
    out = {}
    for name in sorted(os.listdir(TIICHRI)):
        if name.startswith('data_0') and name.endswith('.xml'):
            with open(os.path.join(TIICHRI, name),
                      encoding='utf-8') as handle:
                out[name] = handle.read()
    return out


def parse_contracts(files):
    """Wage and terms per employee, from the contract records."""
    contracts = {}
    for name, text in files.items():
        key = re.search(r'data_\d+_(\w+)\.xml', name)
        if not key:
            continue
        employee = key.group(1)
        if employee not in EMPLOYEE_MAP:
            continue
        wages = re.findall(r'<field name="wage">([\d.]+)</field>', text)
        if not wages:
            continue
        # An employee can have several contracts in the source (a part-time
        # one first, then a full-time one). The one in force for the payslips
        # is the last, which is also the highest wage.
        contracts[employee] = {
            'wage': max(float(w) for w in wages),
            'hourly': employee in HOURLY,
        }
    return contracts


def parse_inputs(files):
    """Payslip inputs per employee and month.

    The XML writes them as <function name="write"> on an already created
    input line: the search finds it by payslip and code, the second value
    carries the amount.
    """
    inputs = {}
    for name, text in files.items():
        key = re.search(r'data_\d+_(\w+)\.xml', name)
        if not key or key.group(1) not in EMPLOYEE_MAP:
            continue
        employee = key.group(1)
        # <function ...> <value search="...ref('hr_payslip_asse_01')..."/> <value eval="{...}"/> </function>
        pattern = re.compile(
            r"ref\('hr_payslip_" + employee +
            r"_(\d+)'\)\), \('code', '=', '(\w+)'\)\]\"/>\s*"
            r'<value eval="(\{[^}]*\})"/>', re.DOTALL)
        for month, code, evald in pattern.findall(text):
            vals = eval(evald, {'__builtins__': {}}, {})
            entry = inputs.setdefault((employee, int(month)), [])
            entry.append({
                'code': code,
                'amount': float(vals.get('amount', 0.0) or 0.0),
                'amount_qty': float(vals.get('amount_qty', 0.0) or 0.0),
            })
    return inputs


def parse_benefits(files):
    """Contract benefits (company car etc) per employee and month.

    Tiichri carries them as hr.contract.benefit with a value and a start
    date; the payslip rule reads the benefit for the month, so the AI
    needs the value per month, not a single number.
    """
    benefits = {}
    for name, text in files.items():
        key = re.search(r'data_\d+_(\w+)\.xml', name)
        if not key or key.group(1) not in EMPLOYEE_MAP:
            continue
        employee = key.group(1)
        for block in re.findall(
                r'<record id="hr_benefit[^"]*" model="hr\.contract\.benefit">'
                r'(.*?)</record>', text, re.DOTALL):
            value = re.search(r'name="value">([\d.]+)<', block)
            start = re.search(r'name="date_start">([^<]+)<', block)
            bname = re.search(r'name="name" ref="[^"]*\.(\w+)"', block)
            if not (value and bname):
                continue
            benefits.setdefault(employee, []).append({
                'code': bname.group(1),
                'value': float(value.group(1)),
                'start': start.group(1) if start else f'{SOURCE_YEAR}-01-01',
            })
    return benefits


def benefit_for_month(entries, month):
    """The benefit value in force for a given month of the source year."""
    if not entries:
        return 0.0
    best = None
    for entry in sorted(entries, key=lambda e: e['start']):
        if int(entry['start'][5:7]) <= month:
            best = entry
    return best['value'] if best else 0.0


def parse_leaves(files):
    """Leaves per employee, as (from, to, type) tuples."""
    leaves = {}
    for name, text in files.items():
        key = re.search(r'data_\d+_(\w+)\.xml', name)
        if not key or key.group(1) not in EMPLOYEE_MAP:
            continue
        employee = key.group(1)
        for block in re.findall(
                r'<record id="hr_leave[^"]*" model="hr\.leave">(.*?)</record>',
                text, re.DOTALL):
            date_from = re.search(r'name="date_from">([^<]+)<', block)
            date_to = re.search(r'name="date_to">([^<]+)<', block)
            ltype = re.search(r'name="holiday_status_id" ref="[^"]*\.(\w+)"',
                              block)
            if not (date_from and date_to):
                continue
            entry = {
                'date_from': date_from.group(1)[:10],
                'date_to': date_to.group(1)[:10],
                'type': ltype.group(1) if ltype else 'leave_type_holiday',
            }
            # Partial-day leaves carry explicit hours and a sick-leave part.
            # Without them the whole day is deducted instead of the hours
            # the employee was actually away.
            hours = re.search(r'name="number_of_hours">([\d.]+)<', block)
            if hours:
                entry['number_of_hours'] = float(hours.group(1))
            # Partial-day leaves are expressed as a clock interval; Odoo
            # derives date_from/date_to from these hours.
            hfrom = re.search(r'name="request_hour_from">([\d.]+)<', block)
            hto = re.search(r'name="request_hour_to">([\d.]+)<', block)
            if hfrom:
                entry['request_hour_from'] = float(hfrom.group(1))
            if hto:
                entry['request_hour_to'] = float(hto.group(1))
            part = re.search(r'name="sick_leave_part">([\d.]+)<', block)
            if part:
                entry['sick_leave_part'] = float(part.group(1))
            leaves.setdefault(employee, []).append(entry)
    return leaves


def shift_date(value, target_year):
    """Move a date to the target year, keeping the weekday.

    Tiichri's leaves sit on specific weekdays — a Friday sick day is a
    Friday sick day. Shifting by the raw year difference (730 days from
    2022 to 2024) moves every date by two weekdays, so a Friday becomes a
    Sunday and Odoo sees no working hours at all.

    Shifting by whole weeks instead keeps the weekday and therefore the
    number of working days a leave covers, which is what the facit depends
    on. The date may move a day or two; the hours do not.
    """
    import datetime

    source = datetime.date.fromisoformat(value)
    same_day = source.replace(year=target_year)
    delta = (same_day - source).days
    whole_weeks = (delta // 7) * 7
    shifted = source + datetime.timedelta(days=whole_weeks)
    return shifted.isoformat()


def month_bounds(year, month):
    last = calendar.monthrange(year, month)[1]
    return f'{year}-{month:02d}-01', f'{year}-{month:02d}-{last:02d}'


def build_quarter(quarter, contracts, inputs, leaves, benefits):
    months = [(quarter - 1) * 3 + m for m in (1, 2, 3)]
    out_months = []
    for month in months:
        payslips = []
        for employee, data in contracts.items():
            emp_inputs = list(inputs.get((employee, month), []))
            if data['hourly']:
                emp_inputs.append({'code': 'timmar', 'amount': 0.0,
                                   'amount_qty': 168.0 if employee == 'helmer'
                                   else 144.0})

            payslips.append({
                'employee': EMPLOYEE_MAP[employee],
                'inputs': emp_inputs,
            })
        start, end = month_bounds(TARGET_YEAR, month)
        pay_day = min(25, calendar.monthrange(TARGET_YEAR, month)[1])
        out_months.append({
            'year': TARGET_YEAR,
            'month': month,
            'run_name': f'Lönekörning {TARGET_YEAR}-{month:02d}',
            'date_from': start,
            'date_to': end,
            'pay_date': f'{TARGET_YEAR}-{month:02d}-{pay_day:02d}',
            'payslips': payslips,
        })

    # Contracts: same wage as Tiichri, one per employee
    out_contracts = []
    for employee, data in contracts.items():
        contract = {
            'employee': EMPLOYEE_MAP[employee],
            'name': employee.capitalize(),
            'wage': data['wage'],
            'structure': 'arb_tim' if data['hourly'] else 'tj_man',
            'date_start': f'{TARGET_YEAR}-01-01',
            'first_contract_date': '2018-04-01',
            'calendar': 'standard',
            'table_number': 30,
            'column_number': 'column1',
            'one_off_tax': 0.57 if employee == 'asse' else 0.34,
        }
        if data['hourly']:
            contract['wage_unit'] = 'hourly'
        # Benefits live on the contract, not on the payslip. Tiichri's
        # values are per month, so the quarter carries the ones in force.
        entries = benefits.get(employee, [])
        if entries:
            # One benefit row, with the value in force at the start of the
            # quarter. Several rows would be summed by the salary rule.
            contract['benefits'] = [{
                'name': 'l10n_se_hr_payroll_benefits.hr_benefit_carbru',
                'desc': 'Tjänstebil',
                'value': benefit_for_month(entries, months[0]),
            }]
        out_contracts.append(contract)

    # Leaves that fall inside this quarter
    out_leaves = []
    for employee, entries in leaves.items():
        for entry in entries:
            shifted_from = shift_date(entry['date_from'], TARGET_YEAR)
            shifted_to = shift_date(entry['date_to'], TARGET_YEAR)
            m = int(shifted_from[5:7])
            if (m - 1) // 3 + 1 != quarter:
                continue
            leave = {
                'employee': EMPLOYEE_MAP[employee],
                'leave_type': LEAVE_TYPE_MAP.get(
                    entry['type'], 'l10n_se_hr_payroll.leave_type_loa'),
                'date_from': shifted_from,
                'date_to': shifted_to,
            }
            if entry.get('number_of_hours'):
                leave['number_of_hours'] = entry['number_of_hours']
            if entry.get('request_hour_from') is not None:
                leave['request_hour_from'] = entry['request_hour_from']
            if entry.get('request_hour_to') is not None:
                leave['request_hour_to'] = entry['request_hour_to']
            out_leaves.append(leave)

    return {
        'metadata': {
            'quarter': f'{TARGET_YEAR}Q{quarter}',
            'tax_table_year': TARGET_YEAR,
            'generator': 'extract_tiichri_anchor.py',
            'note': ('2024 is the Tiichri 2022 anchor year, shifted one '
                     'month-for-month. Wages, inputs and leaves are '
                     "Tiichri's own, so the external facit applies."),
        },
        'contracts': out_contracts,
        'leaves': out_leaves,
        'months': out_months,
    }


def main():
    files = read_files()
    contracts = parse_contracts(files)
    inputs = parse_inputs(files)
    leaves = parse_leaves(files)
    benefits = parse_benefits(files)
    print(f'kontrakt: {len(contracts)}, inputs: {len(inputs)}, '
          f'ledigheter: {sum(len(v) for v in leaves.values())}',
          file=sys.stderr)

    os.makedirs(OUT_DIR, exist_ok=True)
    for quarter in (1, 2, 3, 4):
        payload = build_quarter(quarter, contracts, inputs, leaves, benefits)
        path = os.path.join(OUT_DIR, f'{TARGET_YEAR}q{quarter}.json.gz')
        with gzip.open(path, 'wt', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, separators=(',', ':'))
        n = sum(len(m['payslips']) for m in payload['months'])
        print(f'{TARGET_YEAR}Q{quarter}: {n} payslips, '
              f'{len(payload["leaves"])} leaves', file=sys.stderr)


if __name__ == '__main__':
    main()
