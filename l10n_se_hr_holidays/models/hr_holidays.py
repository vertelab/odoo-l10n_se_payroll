# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2014- Vertel AB (<http://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from dataclasses import field
import odoo.exceptions
from odoo import models, fields, api, _
import datetime
from datetime import timedelta, date, datetime
from odoo.exceptions import AccessError, UserError, ValidationError

import logging

from pytz import timezone, UTC
from collections import defaultdict, namedtuple
import math
from odoo.tools.float_utils import float_round

_logger = logging.getLogger(__name__)

from odoo.addons.resource.models.utils import float_to_time, HOURS_PER_DAY

# Used to agglomerate the attendances in order to find the hour_from and hour_to
# See _compute_date_from_to
DummyAttendance = namedtuple('DummyAttendance', 'hour_from, hour_to, dayofweek, day_period, week_type')


class Holidays(models.Model):
    _inherit = "hr.leave"

    def _compute_karens(self):
        for leave_request in self:
            if leave_request.holiday_status_id.sick_leave:
                leave = self.env['hr.leave'].search([
                    ('employee_id', '=', leave_request.employee_id.id),
                    ('date_to', '<', leave_request.date_from)],
                    order='date_to desc', limit=1)

                if not leave or (leave_request.date_from - leave[0].date_to).days > 5:
                    leave_request.is_deffered_period = True
                else:
                    leave_request.is_deffered_period = False
            else:
                leave_request.is_deffered_period = False

    is_deffered_period = fields.Boolean(string="Deffered Day", compute=_compute_karens)

    sick_leave_part = fields.Selection([
        ('100', '100% (heltid)'),
        ('75', '75%'),
        ('50', '50%'),
        ('25', '25%'),
    ], string='Sjukskrivningsgrad', default=False,
       help='Grad av sjukskrivning enligt Försäkringskassan. '
            'Styr hur stor andel av arbetsdagen som är sjukskriven.')

    def _get_number_of_days(self, date_from, date_to, employee_id):
        context_data = {'hr_leave_request': True, 'include_weekends': False}

        if self.holiday_status_id.include_weekends:
            context_data['include_weekends'] = True

        instance = self.with_context(context_data)
        return super(Holidays, instance)._get_number_of_days(date_from, date_to, employee_id, )

    def action_fetch_data(self):
        pass


class hr_holidays_status(models.Model):
    _inherit = "hr.leave.type"

    limit = fields.Boolean('Allow to Override Limit',
                           help='If you select this check box, the system allows the employees to take more leaves '
                                'than the available ones for this type and will not take them into account for the '
                                '"Remaining Legal Leaves" defined on the employee form.')

    payslip_rule = fields.Text(string='Earning Rule', help="Python Code")
    payslip_condition = fields.Text(string='Earning Condition', help="Python Code")
    legal_leave = fields.Boolean(string='Legal Leave', default=False,
                                 help='If checked, it will be included in legal leaves calculation')
    holiday_basis = fields.Boolean(string='Holiday Basis', default=False,
                                   help='If checked, this kind of holiday will be included in holiday basis calculation')
    sick_leave = fields.Boolean(string='Sick Leave', default=False,
                                help='If checked, it will automatically check if any day will be a deferred period')

    include_weekends = fields.Boolean(string='Include Weekends', default=False,
                                      help='If enabled, weekends are counted in leave days calculation.')

    @api.model
    def init_records(self):
        ir_model_data = self.env['ir.model.data']
        current_year = date.today().year

        leave_type_vacation = ir_model_data._xmlid_lookup('l10n_se_hr_holidays.leave_type_vacation')[1]
        self.env['hr.leave.type'].browse(leave_type_vacation).write({
            'name': f'Legal Leaves {current_year - 1}',
            'legal_leave': True,
            'limit': False,
            'date_earning_start': fields.Date.to_string(date(current_year - 2, 4, 1)),
            'date_earning_end': fields.Date.to_string(date(current_year - 1, 3, 31)),
        })
        
        leave_type_vacation_unpaid = ir_model_data._xmlid_lookup('l10n_se_hr_holidays.leave_type_vacation_unpaid')[1]
        self.env['hr.leave.type'].browse(leave_type_vacation_unpaid).write({
            'name': 'Legal Leaves unpaid',
            'legal_leave': False,
            'limit': True,
        })

        module_name = 'l10n_se_hr_holidays' 
        records_config = {
            'holiday_status_cl-4': -4,
            'holiday_status_cl-3': -3,
            'holiday_status_cl-2': -2,
            'holiday_status_cl-1': -1,
            'holiday_status_cl0': 0,
            'holiday_status_cl1': 1,
            'holiday_status_cl2': 2,
            'holiday_status_cl3': 3,
        }

        for xml_id, offset in records_config.items():
            try:
                record_id = ir_model_data._xmlid_lookup(f'{module_name}.{xml_id}')[1]

                name_year = current_year + offset - 1
                start_year = current_year + offset - 2
                end_year = current_year + offset - 1
                
                self.env['hr.leave.type'].browse(record_id).write({
                    'name': f'Legal Leaves {name_year}',
                    'legal_leave': True,
                    'limit': False,
                    'date_earning_start': fields.Date.to_string(date(start_year, 4, 1)),
                    'date_earning_end': fields.Date.to_string(date(end_year, 3, 31)),
                })
            except ValueError:
                continue

        # holiday_status_sl = ir_model_data._xmlid_lookup('hr_holidays.holiday_status_sl')[1]
        # self.env['hr.leave.type'].browse(holiday_status_sl).write({
        #     'name': 'Sick Leave 100%',
        #     'legal_leave': False,
        #     # 'allocation_type': 'no',
        #     'limit': True,
        #     # 'color_name': 'red',
        # })
        # holiday_status_sl = ir_model_data._xmlid_lookup('hr_holidays.holiday_status_sl')[1]
        # self.env['hr.leave.type'].browse(holiday_status_sl).write({
        #     'name': 'Sick Leave 100%',
        #     'legal_leave': False,
        #     # 'allocation_type': 'no',
        #     'limit': True,
        #     # 'color_name': 'red',
        # })

    @api.depends('date_earning_start', 'date_earning_end', 'limit')
    def _holidays_allowed(self):
        for rec in self:
            if not rec.limit:
                rec.holidays_allowed = not (rec.date_earning_start and rec.date_earning_end) or \
                                       fields.Date.today() > rec.date_earning_end
            else:
                rec.holidays_allowed = True

    holidays_allowed = fields.Boolean(string="Allowed", compute='_holidays_allowed', store=True)

    @api.model
    def get_earning_holiday(self):
        holidays = self.env['hr.leave.status'].search(
            [('date_earning_start', '>', fields.Date.today()), ('date_earning_end', '<', fields.Date.today())])
        return holidays[0] if len(holidays) > 0 else None

    date_earning_start = fields.Date(string='Earning year starts')
    date_earning_end = fields.Date(string='Earning year ends')

    def earn_leaves_days(self, forced_start=None, forced_end=None):
        today = fields.Date.context_today(self)
        if today.month <= 3:
            default_start = today.replace(year=today.year - 1, month=4, day=1)
            default_end = today.replace(month=3, day=31)
        else:
            default_start = today.replace(month=4, day=1)
            default_end = today.replace(year=today.year + 1, month=3, day=31)
            
        start_date = forced_start or default_start
        end_date = forced_end or default_end

        if not start_date or not end_date:
            raise UserError(_("Start- och slutdatum för intjänande saknas!"))
            
        for rec in self:
            if rec.work_entry_type_id.code != 'sem_bet':
                continue

            unpaid_leave_type = self.env['hr.leave.type'].search([('work_entry_type_id.code', '=', 'sem_obet')], limit=1)

            for employee in self.env['hr.employee'].search([('contract_id', '!=', False)]):
                alloc_name = f"Intjänad semester ({start_date} till {end_date})"
                existing_alloc = self.env['hr.leave.allocation'].search([
                    ('employee_id', '=', employee.id),
                    ('holiday_status_id', '=', rec.id),
                    ('name', '=', alloc_name),
                    ('state', 'in', ['confirm', 'validate'])
                ], limit=1)
                
                if existing_alloc:
                    continue

                earning_days = self.env['hr.payslip'].get_leaves_earnings_days(employee, start_date, end_date)
                net_days = earning_days['employed_days'] - earning_days['absent_days']

                if net_days > 0:
                    annual_rights = employee.contract_id.annual_vacation_days or 25.0
                    
                    earned_paid_vacation = math.ceil((net_days / 365.0) * annual_rights)
                    
                    if earned_paid_vacation > annual_rights:
                        earned_paid_vacation = annual_rights

                    # Semesteråret börjar dagen efter intjänandeårets slut
                    vacation_start = end_date + relativedelta(days=1)
                    # Semesteråret slutar ett år senare
                    vacation_end = vacation_start + relativedelta(years=1, days=-1)

                    alloc_paid = self.env['hr.leave.allocation'].create({
                        'name': f"Intjänad semester ({start_date} till {end_date})",
                        'employee_id': employee.id,
                        'holiday_status_id': rec.id,
                        'number_of_days': earned_paid_vacation,
                        'state': 'confirm', 
                        'date_from': vacation_start,
                        'date_to': vacation_end,
                    })
                    alloc_paid.action_validate()

                    earned_unpaid_vacation = annual_rights - earned_paid_vacation
                    if earned_unpaid_vacation > 0 and unpaid_leave_type:
                        alloc_unpaid = self.env['hr.leave.allocation'].create({
                            'name': f"Intjänad OBETALD semester ({start_date} till {end_date})",
                            'employee_id': employee.id,
                            'holiday_status_id': unpaid_leave_type.id,
                            'number_of_days': earned_unpaid_vacation,
                            'state': 'confirm', 
                            'date_from': vacation_start,
                            'date_to': vacation_end,
                        })
                        alloc_unpaid.action_validate()

                    log_body = f"Semesterberäkning: {earned_paid_vacation} betalda dagar, {earned_unpaid_vacation} obetalda dagar. (Grundat på {net_days} nettodagar)."
                    alloc_paid.message_post(body=log_body, subject="Semester uträknad")

    def action_transfer_to_saved_leaves(self, forced_date=None):
        today = forced_date or fields.Date.context_today(self)
        
        saved_leave_type = self.env.ref('l10n_se_hr_holidays.leave_type_vacation_saved', raise_if_not_found=False)
        if not saved_leave_type:
            _logger.error("Frånvarotyp för sparad semester saknas!")
            return

        employee_model_id = self.env['ir.model']._get('hr.employee').id
        todo_activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)

        expiring_saved_allocs = self.env['hr.leave.allocation'].search([
            ('holiday_status_id', '=', saved_leave_type.id),
            ('state', '=', 'validate'),
            ('date_to', '!=', False),
            ('date_to', '<=', today),
        ])

        for alloc in expiring_saved_allocs:
            remaining_saved = alloc.number_of_days - alloc.leaves_taken

            if remaining_saved > 0:
                note = (f"Sparade semesterdagar ({remaining_saved} st) har nått sin 5-årsgräns "
                        f"för {alloc.employee_id.name}. Dessa förfaller nu och kommer att "
                        f"betalas ut som semesterersättning i pengar på nästa lön.")
                        
                alloc.employee_id.message_post(body=note, subject="Förfallen sparad semester")

        allocations = self.env['hr.leave.allocation'].search([
            ('holiday_status_id.work_entry_type_id.code', '=', 'sem_bet'),
            ('state', '=', 'validate'),
            ('date_to', '!=', False),
            ('date_to', '<=', today),
        ])

        for alloc in allocations:
            remaining_days = alloc.number_of_days - alloc.leaves_taken

            if remaining_days <= 0:
                continue

            saveable_limit = max(0.0, alloc.number_of_days - 20.0)
            days_to_save = min(remaining_days, saveable_limit)
            
            unspent_mandatory_days = remaining_days - days_to_save

            if days_to_save > 0:
                saved_start = alloc.date_to + relativedelta(days=1)
                saved_end = saved_start + relativedelta(years=5, days=-1)

                saved_alloc = self.env['hr.leave.allocation'].create({
                    'name': f"Sparad semester (utgår {saved_end.strftime('%Y-%m-%d')})",
                    'employee_id': alloc.employee_id.id,
                    'holiday_status_id': saved_leave_type.id,
                    'number_of_days': days_to_save,
                    'state': 'confirm',
                    'date_from': saved_start,
                    'date_to': saved_end, 
                })
                saved_alloc.action_validate()

                alloc.message_post(body=f"Överförde {days_to_save} dagar till Sparad Semester. Dessa gäller till {saved_end}.")
            
            if unspent_mandatory_days > 0:
                warning_note = (
                    f"Observera: {alloc.employee_id.name} har {unspent_mandatory_days} outtagna lagstadgade "
                    f"semesterdagar (av de 20 obligatoriska) för semesteråret som avslutades. "
                    f"Dessa flyttas inte till den sparade potten. Vänligen granska manuellt."
                )
                
                alloc.employee_id.message_post(body=warning_note, subject="Outtagna lagstadgade semesterdagar")
                
                if todo_activity_type:
                    self.env['mail.activity'].create({
                        'res_id': alloc.employee_id.id,
                        'res_model_id': employee_model_id,
                        'activity_type_id': todo_activity_type.id,
                        'summary': 'Granska outtagna lagstadgade semesterdagar',
                        'note': warning_note,
                        'user_id': self.env.uid,
                    })
                    
class hr_employee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def get_leaves_days(self, date_from, date_to):
        return self.contract_id.vacation_days


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
