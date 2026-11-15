"""Payroll demo: turn a quarter's JSON into payslips, entries and payments.

Three steps per quarter, in this order:

    contracts   hr.contract (one per employee and wage period)
    leaves      hr.leave, validated — the salary rules read them
    payslips    hr.payslip.run per month + hr.payslip per employee

The payslips are computed after they exist, because compute_sheet() reads
the leaves through get_worked_day_lines(). Marking them done posts the
entry (OCA payroll_account), and the net wage is then paid from the bank
so the wage liability is settled — the same shape as the accounting demo.

The accounts on the salary rules and the structure itself are set up in
hr_payslip_setup.py, once, before the first quarter is loaded.
"""
import logging
from datetime import date, timedelta

from odoo import api, models

from .demo_dataset import LOADER_VERSION, read_quarter
from .hr_payslip_setup import BANK_ACCOUNT, NET_WAGE_ACCOUNT

_logger = logging.getLogger(__name__)


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    # ------------------------------------------------------------------
    # Periods
    # ------------------------------------------------------------------

    @api.model
    def _payroll_demo_period(self, year, month):
        """The accounting period for a month, created if the module has them."""
        if 'account.period' not in self.env.registry:
            return self.env['account.period']
        company = self._payroll_demo_company()
        start = date(year, month, 1)
        end = date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)
        Period = self.env['account.period']
        period = Period.search([
            ('date_start', '<=', start),
            ('date_stop', '>=', start),
            ('company_id', 'in', [False, company.id]),
        ], limit=1)
        if period:
            return period
        fiscal_year = self.env['account.fiscal.year'].search([
            ('date_from', '<=', start),
            ('date_to', '>=', start),
            ('company_id', '=', company.id),
        ], limit=1)
        if not fiscal_year:
            fiscal_year = self.env['account.fiscal.year'].create({
                'name': str(year),
                'date_from': date(year, 1, 1),
                'date_to': date(year, 12, 31),
                'company_id': company.id,
            })
        # account.period _inherits date.range, and date.range.type_id is
        # required — a period cannot be created without its range type.
        range_type = self.env['date.range.type'].search([
            ('name', '=', 'Lönemånad'),
            ('company_id', '=', company.id),
        ], limit=1)
        if not range_type:
            range_type = self.env['date.range.type'].create({
                'name': 'Lönemånad',
                'allow_overlap': False,
                'company_id': company.id,
            })
        date_range = self.env['date.range'].create({
            'name': f'{month:02d}/{year}',
            'type_id': range_type.id,
            'date_start': start,
            'date_end': end,
            'company_id': company.id,
        })
        return Period.create({
            'name': f'{month:02d}/{year}',
            'date_range_id': date_range.id,
            'fiscalyear_id': fiscal_year.id,
            'company_id': company.id,
        })

    # ------------------------------------------------------------------
    # Loading one quarter
    # ------------------------------------------------------------------

    @api.model
    def _payroll_demo_load_quarter(self, dataset):
        """Load the payroll for one demo.dataset row. Returns the count."""
        payload = read_quarter(dataset)
        if payload is None:
            return 0
        _logger.warning('payroll_demo: LOADER %s loading %s (%s months)',
                        LOADER_VERSION, dataset.name,
                        len(payload.get('months', [])))

        company = self._payroll_demo_company()
        self._payroll_demo_set_rule_accounts()
        contracts = self._payroll_demo_create_contracts(payload, company)
        self._payroll_demo_create_leaves(payload, company)

        count = 0
        for month in payload.get('months', []):
            count += self._payroll_demo_load_month(month, contracts, company)
        _logger.info('payroll_demo: %s loaded, %s payslips', dataset.name, count)
        return count

    @api.model
    def _payroll_demo_create_contracts(self, payload, company):
        """Create the contracts of the quarter. Returns {employee: contract}."""
        Contract = self.env['hr.contract']
        by_employee = {}
        for data in payload.get('contracts', []):
            employee = self._payroll_demo_employee(data['employee'])
            structure = self._payroll_demo_structure(data['structure'])
            if not structure:
                _logger.warning('payroll_demo: structure %s missing',
                                data['structure'])
                continue
            vals = {
                'name': data['name'],
                'employee_id': employee.id,
                'company_id': company.id,
                'wage': data['wage'],
                'wage_unit': data.get('wage_unit', 'monthly'),
                'date_start': data['date_start'],
                'date_end': data.get('date_end') or False,
                'first_contract_date': data.get('first_contract_date')
                or data['date_start'],
                'struct_id': structure.id,
                'resource_calendar_id': self._payroll_demo_calendar(
                    data.get('calendar', 'standard')).id,
                'state': 'open',
                'table_number': data.get('table_number', 30),
                'column_number': data.get('column_number', 'column1'),
                'has_one_off_tax': data.get('has_one_off_tax', True),
                'one_off_tax': data.get('one_off_tax', 0.3),
                'annual_vacation_days': data.get('annual_vacation_days', 25.0),
                'wage_exchange_amount': data.get('wage_exchange_amount', 0.0),
                'wage_exchange_start': data.get('wage_exchange_start') or False,
                'wage_exchange_end': data.get('wage_exchange_end') or False,
            }
            contract = Contract.search([
                ('employee_id', '=', employee.id),
                ('date_start', '=', data['date_start']),
                ('company_id', '=', company.id),
            ], limit=1)
            if contract:
                contract.write(vals)
            else:
                contract = Contract.create(vals)
            by_employee[data['employee']] = contract
        return by_employee

    @api.model
    def _payroll_demo_calendar(self, code):
        """The working schedule for a contract.

        The schedules belong to the demo company, so they are created here
        rather than in l10n_se_demo_company — they are payroll, not company.
        """
        Calendar = self.env['resource.calendar']
        company = self._payroll_demo_company()
        calendar = Calendar.search([
            ('name', '=', f'Demo {code}'),
            ('company_id', '=', company.id),
        ], limit=1)
        if calendar:
            return calendar
        hours = {'standard': 40, 'part_time_80': 32, 'part_time_75': 30,
                 'part_time_66': 26.4, 'part_time_73': 29.2}
        per_day = hours.get(code, 40) / 5.0
        attendances = []
        for day in range(5):
            attendances += [
                (0, 0, {'name': f'{day} Morning', 'dayofweek': str(day),
                        'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': f'{day} Lunch', 'dayofweek': str(day),
                        'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': f'{day} Afternoon', 'dayofweek': str(day),
                        'hour_from': 13, 'hour_to': 13 + per_day - 4,
                        'day_period': 'afternoon'}),
            ]
        return Calendar.create({
            'name': f'Demo {code}',
            'company_id': company.id,
            'hours_per_day': per_day,
            'work_time_rate': hours.get(code, 40) / 40.0 * 100.0,
            'full_time_required_hours': 40,
            'attendance_ids': attendances,
        })

    @api.model
    def _payroll_demo_create_leaves(self, payload, company):
        """Create and validate the quarter's leaves."""
        Leave = self.env['hr.leave']
        created = Leave.browse()
        for data in payload.get('leaves', []):
            employee = self._payroll_demo_employee(data['employee'])
            leave_type = self.env.ref(data['leave_type'])
            existing = Leave.search([
                ('employee_id', '=', employee.id),
                ('date_from', '=', data['date_from']),
                ('date_to', '=', data['date_to']),
                ('holiday_status_id', '=', leave_type.id),
            ], limit=1)
            if existing:
                created |= existing
                continue
            vals = {
                'name': data.get('name') or leave_type.name,
                'employee_id': employee.id,
                'holiday_status_id': leave_type.id,
                'date_from': data['date_from'],
                'date_to': data['date_to'],
                'request_date_from': data['date_from'][:10],
                'request_date_to': data['date_to'][:10],
            }
            if data.get('number_of_hours'):
                vals['number_of_hours'] = data['number_of_hours']
            if data.get('sick_leave_part'):
                vals['sick_leave_part'] = data['sick_leave_part']
            created |= Leave.create(vals)
        for leave in created:
            if leave.state in ('confirm', 'validate1'):
                leave.action_validate()
        return created

    @api.model
    def _payroll_demo_load_month(self, month, contracts, company):
        """Create, compute, post and pay one month. Returns the payslip count."""
        year, number = month['year'], month['month']
        period = self._payroll_demo_period(year, number)
        journal = self.env['account.journal'].search([
            ('code', '=', 'LÖN'),
            ('company_id', '=', company.id),
        ], limit=1)
        if not journal:
            _logger.warning('payroll_demo: LÖN journal missing, month skipped')
            return 0
        run_vals = {
            'name': month['run_name'],
            'company_id': company.id,
            'journal_id': journal.id,
            'date_start': month['date_from'],
            'date_end': month['date_to'],
        }
        if period:
            run_vals['period_id'] = period.id
        run = self.env['hr.payslip.run'].search([
            ('name', '=', month['run_name']),
            ('company_id', '=', company.id),
        ], limit=1)
        if run:
            run.write(run_vals)
        else:
            run = self.env['hr.payslip.run'].create(run_vals)

        slips = self.env['hr.payslip']
        for data in month.get('payslips', []):
            contract = contracts.get(data['employee'])
            if not contract:
                _logger.warning('payroll_demo: no contract for %s in %s',
                                data['employee'], month['run_name'])
                continue
            existing = self.env['hr.payslip'].search([
                ('employee_id', '=', contract.employee_id.id),
                ('date_from', '=', month['date_from']),
                ('payslip_run_id', '=', run.id),
            ], limit=1)
            if existing:
                slips |= existing
                continue
            vals = {
                'name': f'{contract.employee_id.name} {month["run_name"]}',
                'employee_id': contract.employee_id.id,
                'contract_id': contract.id,
                'struct_id': contract.struct_id.id,
                'payslip_run_id': run.id,
                'company_id': company.id,
                'journal_id': journal.id,
                'date_from': month['date_from'],
                'date_to': month['date_to'],
                'date': month['date_to'],
            }
            if period:
                vals['period_id'] = period.id
            slip = self.env['hr.payslip'].create(vals)
            slip.write({
                'input_line_ids': [
                    (0, 0, {
                        'name': line['code'],
                        'code': line['code'],
                        'amount': line.get('amount', 0.0),
                        'amount_qty': line.get('amount_qty', 0.0),
                        'contract_id': contract.id,
                    })
                    for line in data.get('inputs', [])
                ],
            })
            slips |= slip

        if slips:
            slips.compute_sheet()
            slips.action_payslip_done()
            self._payroll_demo_pay(slips, month, company)
        return len(slips)

    @api.model
    def _payroll_demo_pay(self, slips, month, company):
        """Pay the net wage from the bank and match it to the wage liability."""
        total = sum(slips.mapped('nl_amount'))
        if not total:
            return self.env['account.payment']
        bank_journal = self.env['account.journal'].search([
            ('code', '=', 'BNK1'),
            ('company_id', '=', company.id),
        ], limit=1)
        liability = self._payroll_demo_account(NET_WAGE_ACCOUNT)
        if not (bank_journal and liability):
            _logger.warning('payroll_demo: cannot pay %s, bank or liability '
                            'account missing', month['run_name'])
            return self.env['account.payment']
        payment = self.env['account.payment'].create({
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'partner_id': company.partner_id.id,
            'amount': total,
            'journal_id': bank_journal.id,
            'date': month['pay_date'],
            'memo': f'Nettolön {month["run_name"]}',
            'company_id': company.id,
        })
        payment.action_post()
        # Match the payment against the net wage liability of the payslips'
        # entries, so the liability is settled like a real wage payment.
        lines = slips.move_id.line_ids.filtered(
            lambda l: l.account_id == liability and l.credit)
        if lines:
            (lines + payment.move_id.line_ids.filtered(
                lambda l: l.account_id == liability)).reconcile()
        return payment

    # ------------------------------------------------------------------
    # Removal and withdrawal
    # ------------------------------------------------------------------

    @api.model
    def _payroll_demo_unload_quarter(self, dataset):
        """Remove the payslips, runs, payments and leaves of the quarter."""
        start, end = self._payroll_demo_bounds(dataset)
        company = self._payroll_demo_company()
        slips = self.search([
            ('date_from', '>=', start),
            ('date_from', '<', end),
            ('company_id', '=', company.id),
        ])
        count = len(slips)
        if slips:
            # A done payslip cannot be cancelled while its entry is posted.
            for slip in slips:
                if slip.state == 'done':
                    slip.action_payslip_cancel()
            slips.with_context(force_delete=True).unlink()
        runs = self.env['hr.payslip.run'].search([
            ('date_start', '>=', start),
            ('date_start', '<', end),
            ('company_id', '=', company.id),
        ])
        runs.unlink()
        payments = self.env['account.payment'].search([
            ('date', '>=', start),
            ('date', '<', end),
            ('company_id', '=', company.id),
            ('memo', 'like', 'Nettolön'),
        ])
        payments.with_context(force_delete=True).unlink()
        leaves = self.env['hr.leave'].search([
            ('date_from', '>=', start),
            ('date_from', '<', end),
            ('company_id', '=', company.id),
        ])
        leaves.with_context(force_delete=True).unlink()
        _logger.info('payroll_demo: unloaded %s, %s payslips, %s payments',
                     dataset.name, count, len(payments))
        return count

    @api.model
    def _payroll_demo_unreconcile_quarter(self, dataset):
        """Withdraw the wage payments so the liability is open again."""
        start, end = self._payroll_demo_bounds(dataset)
        company = self._payroll_demo_company()
        payments = self.env['account.payment'].search([
            ('date', '>=', start),
            ('date', '<', end),
            ('company_id', '=', company.id),
            ('memo', 'like', 'Nettolön'),
        ])
        if not payments:
            return 0
        lines = payments.move_id.line_ids
        fulls = self.env['account.full.reconcile'].search([
            ('reconciled_line_ids', 'in', lines.ids),
        ])
        if fulls:
            fulls.unlink()
        partials = self.env['account.partial.reconcile'].search([
            '|', ('debit_move_id', 'in', lines.ids),
            ('credit_move_id', 'in', lines.ids),
        ])
        if partials:
            partials.unlink()
        count = len(payments)
        payments.with_context(force_delete=True).unlink()
        _logger.info('payroll_demo: unreconciled %s, %s payments withdrawn',
                     dataset.name, count)
        return count

    @staticmethod
    def _payroll_demo_bounds(dataset):
        year = dataset.year
        quarter = int(dataset.quarter)
        start = f'{year}-{(quarter - 1) * 3 + 1:02d}-01'
        end = (f'{year + 1}-01-01' if quarter == 4
               else f'{year}-{quarter * 3 + 1:02d}-01')
        return start, end
