import logging
from dateutil.relativedelta import relativedelta

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

    day_of_pay = fields.Integer(string="Lönedag", default=25)

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

        return len(combined_qualifying_periods)


    def get_qualifying_sick_leave_periods(self, payslip_id):
        twelve_months_ago = payslip_id.date_from - relativedelta(months = 12)

        domain = [
            ('date_from', '>=', twelve_months_ago),
            ('date_to', '<=', payslip_id.date_to),

            ('employee_id', '=', self.employee_id.id), 
            ('holiday_status_id.sick_leave', '=', True),
        ]

        leaves = self.env['hr.leave'].search(domain)
        
        leaves_mapped = list(map(lambda l: dict(date_from = l.date_from.date(), date_to = l.date_to.date()) ,leaves))

        return leaves_mapped


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
            ('holiday_status_id.sick_leave', '=', True)
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
            number_of_days = previous_end.day - current_start.day + 1
            _logger.error(f"{number_of_days=}")
            total_days += number_of_days - leave["non_sick_days"]
            _logger.error(f"{total_days=}")
        return total_days


    def get_non_sick_days(self, leave):
        current_start = leave["date_from"]
        previous_end = leave["date_to"]
        number_of_days = previous_end.day - current_start.day 
        _logger.error(f"Sick: {number_of_days}")
        return number_of_days    


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
                if current_start.day - previous_end.day <= 5: 
                    combined_periods[-1]["non_sick_days"] += current_start.day - previous_end.day -1

                    combined_periods[-1]["date_to"] = current_end
                else: 
                    combined_periods.append(
                        {"date_from": current_start, "date_to": current_end, "non_sick_days": 0}
                    )

        return combined_periods


    def get_leave_of_absence_periods(self, payslip):
        domain = [
            ('date_from', '<=', payslip.date_to),
            ('date_to', '>=', payslip.date_from),
            ('employee_id', '=', self.employee_id.id),
            ('holiday_status_id.work_entry_type_id.code', '=', 'leave_of_absence'),
            ('state', '=', 'validate'),
        ]
        _logger.info(f"Söker tjänstledighet med domän: {domain}")
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
                _logger.info(f"Tjänstledighet timmar: {p['number_of_hours']}")
            # 1-5 arbetsdaagar
            elif 1.0 <= p['number_of_days'] <= 5.0:
                res['short_leave_days'] += p['number_of_days']
                _logger.info(f"Tjänstledighet 1-5 dagar: {p['number_of_days']}")
            # Mer än 5 (kalender)dagar
            else:
                delta = p['date_to'].date() - p['date_from'].date()
                calendar_days = delta.days +1
                res['long_leave_calendar_days'] += calendar_days
                _logger.info(f"Tjänstledighet 5+ kalenderdagar: {calendar_days}")

        return res