import logging
from dateutil.relativedelta import relativedelta
from datetime import datetime, time, date
from pytz import timezone

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


#VA = Veckoarbetstid                         Weekly Working Hours

#http://www.vismaspcs.se/visma-support/visma-lon-special/content/visma-lon-special/semester/semesterlon-vid-andrad-sysselsattningsgrad.htm
#APR = Arbetstidsprocent                     Working Percent
#ML = Månadslön                              Monthly Salary
#SSG = Sysselsättninggrad                    Employment Rate
#VAD = Veckoarbetstid dagar heltid           WWH Days Full Time
#VADI = Veckoarbetstid dagar intermittent    WWH Days Intermittent

# regler att ha i åtanke:
# 1. Om anställd är sjuk mer än 14 dagar så är det arbetsgivaren som betalar
# 2. Om anställd är sjuk mer än 90 dagar så är det försäkringskassan som betalar
# 3. Karens dras bara en gång per sjukperiod
# 4. Återinsjuknande inom 5 dagar räknas som samma sjukperiod
# 5. En sjukperiod pågår tills anställd är frisk
# 6. Om anställd är sjuk på en helg(dag) räknas det som sjukdag om den föregås eller följs av en sjukdag OM det är fler än 15 dagar
# 7. Om en anställd blir sjuk under en semester räknas det som sjukdag och inte semesterdag

class hr_contract(models.Model):
    _inherit = "hr.contract"

    correction_ids = fields.One2many(
        'hr.payroll.correction',
        compute='_compute_correction_ids',
        string='Lönekorrigeringar')

    def _compute_correction_ids(self):
        for contract in self:
            contract.correction_ids = self.env['hr.payroll.correction'].search([
                ('employee_id', '=', contract.employee_id.id),
            ]) if contract.employee_id else False

    wage_exchange_amount = fields.Float(string="Löneväxlingssumma", default=0.0)
    wage_exchange_start = fields.Date(string="Startdatum löneväxling")
    wage_exchange_end = fields.Date(string="Slutdatum löneväxling", help="Lämna tom om växlingen är pågående")

    day_of_pay = fields.Integer(string="Lönedag", default=25)

    #löneutmätning på engelska = attachment of earnings
    has_attachment_of_earnings = fields.Boolean(string="Löneutmätning", default=False)
    attachment_of_earnings_start = fields.Date(string="Startdatum löneutmätning")

    attachment_amount = fields.Float(string="Utmätningsbelopp", help="Det fasta belopp Kronofogden beslutat ska dras per månad.")
    protected_amount = fields.Float(string="Förbehållsbelopp", help="Det individuella belopp den anställde måste få behålla (bestäms av Kronofogden).")

    def get_attachment_deduction(self, payslip, net_salary_before_deduction):
        self.ensure_one()

        if not self.has_attachment_of_earnings:
            return 0.0
        
        if self.attachment_of_earnings_start and self.attachment_of_earnings_start > payslip.date_to:
            return 0.0

        available_for_attachment = net_salary_before_deduction - self.protected_amount

        if available_for_attachment <= 0:
            return 0.0
            
        actual_deduction = min(self.attachment_amount, available_for_attachment)
        
        return actual_deduction

    def get_current_wage_exchange(self, payslip):
        self.ensure_one()

        if not self.wage_exchange_amount:
            return 0.0

        if not self.wage_exchange_start:
            return 0.0
        
        starts_before_end = self.wage_exchange_start <= payslip.date_to
        ends_after_start = not self.wage_exchange_end or self.wage_exchange_end >= payslip.date_from

        if starts_before_end and ends_after_start:
            return self.wage_exchange_amount

        return 0.0

    def get_effective_wage(self, payslip):
        self.ensure_one()
        exchange = self.get_current_wage_exchange(payslip)
        return self.wage - exchange

    def get_full_time_wage(self, payslip):
        # Funktion för att räkna upp deltidslön till heltidslön
        # behövs vid bl.a. övertidsberäkning
        self.ensure_one()
        current_wage = self.get_effective_wage(payslip)

        rate = (self.resource_calendar_id.work_time_rate or 100.0) / 100.0
        
        return current_wage / rate if rate > 0 else current_wage

    # 1-14 + 15-90
    def get_sick_days(self, payslip_id):
        sick_leaves = self.get_monthly_sick_leave_periods(payslip_id)
        combined_sick_leaves = self.combine_sick_leave_periods(sick_leaves)
        sick_days = self.calculate_sick_days(combined_sick_leaves)

        return sick_days

    # antal karensavdrag
    def qualifying_count(self, payslip_id):
        qualifying_periods = self.get_qualifying_sick_leave_periods(payslip_id) 
        combined_qualifying_periods = self.combine_sick_leave_periods(qualifying_periods)

        twelve_months_ago = payslip_id.date_from - relativedelta(months = 12)

        historical_deductions_count = 0
        new_deductions_this_month = 0

        sorted_periods = sorted(combined_qualifying_periods, key=lambda p: p['date_from'])

        for period in sorted_periods:
            if period['date_from'] >= twelve_months_ago:
                if payslip_id.date_from <= period['date_from'] <= payslip_id.date_to:
                    if historical_deductions_count < 10:
                        new_deductions_this_month += 1
                        historical_deductions_count += 1
                    else:
                        _logger.info(f"Högriskskydd triggat för {self.employee_id.name}. Inget karensavdrag dras.")
                elif period['date_from'] < payslip_id.date_from:
                    historical_deductions_count += 1

        return new_deductions_this_month


    def get_qualifying_sick_leave_periods(self, payslip_id):
        twelve_months_ago = payslip_id.date_from - relativedelta(months = 12)

        domain = [
            ('date_from', '<=', payslip_id.date_to),
            ('date_to', '>=', twelve_months_ago),
            ('employee_id', '=', self.employee_id.id), 
            ('holiday_status_id.work_entry_type_id.code', '=', 'sjk'),
            ('state', 'in', ['confirm', 'validate']),
        ]

        leaves = self.env['hr.leave'].search(domain)

        return [{'date_from': l.date_from.date(), 'date_to': l.date_to.date()} for l in leaves]
        
    def get_monthly_sick_leave_periods(self, payslip_id):

        domain = [
            '|','|', '|', 
            '&', 
                ('date_from', '<=', payslip_id.date_from), 
                ('date_to', '>=', payslip_id.date_to), 
            '&', 
                ('date_from', '<=', payslip_id.date_from), 
                ('date_from','>=', payslip_id.date_from), 
            '&', 
                ('date_from', '<=', payslip_id.date_to), 
                ('date_to','>=', payslip_id.date_to), 
            '&', 
                ('date_from', '>=', payslip_id.date_from), 
                ('date_to','<=', payslip_id.date_to), 
                        
            ('employee_id', '=', self.employee_id.id), 
            ('holiday_status_id.work_entry_type_id.code', '=', 'sjk')
        ]
        
        leaves = self.env['hr.leave'].search(domain)

        fix_weekend_leaves = []

        for leave in leaves:
            fix_weekend_leaves.append(
                {"date_from": leave.date_from.date(), "date_to": leave.date_to.date()}
            )

        return fix_weekend_leaves


    def calculate_sick_days(self, leaves):
        total_days = 0
        for leave in leaves: 
            current_start = leave["date_from"]
            previous_end = leave["date_to"]
            number_of_days = (previous_end - current_start).days + 1
            #_logger.error(f"{number_of_days=}")
            total_days += number_of_days - leave.get("non_sick_days", 0)
            #_logger.error(f"{total_days=}")
        return total_days


    def get_non_sick_days(self, leave):
        current_start = leave["date_from"]
        previous_end = leave["date_to"]
        #number_of_days = previous_end.day - current_start.day 
        #_logger.error(f"Sick: {number_of_days}")
        return (previous_end - current_start).days


    # Kombinerar perioder som ligger inom fem dagar från varandra så att de räknas till samma sjukperiod
    def combine_sick_leave_periods(self, leaves):
        sorted_leaves = sorted(leaves, key=lambda l: l["date_from"])
        combined_periods = []

        cut_off_date = None

        for leave in sorted_leaves:
            current_start = leave["date_from"]
            current_end = leave["date_to"]

            if not combined_periods:
                combined_periods.append(
                    {"date_from": current_start, "date_to": current_end, "non_sick_days": 0}
                )
            else: 
                previous_end = combined_periods[-1]["date_to"]
                if (current_start - previous_end).days <= 5: 
                    combined_periods[-1]["date_to"] = max(previous_end, current_end)
                else: 
                    combined_periods.append({"date_from": current_start, "date_to": current_end})
        return combined_periods

    def get_sick_pay_data(self, payslip):
        # Kolla sex mån bakåt för att lämna utrymme för 5-dagarsregeln
        import pytz
        date_from_history = payslip.date_from - relativedelta(months=6)
        domain = [
            ('date_from', '<=', payslip.date_to),
            ('date_to', '>=', date_from_history),
            ('employee_id', '=', self.employee_id.id),
            ('holiday_status_id.work_entry_type_id.code', '=', 'sjk'),
            ('state', 'in', ['confirm', 'validate']),
        ]
        leaves = self.env['hr.leave'].search(domain)
        
        leaves_mapped = [{'date_from': l.date_from.date(), 'date_to': l.date_to.date(), 'obj': l} for l in leaves]
        combined_periods = self.combine_sick_leave_periods(leaves_mapped)

        res = {
            'hours_1_14': 0.0,
            'days_15_90': 0.0,
            'part_15_90': 1.0,
            'days_91_plus': 0.0,
        }

        part_sum = 0.0
        part_day_count = 0

        for period in combined_periods:
            loop_date = period['date_from']
            while loop_date <= period['date_to']:
                day_index = (loop_date - period['date_from']).days + 1
                
                if payslip.date_from <= loop_date <= payslip.date_to:
                    actual_leaves_this_day = [l['obj'] for l in leaves_mapped if l['date_from'] <= loop_date <= l['date_to']]
                    
                    if actual_leaves_this_day:
                        explicit_parts = [l.sick_leave_part for l in actual_leaves_this_day
                                            if hasattr(l, 'sick_leave_part') and l.sick_leave_part]
                        
                        day_start = datetime.combine(loop_date, time.min)
                        day_end = datetime.combine(loop_date, time.max)

                        work_hours_today = self.resource_calendar_id.get_work_hours_count(
                            day_start, day_end, compute_leaves=True)

                        user_tz = pytz.timezone(self.env.user.tz or 'Europe/Stockholm')

                        day_start_local = user_tz.localize(day_start)
                        day_end_local = user_tz.localize(day_end)

                        day_start_utc = day_start_local.astimezone(pytz.utc).replace(tzinfo=None)
                        day_end_utc = day_end_local.astimezone(pytz.utc).replace(tzinfo=None)

                        is_global_leave = self.env['resource.calendar.leaves'].search_count([
                            ('resource_id', '=', False),
                            ('date_from', '<=', day_end_utc),
                            ('date_to', '>=', day_start_utc),
                            '|', ('calendar_id', '=', False), ('calendar_id', '=', self.resource_calendar_id.id),
                            ('company_id', 'in', [False, self.company_id.id])
                        ])
                        
                        if is_global_leave > 0:
                            work_hours_today = 0.0

                        if explicit_parts:
                            part = max(int(d) for d in explicit_parts) / 100.0
                        else:
                            if work_hours_today > 0:
                                leave_hours = sum(l.number_of_hours for l in actual_leaves_this_day)
                                part = min(leave_hours / work_hours_today, 1.0)
                            else:
                                part = 1.0

                        if day_index <= 14:
                            if work_hours_today > 0:
                                res['hours_1_14'] += (work_hours_today * part)
                        elif 15 <= day_index <= 90:
                            res['days_15_90'] += 1.0
                            part_sum += part
                            part_day_count += 1
                        else:
                            res['days_91_plus'] += 1.0
            
                loop_date += relativedelta(days=1)

        if part_day_count > 0:
            res['part_15_90'] = part_sum / part_day_count

        return res

    def get_leave_of_absence_periods(self, payslip):
        domain = [
            ('date_from', '<=', payslip.date_to),
            ('date_to', '>=', payslip.date_from),
            ('employee_id', '=', self.employee_id.id),
            ('holiday_status_id.work_entry_type_id.code', '=', 'tjl'),
            ('state', '=', 'validate'),
        ]
        leaves = self.env['hr.leave'].search(domain)

        leave_periods = []
        for l in leaves:
            leave_periods.append({
                "date_from": l.date_from,
                "date_to": l.date_to,
                "number_of_days": l.number_of_days,
                "number_of_hours": l.number_of_hours,
            })
        return leave_periods

    def split_leave_of_absence_periods(self, payslip):

        periods = self.get_leave_of_absence_periods(payslip)

        res = {
            'hourly_leave_hours': 0.0,
            'short_leave_days': 0.0,
            'long_leave_calendar_days': 0.0
        }

        for p in periods:
            # Del av dag
            if p['number_of_days'] < 1.0:
                res['hourly_leave_hours'] += p['number_of_hours']
                #_logger.info(f"Tjänstledighet timmar: {p['number_of_hours']}")
            # 1-5 arbetsdaagar
            elif 1.0 <= p['number_of_days'] <= 5.0:
                res['short_leave_days'] += p['number_of_days']
                #_logger.info(f"Tjänstledighet 1-5 dagar: {p['number_of_days']}")
            # Mer än 5 (kalender)dagar
            else:
                delta = p['date_to'].date() - p['date_from'].date()
                calendar_days = delta.days +1
                res['long_leave_calendar_days'] += calendar_days
                #_logger.info(f"Tjänstledighet 5+ kalenderdagar: {calendar_days}")

        return res
    
    def get_vacation_days(self, payslip_id):
        domain = [
            ('date_from', '<=', payslip_id.date_to),
            ('date_to', '>=', payslip_id.date_from),
            ('employee_id', '=', self.employee_id.id),
            ('holiday_status_id.work_entry_type_id.code', '=', 'sem_bet'),
            ('state', '=', 'validate'),
        ]
        
        leaves = self.env['hr.leave'].search(domain)
        total_days = sum(leave.number_of_days for leave in leaves)
        
        return total_days
    
    def get_actual_work_hours(self, payslip):
        self.ensure_one()
        
        is_hourly = self.struct_id and self.struct_id.code and 'tim' in self.struct_id.code

        if is_hourly:
            timesheets = self.env['account.analytic.line'].search([
                ('employee_id', '=', self.employee_id.id),
                ('date', '>=', payslip.date_from),
                ('date', '<=', payslip.date_to),
                ('holiday_id', '=', False),
            ])
            return sum(timesheets.mapped('unit_amount'))

        import pytz

        user_tz = pytz.timezone(self.env.user.tz or 'Europe/Stockholm')

        start_dt = user_tz.localize(datetime.combine(payslip.date_from, time.min)).astimezone(pytz.UTC)
        end_dt = user_tz.localize(datetime.combine(payslip.date_to, time.max)).astimezone(pytz.UTC)

        total_scheduled = self.resource_calendar_id.get_work_hours_count(
            start_dt, end_dt, compute_leaves=False
        )

        public_holiday_hours = 0.0

        global_leaves = self.env['resource.calendar.leaves'].search([
            ('resource_id', '=', False),
            ('date_from', '<=', end_dt),
            ('date_to', '>=', start_dt),
            '|', ('calendar_id', '=', False), ('calendar_id', '=', self.resource_calendar_id.id),
            ('company_id', 'in', [False, self.company_id.id])
        ])

        for leave in global_leaves:
            leave_start_utc = pytz.utc.localize(leave.date_from)
            leave_end_utc = pytz.utc.localize(leave.date_to)
            
            l_start = max(start_dt, leave_start_utc)
            l_end = min(end_dt, leave_end_utc)
            
            if l_start < l_end:
                public_holiday_hours += self.resource_calendar_id.get_work_hours_count(l_start, l_end, compute_leaves=False)

        absence_codes = [
            'vab', 'sjk', 'tj_ledighet',
            'f_ledighet', 'f_led',
            'f_led_arb', 'f_led_tj',
            'f_lon_tj',
            'tjl_tim', 'tjl_kort', 'tjl',
            'tjl_lang', 'sem_bet', 
            'sem_obet', 'sjk_1_14', 
            'sjk_lon_1590', 'sjk_15_90_arb'
        ]
        absence_hours = sum(
            abs(line.number_of_hours) 
            for line in payslip.worked_days_line_ids 
            if line.code and line.code.lower() in absence_codes
        )

        return max(0.0, total_scheduled - absence_hours - public_holiday_hours)

    def get_holiday_basis_pay_hours(self, payslip):
        self.ensure_one()

        basis_hour_codes = ['sjk', 'vab', 'f_led']

        basis_hours = sum(
            abs(line.number_of_hours)
            for line in payslip.worked_days_line_ids
            if line.code and line.code.lower() in basis_hour_codes
        )

        return basis_hours

    def get_historical_employment_rate(self, payslip):
        self.ensure_one()

        current_date = payslip.date_from
        if current_date.month >= 4:
            earning_year_start = date(current_date.year - 1, 4, 1)
            earning_year_end = date(current_date.year, 3, 31)
        else:
            earning_year_start = date(current_date.year - 2, 4, 1)
            earning_year_end = date(current_date.year - 1, 3, 31)

        contracts = self.env['hr.contract'].search([
            ('employee_id', '=', self.employee_id.id),
            ('date_start', '<=', earning_year_end),
            '|', ('date_end', '>=', earning_year_start), ('date_end', '=', False),
        ])

        total_average_rate = 0.0
        total_days_employed = 0

        for ct in contracts:
            overlap_start = max(ct.date_start, earning_year_start)
            overlap_end = min(ct.date_end or earning_year_end, earning_year_end)

            if overlap_start > overlap_end:
                continue
            
            duration = (overlap_end - overlap_start).days + 1

            cal = ct.resource_calendar_id
            if cal and cal.full_time_required_hours > 0:
                weekly_hours = sum(line.hour_to - line.hour_from for line in cal.attendance_ids if line.day_period != 'lunch')
                rate = weekly_hours / cal.full_time_required_hours
            else:
                rate = 1.0
            
            total_average_rate += (rate * duration)
            total_days_employed += duration
        
        if total_days_employed > 0:
            raw_rate = total_average_rate / total_days_employed
            return round(raw_rate, 2)
        return 1.0

    def get_parental_leave_data(self, payslip):
        domain = [
            ('date_from', '<=', payslip.date_to),
            ('date_to', '>=', payslip.date_from),
            ('employee_id', '=', self.employee_id.id),
            ('holiday_status_id.work_entry_type_id.code', '=', 'f_led'),
            ('state', '=', 'validate'),
        ]
        leaves = self.env['hr.leave'].search(domain)

        res = {
            'hourly_hours': 0.0,
            'short_work_days': 0.0,
            'long_calendar_days': 0.0
        }

        for l in leaves:
            start = max(l.date_from.date(), payslip.date_from)
            end = min(l.date_to.date(), payslip.date_to)
            
            if l.number_of_days < 1.0:
                res['hourly_hours'] += l.number_of_hours
            
            elif 1.0 <= l.number_of_days <= 5.0:
                res['short_work_days'] += l.number_of_days
            
            else:
                delta = (end - start).days + 1
                res['long_calendar_days'] += delta

        return res

    def calculate_employment_years(self, reference_date):
        self.ensure_one()
        start_date = self.first_contract_date or self.date_start

        if not start_date:
            return 0
        
        d1 = start_date
        d2 = reference_date
        
        years = relativedelta(d2, d1).years
        return years

    def get_calendar_days_for_f_led(self, payslip):
        domain = [
            ('date_from', '<=', payslip.date_to),
            ('date_to', '>=', payslip.date_from),
            ('employee_id', '=', self.employee_id.id),
            ('holiday_status_id.work_entry_type_id.code', '=', 'f_led'),
            ('state', '=', 'validate'),
        ]
        leaves = self.env['hr.leave'].search(domain)
        total_cal_days = 0
        for l in leaves:
            start = max(l.date_from.date(), payslip.date_from)
            end = min(l.date_to.date(), payslip.date_to)
            total_cal_days += (end - start).days + 1
        return total_cal_days


    def get_parental_pay_amount(self, payslip):
        self.ensure_one()

        input_line = payslip.input_line_ids.filtered(lambda l: l.code == 'fl_slut_tj')
        input_amount = input_line.amount if input_line else 0.0

        effective_wage = self.get_effective_wage(payslip)

        PBB = payslip.struct_id.get_constant('PBB') or 48300 
        limit = 40250

        if effective_wage <= limit:
            avdrag_dag = 0.90 * (effective_wage * 12) / 365
        else:
            avdrag_dag = (0.90 * (10 * PBB) / 365) + (0.10 * (effective_wage * 12 - 10 * PBB) / 365)

        years = self.calculate_employment_years(payslip.date_to)
        total_f_lon = 0
        
        if 1 <= years < 2:
            total_f_lon = (2 * effective_wage) - (60 * avdrag_dag)
        elif 2 <= years < 3:
            total_f_lon = (3 * effective_wage) - (90 * avdrag_dag)
        elif 3 <= years < 4:
            total_f_lon = (4 * effective_wage) - (120 * avdrag_dag)
        elif years >= 4:
            total_f_lon = (5 * effective_wage) - (150 * avdrag_dag)

        if input_amount > 0:
            return max(0, total_f_lon * 0.5)

        current_leaves = self.env['hr.leave'].search([
            ('employee_id', '=', self.employee_id.id),
            ('date_from', '<=', payslip.date_to),
            ('date_to', '>=', payslip.date_from),
            ('holiday_status_id.work_entry_type_id.code', '=', 'f_led'),
            ('state', '=', 'validate')
        ])

        if current_leaves:
            for leave in current_leaves:
                start_date = leave.date_from.date()
                
                if payslip.date_from <= start_date <= payslip.date_to:
                    
                    duration = (leave.date_to.date() - leave.date_from.date()).days + 1
                    
                    if duration >= 30:
                        day_before = start_date - relativedelta(days=1)
                        previous_leave_exists = self.env['hr.leave'].search_count([
                            ('employee_id', '=', self.employee_id.id),
                            ('date_to', '=', day_before),
                            ('holiday_status_id.work_entry_type_id.code', '=', 'f_led'),
                            ('state', '=', 'validate')
                        ])

                        if previous_leave_exists == 0:
                            return max(0, total_f_lon * 0.5)
        
        return 0.0

    def get_expired_saved_vacation_days(self, payslip):
        self.ensure_one()

        date_from_history = payslip.date_from - relativedelta(months=1)
        date_to_history = payslip.date_from - relativedelta(days=1)

        saved_leave_type = self.env.ref('l10n_se_hr_holidays.leave_type_vacation_saved', raise_if_not_found=False)
        if not saved_leave_type:
            return 0.0

        allocations = self.env['hr.leave.allocation'].search([
            ('employee_id', '=', self.employee_id.id),
            ('holiday_status_id', '=', saved_leave_type.id),
            ('state', '=', 'validate'),
            ('date_to', '>=', date_from_history),
            ('date_to', '<=', date_to_history),
        ])

        expired_days = 0.0
        for alloc in allocations:
            remaining = alloc.number_of_days - alloc.leaves_taken
            if remaining > 0:
                expired_days += remaining
        return expired_days