import logging
from dateutil.relativedelta import relativedelta
from datetime import datetime, time, date

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

    wage_exchange_amount = fields.Float(string="Löneväxlingssumma", defaul=0.0)
    wage_exchange_start = fields.Date(string="Startdatum löneväxling")
    wage_exchange_end = fields.Date(string="Slutdatum löneväxling", help="Lämna tom om växlingen är pågående")

    day_of_pay = fields.Integer(string="Lönedag", default=25)

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

        new_deductions_this_month = 0
        for period in combined_qualifying_periods:
            if payslip_id.date_from <= period['date_from'] <= payslip_id.date_to:
                new_deductions_this_month += 1

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
        
        #leaves_mapped = list(map(lambda l: dict(date_from = l.date_from.date(), date_to = l.date_to.date()) ,leaves))

        #return leaves_mapped
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

        # for leave in leaves:
        #     if leave.date_to.weekday() == 4:
        #         fix_weekend_leaves.append(
        #             {"date_from": leave.date_from.date(), "date_to": leave.date_to.date() + relativedelta(days = 2)}
        #         )
        #     else:
        #         fix_weekend_leaves.append(
        #             {"date_from": leave.date_from.date(), "date_to": leave.date_to.date()}
        #         )
        # _logger.error(f"{fix_weekend_leaves=}")

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

            #cut_off_date = fields.Date(year=leave.date_from.year, month=leave.date_from.month, day=1) + relativedelta(months = 1) - relativedelta(days = 1)
            #if current_end > cut_off_date:
            #    current_end = cut_off_date 

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
            'days_91_plus': 0.0
        }

        for period in combined_periods:
            loop_date = period['date_from']
            while loop_date <= period['date_to']:
                day_index = (loop_date - period['date_from']).days + 1
                
                if payslip.date_from <= loop_date <= payslip.date_to:
                    actual_leaves_this_day = [l['obj'] for l in leaves_mapped if l['date_from'] <= loop_date <= l['date_to']]
                    
                    if actual_leaves_this_day:
                        if day_index <= 14:
                            for leave in actual_leaves_this_day:
                                if leave.request_unit_hours:
                                    res['hours_1_14'] += leave.number_of_hours
                                else:
                                    day_start = fields.Datetime.to_datetime(loop_date)
                                    day_end = day_start + relativedelta(days=1, seconds=-1)
                                    res['hours_1_14'] += self.resource_calendar_id.get_work_hours_count(day_start, day_end, compute_leaves=False)
                        elif 15 <= day_index <= 90:
                            res['days_15_90'] += 1.0
                        else:
                            res['days_91_plus'] += 1.0
            
                loop_date += relativedelta(days=1)
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
        
        start_dt = datetime.combine(payslip.date_from, time.min)
        end_dt = datetime.combine(payslip.date_to, time.max)

        total_scheduled = self.resource_calendar_id.get_work_hours_count(
            start_dt, end_dt, compute_leaves=False
        )

        absence_codes = ['vab', 'sjk', 'tjl_tim', 'tjl_kort', 'tjl_lang', 'sem_bet', 'sem_obet', 'sjk_1_14', 'sjk_15_90']
        absence_hours = sum(
            abs(line.number_of_hours) 
            for line in payslip.worked_days_line_ids 
            if line.code and line.code.lower() in absence_codes
        )

        return max(0.0, total_scheduled - absence_hours)

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
            return total_average_rate / total_days_employed
        return 1.0