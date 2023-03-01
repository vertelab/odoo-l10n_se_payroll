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

from odoo.addons.resource.models.resource import float_to_time, HOURS_PER_DAY

# Used to agglomerate the attendances in order to find the hour_from and hour_to
# See _compute_date_from_to
DummyAttendance = namedtuple('DummyAttendance', 'hour_from, hour_to, dayofweek, day_period, week_type')

class Holidays(models.Model):
    _inherit = "hr.leave"

    def _timesheet_prepare_line_values(self, index, work_hours_data, day_date, work_hours_count):
        val_list = super(Holidays, self)._timesheet_prepare_line_values(index, work_hours_data, day_date,
                                                                        work_hours_count)
        return val_list

    def _get_number_of_days(self, date_from, date_to, employee_id):
        context_data = {'hr_leave_request': True, 'include_weekends': False}

        if self.holiday_status_id.include_weekends:
            context_data['include_weekends'] = True

        instance = self.with_context(context_data)
        return super(Holidays, instance)._get_number_of_days(date_from, date_to, employee_id, )

    @api.constrains('date_from', 'date_to', 'employee_id')
    def _check_date(self):
        if self.env.context.get('leave_skip_date_check', False):
            return
        for holiday in self.filtered('employee_id'):
            domain = [
                ('date_from', '<', holiday.date_to),
                ('date_to', '>', holiday.date_from),
                ('employee_id', '=', holiday.employee_id.id),
                ('id', '!=', holiday.id),
                ('state', 'not in', ['cancel', 'refuse']),
            ]
            nholidays = self.search_count(domain)
            if nholidays:
                return

    # Owerriding this function to get rid of an if case that raises a VaildationError
    def action_validate(self):
        current_employee = self.env.user.employee_id
        leaves = self.filtered(lambda l: l.employee_id and not l.number_of_days)
        if leaves:
            return
            # raise ValidationError(
            #     _('The following employees are not supposed to work during that period:\n %s') % ','.join(
            #         leaves.mapped('employee_id.name')))

        if any(holiday.state not in ['confirm', 'validate1'] and holiday.validation_type != 'no_validation' for holiday
               in self):
            raise UserError(_('Time off request must be confirmed in order to approve it.'))

        self.write({'state': 'validate'})
        self.filtered(lambda holiday: holiday.validation_type == 'both').write(
            {'second_approver_id': current_employee.id})
        self.filtered(lambda holiday: holiday.validation_type != 'both').write(
            {'first_approver_id': current_employee.id})

        for holiday in self.filtered(lambda holiday: holiday.holiday_type != 'employee'):
            if holiday.holiday_type == 'category':
                employees = holiday.category_id.employee_ids
            elif holiday.holiday_type == 'company':
                employees = self.env['hr.employee'].search([('company_id', '=', holiday.mode_company_id.id)])
            else:
                employees = holiday.department_id.member_ids

            conflicting_leaves = self.env['hr.leave'].with_context(
                tracking_disable=True,
                mail_activity_automation_skip=True,
                leave_fast_create=True
            ).search([
                ('date_from', '<=', holiday.date_to),
                ('date_to', '>', holiday.date_from),
                ('state', 'not in', ['cancel', 'refuse']),
                ('holiday_type', '=', 'employee'),
                ('employee_id', 'in', employees.ids)])

            if conflicting_leaves:
                # YTI: More complex use cases could be managed in master

                if holiday.leave_type_request_unit != 'day' or any(
                        l.leave_type_request_unit == 'hour' for l in conflicting_leaves):
                    raise ValidationError(_('You can not have 2 time off that overlaps on the same day.'))

                # keep track of conflicting leaves states before refusal
                target_states = {l.id: l.state for l in conflicting_leaves}
                conflicting_leaves.action_refuse()
                split_leaves_vals = []
                for conflicting_leave in conflicting_leaves:
                    if conflicting_leave.leave_type_request_unit == 'half_day' and conflicting_leave.request_unit_half:
                        continue

                    # Leaves in days
                    if conflicting_leave.date_from < holiday.date_from:
                        before_leave_vals = conflicting_leave.copy_data({
                            'date_from': conflicting_leave.date_from.date(),
                            'date_to': holiday.date_from.date() + timedelta(days=-1),
                            'state': target_states[conflicting_leave.id],
                        })[0]
                        before_leave = self.env['hr.leave'].new(before_leave_vals)
                        before_leave._compute_date_from_to()

                        # Could happen for part-time contract, that time off is not necessary
                        # anymore.
                        # Imagine you work on monday-wednesday-friday only.
                        # You take a time off on friday.
                        # We create a company time off on friday.
                        # By looking at the last attendance before the company time off
                        # start date to compute the date_to, you would have a date_from > date_to.
                        # Just don't create the leave at that time. That's the reason why we use
                        # new instead of create. As the leave is not actually created yet, the sql
                        # constraint didn't check date_from < date_to yet.
                        if before_leave.date_from < before_leave.date_to:
                            split_leaves_vals.append(before_leave._convert_to_write(before_leave._cache))
                    if conflicting_leave.date_to > holiday.date_to:
                        after_leave_vals = conflicting_leave.copy_data({
                            'date_from': holiday.date_to.date() + timedelta(days=1),
                            'date_to': conflicting_leave.date_to.date(),
                            'state': target_states[conflicting_leave.id],
                        })[0]
                        after_leave = self.env['hr.leave'].new(after_leave_vals)
                        after_leave._compute_date_from_to()
                        # Could happen for part-time contract, that time off is not necessary
                        # anymore.
                        if after_leave.date_from < after_leave.date_to:
                            split_leaves_vals.append(after_leave._convert_to_write(after_leave._cache))

                split_leaves = self.env['hr.leave'].with_context(
                    tracking_disable=True,
                    mail_activity_automation_skip=True,
                    leave_fast_create=True,
                    leave_skip_state_check=True
                ).create(split_leaves_vals)

                split_leaves.filtered(lambda l: l.state in 'validate')._validate_leave_request()

            values = holiday._prepare_employees_holiday_values(employees)
            leaves = self.env['hr.leave'].with_context(
                tracking_disable=True,
                mail_activity_automation_skip=True,
                leave_fast_create=True,
                leave_skip_state_check=True,
            ).create(values)

            leaves._validate_leave_request()

        employee_requests = self.filtered(lambda hol: hol.holiday_type == 'employee')
        employee_requests._validate_leave_request()
        if not self.env.context.get('leave_fast_create'):
            employee_requests.filtered(lambda holiday: holiday.validation_type != 'no_validation').activity_update()
        return True
    
    # def _default_start_datetime(self):
    #     return fields.Datetime.to_string(datetime.combine(fields.Datetime.now(), datetime.min.time()))
        

    # @api.depends('request_hour_start')
    # def _default_end_datetime(self):
    #     return fields.Datetime.to_string(datetime.combine(fields.Datetime.now(), datetime.max.time()))


    # request_hour_start = fields.Datetime()
    # request_hour_end = fields.Datetime()
    # display_time = fields.Char(string="Time!", compute="_compute_display_time")



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

    include_weekends = fields.Boolean(string='Include Weekends', default=False,
                                      help='If enabled, weekends are counted in leave days calculation.')

    @api.model
    def init_records(self):
        holiday_status_cl = self.env['ir.model.data'].get_object_reference('hr_holidays', 'holiday_status_cl')
        self.env['hr.leave.type'].browse(holiday_status_cl[1]).write({
            'name': 'Legal Leaves ' + str(fields.Date.from_string(fields.Datetime.now()).year - 1),
            'legal_leave': True,
            'limit': False,
            'allocation_type': 'fixed_allocation',
            'date_earning_start': fields.Date.to_string(date(date.today().year - 2, 4, 1)),
            'date_earning_end': fields.Date.to_string(date(date.today().year - 1, 3, 31)),
        })
        holiday_status_unpaid = self.env['ir.model.data'].get_object_reference('hr_holidays', 'holiday_status_unpaid')
        self.env['hr.leave.type'].browse(holiday_status_unpaid[1]).write({
            'name': 'Legal Leaves unpaid',
            'legal_leave': False,
            'allocation_type': 'no',
            'limit': True,
            # 'unpaid': True,
        })
        holiday_status_sl = self.env['ir.model.data'].get_object_reference('hr_holidays', 'holiday_status_sl')
        self.env['hr.leave.type'].browse(holiday_status_sl[1]).write({
            'name': 'Sick Leave 100%',
            'legal_leave': False,
            'allocation_type': 'no',
            'limit': True,
            'color_name': 'red',
        })
        # holiday_status_comp
        holiday_status_sl = self.env['ir.model.data'].get_object_reference('hr_holidays', 'holiday_status_sl')
        self.env['hr.leave.type'].browse(holiday_status_sl[1]).write({
            'name': 'Sick Leave 100%',
            'legal_leave': False,
            'allocation_type': 'no',
            'limit': True,
            'color_name': 'red',
        })

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

    def earn_leaves_days(self):
        for rec in self:
            for employee in rec.env['hr.employee'].search([]):
                earning_days = rec.env['hr.payslip'].get_leaves_earnings_days(employee, rec.date_earning_start,
                                                                              rec.date_earning_end)
                if earning_days['employed_days'] - earning_days['absent_days'] > 0:
                    holiday = rec.env['hr.leave'].create({
                        'name': '%s earned days' % rec.name,
                        'employee_id': employee.id,
                        'holiday_status_id': rec.id,
                        'type': 'add',
                        'state': 'validate',
                        'number_of_days_temp': round(((earning_days['employed_days'] - earning_days[
                            'absent_days']) * employee.get_leaves_days(rec.date_earning_start,
                                                                       rec.date_earning_end) / 365) + 0.5, 0),
                    })
                    rec.env['mail.message'].create({
                        'body': _("Earn days %s: %s (%s)" % (earning_days, holiday.number_of_days_temp,
                                                             employee.get_leaves_days(rec.date_earning_start,
                                                                                      rec.date_earning_end))),
                        'subject': "Calculation",
                        'author_id': rec.env['res.users'].browse(rec.env.uid).partner_id.id,
                        'res_id': holiday.id,
                        'model': holiday._name,
                        'type': 'notification', })


class hr_employee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def get_leaves_days(self, date_from, date_to):
        return self.contract_id.vacation_days


class hr_payslip(models.Model):
    _inherit = 'hr.payslip'

    def _holiday_ids(self):
        for rec in self:
            rec.holiday_ids = rec.env['hr.leave'].search(
                [('state', '=', 'validate'), ('employee_id', '=', rec.employee_id.id)]).filtered(
                lambda h: rec.date_to >= h.date_from.date() >= rec.date_from)

    holiday_ids = fields.Many2many(comodel_name='hr.leave', compute='_holiday_ids')

    # ~ @api.one
    def _holiday_status_ids(self):
        for rec in self:
            rec.holiday_status_ids = rec.env['hr.leave.type'].search([('active', '=', True), ('limit', '=', False)])
            rec.holiday_status_ids += rec.env['hr.leave.type'].search([('id', 'in', [
                rec.env.ref('l10n_se_hr_holidays.sick_leave_qualify').id,
                rec.env.ref('l10n_se_hr_holidays.sick_leave_214').id,
                rec.env.ref('hr_holidays.holiday_status_sl').id])])

    holiday_status_ids = fields.Many2many(comodel_name="hr.leave.type", compute="_holiday_status_ids")

    @api.model
    def get_leaves_earnings_days(self, employee, date_from, date_to):
        employed_days = worked_days = absent_days = 0
        for slip in self.env['hr.payslip'].search(
                [('employee_id', '=', employee.id), ('date_from', '>=', date_from), ('date_to', '<=', date_to)]):
            employed_days += (fields.Date.from_string(slip.date_to) - fields.Date.from_string(slip.date_from)).days
            worked_days += slip.worked_days_line_ids.filtered(
                lambda l: l.code == 'WORK100').number_of_days if slip.worked_days_line_ids.filtered(
                lambda l: l.code == 'WORK100') else 0.0
            absent_days += sum(
                a.number_of_days for a in slip.worked_days_line_ids.filtered(lambda l: l.code != 'WORK100'))
        return {'employed_days': employed_days, 'absent_days': absent_days, 'worked_days': worked_days}

    @api.model
    def get_legal_leaves_status(self):
        result = self.with_context({'employee_id': self.employee_id.id}).holiday_status_ids.filtered(
            lambda h: h.remaining_leaves > 0 and h.id not in [
                self.env.ref('hr_holidays.holiday_status_comp').id]).sorted(key=lambda h: h.sequence)
        return result

    @api.model
    def has_legal_leaves(self, code):
        result = self.worked_days_line_ids.filtered(lambda h: h.code == code).mapped('number_of_days')
        return len(result) > 0

    @api.model
    def get_legal_leaves_days(self, code):
        result = sum(self.worked_days_line_ids.filtered(lambda h: h.code == code).mapped('number_of_days'))
        return result

    def leave_number_of_days(self, holiday_status_ref):
        return sum(self.worked_days_line_ids.filtered(lambda w: w.code == self.env.ref(holiday_status_ref).name).mapped(
            'number_of_days'))

    @api.model
    def get_legal_leaves_consumed(self):
        year = datetime.datetime.now().year
        start_date = datetime.datetime(year, 1, 1)
        return abs(sum(self.env['hr.leave'].search(
            [('employee_id', '=', self.employee_id.id), ('date_from', '>=', start_date.strftime('%Y-%m-%d')),
             ('date_to', '<=', self.date_to), ('state', '=', 'validate')]).filtered(
            lambda h: h.holiday_status_id.legal_leave).mapped('number_of_days')))

    def get_holiday_basis_days(self):
        days = 0.0
        for line in self.worked_days_line_ids:
            if self.env['hr.leave.type'].search(
                    [('name', '=', line.code), ('holiday_basis', '=', True)]) or line.code == 'WORK100':
                days += line.number_of_days
        return days

    def get_holiday_basis_percent(self):
        days = 0.0
        days_basis = 0.0
        for line in self.worked_days_line_ids:
            if self.env['hr.leave.type'].search(
                    [('name', '=', line.code), ('holiday_basis', '=', True)]) or line.code == 'WORK100':
                days_basis += line.number_of_days
            days += line.number_of_days
        return days_basis / days if days > 0.0 else 0.0

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
