#!/usr/bin/env python3
"""Generate the payroll demo data, one JSON file per quarter.

2023Q4..2027Q4. The shape is what l10n_se_payroll_demo reads:
contracts, leaves and months, each month carrying its payslips and inputs.

The timeline follows the plan in l10n-se-demo-datasets:

    2023Q4  7 employees (the Tiichri seven)
    2024    + Oskar Lindvall hired in Q3
    2025    + Petra Sandell hired in Q1, Frans Filipsson retires in Q4
    2026    Gustav Groth resigns in Q2
    2027    future — same shape, no payments

Wages rise each year. The variations the plan asks for (sickness,
parental leave, holiday, bonus, overtime, company car, wellness grant,
salary exchange, part-time) are spread across the quarters.

2024 is the anchor year: the inputs are Tiichri 2022's, shifted to 2024.
That makes the external facit usable as a reference.
"""
import calendar
import gzip
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, 'data', 'payslips')

QUARTERS = [(2023, 4)] + [
    (year, quarter)
    for year in (2024, 2025, 2026, 2027)
    for quarter in (1, 2, 3, 4)
]

# The seven from Tiichri, plus the two hired along the timeline.
EMPLOYEES = [
    {
        'employee': 'emp_asse', 'name': 'Asse Aronsson',
        'wage': 52000, 'structure': 'tj_man', 'calendar': 'standard',
        'table_number': 30, 'column_number': 'column1',
        'one_off_tax': 0.57, 'first_contract_date': '2018-04-01',
        'wage_exchange_amount': 4000,
        'wage_exchange_start': '2024-03-01', 'wage_exchange_end': '2027-12-31',
    },
    {
        'employee': 'emp_camilla', 'name': 'Camilla Cobolt',
        'wage': 30000, 'structure': 'tj_man', 'calendar': 'standard',
        'table_number': 30, 'column_number': 'column1',
        'one_off_tax': 0.34, 'first_contract_date': '2022-01-10',
    },
    {
        'employee': 'emp_doris', 'name': 'Doris Dahlin',
        'wage': 17600, 'structure': 'tj_man', 'calendar': 'standard',
        'table_number': 30, 'column_number': 'column1',
        'one_off_tax': 0.34, 'first_contract_date': '2019-04-01',
    },
    {
        'employee': 'emp_frans', 'name': 'Frans Filipsson',
        'wage': 20800, 'structure': 'tj_man', 'calendar': 'standard',
        'table_number': 30, 'column_number': 'column1',
        'one_off_tax': 0.34, 'first_contract_date': '2002-01-01',
        # Retires 2025 Q4
        'date_end': '2025-12-31',
    },
    {
        'employee': 'emp_gustav', 'name': 'Gustav Groth',
        'wage': 25000, 'structure': 'tj_man', 'calendar': 'standard',
        'table_number': 30, 'column_number': 'column1',
        'one_off_tax': 0.34, 'first_contract_date': '2011-04-01',
        # Resigns 2026 Q2
        'date_end': '2026-06-30',
    },
    {
        'employee': 'emp_helmer', 'name': 'Helmer Henriksson',
        'wage': 130, 'structure': 'arb_tim', 'calendar': 'standard',
        'table_number': 30, 'column_number': 'column1',
        'one_off_tax': 0.34, 'first_contract_date': '2011-04-01',
        'wage_unit': 'hourly', 'hours_per_month': 168,
    },
    {
        'employee': 'emp_karin', 'name': 'Karin Kullberg',
        'wage': 115, 'structure': 'arb_tim', 'calendar': 'standard',
        'table_number': 30, 'column_number': 'column1',
        'one_off_tax': 0.34, 'first_contract_date': '2022-06-01',
        'wage_unit': 'hourly', 'hours_per_month': 144,
    },
    {
        'employee': 'emp_oskar', 'name': 'Oskar Lindvall',
        'wage': 24000, 'structure': 'tj_man', 'calendar': 'standard',
        'table_number': 30, 'column_number': 'column1',
        'one_off_tax': 0.34, 'first_contract_date': '2024-08-01',
        # Hired 2024 Q3
        'date_start': '2024-08-01',
    },
    {
        'employee': 'emp_petra', 'name': 'Petra Sandell',
        'wage': 32000, 'structure': 'tj_man', 'calendar': 'standard',
        'table_number': 30, 'column_number': 'column1',
        'one_off_tax': 0.34, 'first_contract_date': '2025-01-01',
        # Hired 2025 Q1
        'date_start': '2025-01-01',
    },
]

# Leave type xmlids from hr_holidays.
# hr_holidays ships these; the names are Odoo 18's, not the obvious ones.
LEAVE_TYPES = {
    'sick': 'hr_holidays.holiday_status_sl',        # Sick Time Off
    'parental': 'hr_holidays.hr_holiday_status_dv',  # Parental Leaves
    'holiday': 'hr_holidays.holiday_status_cl',      # Paid Time Off
}

# Annual wage increase, applied from January each year.
WAGE_RAISE = {2024: 1.032, 2025: 1.028, 2026: 1.030, 2027: 1.025}

# Variations spread over the quarters. Key: (year, quarter) -> list of
# (employee, kind, payload).
VARIATIONS = {
    (2023, 4): [
        ('emp_asse', 'bonus', {'amount': 8000.0}),
        ('emp_camilla', 'overtime', {'simple': 4.0, 'qualified': 2.0}),
    ],
    (2024, 1): [
        ('emp_asse', 'bonus', {'amount': 10000.0}),
        ('emp_asse', 'overtime', {'simple': 2.0, 'qualified': 2.0}),
        ('emp_camilla', 'sick', {'days': 5, 'month': 2}),
        ('emp_doris', 'wellness', {'amount': 1500.0}),
    ],
    (2024, 2): [
        ('emp_camilla', 'parental', {'months': [5, 6], 'percent': 1.0}),
        ('emp_helmer', 'overtime', {'simple': 12.0, 'qualified': 4.0}),
    ],
    (2024, 3): [
        ('emp_asse', 'holiday', {'month': 7}),
        ('emp_doris', 'holiday', {'month': 8}),
        ('emp_gustav', 'bonus', {'amount': 5000.0}),
    ],
    (2024, 4): [
        ('emp_karin', 'sick', {'days': 3, 'month': 10}),
        ('emp_asse', 'wellness', {'amount': 2000.0}),
    ],
    (2025, 1): [
        ('emp_petra', 'bonus', {'amount': 6000.0}),
        ('emp_camilla', 'overtime', {'simple': 6.0, 'qualified': 0.0}),
    ],
    (2025, 2): [
        ('emp_doris', 'parental', {'months': [4, 5, 6], 'percent': 0.5}),
        ('emp_helmer', 'sick', {'days': 8, 'month': 5}),
    ],
    (2025, 3): [
        ('emp_asse', 'holiday', {'month': 7}),
        ('emp_petra', 'holiday', {'month': 8}),
        ('emp_gustav', 'overtime', {'simple': 10.0, 'qualified': 3.0}),
    ],
    (2025, 4): [
        ('emp_frans', 'holiday', {'month': 10}),
        ('emp_karin', 'bonus', {'amount': 4000.0}),
    ],
    (2026, 1): [
        ('emp_asse', 'bonus', {'amount': 12000.0}),
        ('emp_doris', 'wellness', {'amount': 1800.0}),
    ],
    (2026, 2): [
        ('emp_gustav', 'sick', {'days': 10, 'month': 4}),
        ('emp_camilla', 'overtime', {'simple': 8.0, 'qualified': 2.0}),
    ],
    (2026, 3): [
        ('emp_asse', 'holiday', {'month': 7}),
        ('emp_helmer', 'holiday', {'month': 8}),
    ],
    (2026, 4): [
        ('emp_petra', 'parental', {'months': [11, 12], 'percent': 1.0}),
        ('emp_karin', 'wellness', {'amount': 1500.0}),
    ],
    (2027, 1): [
        ('emp_asse', 'bonus', {'amount': 10000.0}),
    ],
    (2027, 2): [
        ('emp_doris', 'overtime', {'simple': 5.0, 'qualified': 1.0}),
    ],
    (2027, 3): [
        ('emp_asse', 'holiday', {'month': 7}),
    ],
    (2027, 4): [
        ('emp_camilla', 'bonus', {'amount': 7000.0}),
    ],
}


def month_bounds(year, month):
    last = calendar.monthrange(year, month)[1]
    return f'{year}-{month:02d}-01', f'{year}-{month:02d}-{last:02d}'


def wage_for(employee, year):
    """The employee's monthly wage in a given year."""
    wage = employee['wage']
    base_year = 2023
    for y in range(base_year + 1, year + 1):
        wage *= WAGE_RAISE.get(y, 1.0)
    return round(wage, 2)


def employed_in(employee, year, month):
    start = employee.get('date_start', '2000-01-01')
    end = employee.get('date_end')
    first = f'{year}-{month:02d}-01'
    if first < start:
        return False
    if end and first > end:
        return False
    return True


def build_contracts(year, quarter):
    """Contracts active in the quarter, with this year's wage."""
    out = []
    months = [(quarter - 1) * 3 + m for m in (1, 2, 3)]
    for emp in EMPLOYEES:
        if not any(employed_in(emp, year, m) for m in months):
            continue
        data = {
            'employee': emp['employee'],
            'name': emp['name'],
            'wage': wage_for(emp, year),
            'structure': emp['structure'],
            'date_start': emp.get('date_start', '2000-01-01'),
            'first_contract_date': emp.get('first_contract_date'),
            'calendar': emp['calendar'],
            'table_number': emp['table_number'],
            'column_number': emp['column_number'],
            'one_off_tax': emp['one_off_tax'],
        }
        if emp.get('date_end'):
            data['date_end'] = emp['date_end']
        if emp.get('wage_unit') == 'hourly':
            data['wage_unit'] = 'hourly'
        for key in ('wage_exchange_amount', 'wage_exchange_start',
                    'wage_exchange_end'):
            if emp.get(key):
                data[key] = emp[key]
        out.append(data)
    return out


def build_leaves(year, quarter):
    """Leaves that fall inside the quarter."""
    out = []
    for (vy, vq), entries in VARIATIONS.items():
        if (vy, vq) != (year, quarter):
            continue
        for emp_id, kind, payload in entries:
            if kind == 'sick':
                m = payload.get('month')
                days = payload['days']
                start, _ = month_bounds(year, m)
                end_day = min(days, calendar.monthrange(year, m)[1])
                out.append({
                    'employee': emp_id,
                    'leave_type': LEAVE_TYPES['sick'],
                    'date_from': start,
                    'date_to': f'{year}-{m:02d}-{end_day:02d}',
                    'days': days,
                })
            elif kind == 'parental':
                for m in payload['months']:
                    if (m - 1) // 3 + 1 != quarter:
                        continue
                    start, end = month_bounds(year, m)
                    out.append({
                        'employee': emp_id,
                        'leave_type': LEAVE_TYPES['parental'],
                        'date_from': start,
                        'date_to': end,
                        'percent': payload['percent'],
                    })
            elif kind == 'holiday':
                m = payload['month']
                if (m - 1) // 3 + 1 != quarter:
                    continue
                start, end = month_bounds(year, m)
                out.append({
                    'employee': emp_id,
                    'leave_type': LEAVE_TYPES['holiday'],
                    'date_from': start,
                    'date_to': end,
                    'days': calendar.monthrange(year, m)[1],
                })
    return out


def build_month(year, quarter, month):
    """One month's payslips with their inputs."""
    payslips = []
    for emp in EMPLOYEES:
        if not employed_in(emp, year, month):
            continue
        inputs = []
        for (vy, vq), entries in VARIATIONS.items():
            if (vy, vq) != (year, quarter):
                continue
            for emp_id, kind, payload in entries:
                if emp_id != emp['employee']:
                    continue
                if kind == 'bonus' and month == (quarter - 1) * 3 + 1:
                    inputs.append({'code': 'bonus',
                                   'amount': payload['amount'],
                                   'amount_qty': 1.0})
                elif kind == 'overtime' and month == (quarter - 1) * 3 + 2:
                    if payload.get('simple'):
                        inputs.append({'code': 'otidtim',
                                       'amount_qty': payload['simple']})
                    if payload.get('qualified'):
                        inputs.append({'code': 'kvaltim',
                                       'amount_qty': payload['qualified']})
                elif kind == 'wellness' and month == (quarter - 1) * 3 + 3:
                    inputs.append({'code': 'friskvard',
                                   'amount': payload['amount'],
                                   'amount_qty': 1.0})
        if emp.get('wage_unit') == 'hourly':
            inputs.append({'code': 'timmar',
                           'amount_qty': emp.get('hours_per_month', 160)})
        payslips.append({'employee': emp['employee'], 'inputs': inputs})

    start, end = month_bounds(year, month)
    pay_day = min(25, calendar.monthrange(year, month)[1])
    return {
        'year': year,
        'month': month,
        'run_name': f'Lönekörning {year}-{month:02d}',
        'date_from': start,
        'date_to': end,
        'pay_date': f'{year}-{month:02d}-{pay_day:02d}',
        'payslips': payslips,
    }


def build_quarter(year, quarter):
    months = [(quarter - 1) * 3 + m for m in (1, 2, 3)]
    return {
        'metadata': {
            'quarter': f'{year}Q{quarter}',
            'tax_table_year': min(year, 2026),
            'generator': 'generate_payroll_data.py',
            'note': ('2027 uses the 2026 tax table until Skatteverket '
                     'publishes the 2027 one' if year == 2027 else ''),
        },
        'contracts': build_contracts(year, quarter),
        'leaves': build_leaves(year, quarter),
        'months': [build_month(year, quarter, m) for m in months],
    }


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    total = 0
    for year, quarter in QUARTERS:
        payload = build_quarter(year, quarter)
        path = os.path.join(OUT_DIR, f'{year}q{quarter}.json.gz')
        with gzip.open(path, 'wt', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, separators=(',', ':'))
        n = sum(len(m['payslips']) for m in payload['months'])
        total += n
        print(f'{year}Q{quarter}: {len(payload["contracts"])} contracts, '
              f'{n} payslips, {len(payload["leaves"])} leaves',
              file=sys.stderr)
    print(f'totalt {total} payslips', file=sys.stderr)


if __name__ == '__main__':
    main()
