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

from importlib.machinery import SourceFileLoader

# logger = SourceFileLoader("logger","/usr/share/tommy/logger.py").load_module()
# logg = logger.TerminalOutput

# ~ from logger import logger.TerminalOutput.getLogger()

# Used to agglomerate the attendances in order to find the hour_from and hour_to
# See _compute_date_from_to
DummyAttendance = namedtuple('DummyAttendance', 'hour_from, hour_to, dayofweek, day_period, week_type')



class Holidays(models.Model):
    _inherit = "hr.leave"

    # ~ logg.msg("Holidays","green",0,"inne i")
    # ~ logg.msg("Holidays","green",0,"inne i", True)

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


    # ~ def _compute_is_deffered:
        # ~ logg.msg("_compute_is_deffered","green",0,"inne i")
        # ~ logg(_compute_is_deffered,"g,0,inne i,*10")
        # ~ start_date - 5

        # ~ leaves = self.env['hr.leave'].search([])

        # ~ if leaves:
            # ~ pass
            # ~ logg.msg(leaves,"yellow",0,"inne i")


    # ~ is_karens_dag = field.Boolean(compute="_compute_is_deffered")

    # ~ _logger.warning(logg)
    # ~ _logger.warning(type(logg))
    # ~ _logger.warning(dir(logg))
    # ~ _logger.warning(f"{type(logg)}"*100)

    _logger.warning(f"inne i Holidays"*100)

    # ~ logg.msg("HolidaysOK!")



class hr_holidays_status(models.Model):
    _inherit = "hr.leave.type"

    _logger.warning(f"inne i hr_holidays_status"*100)


    # ~ logg.msg("hr_holidays_status","green",0,"inne i")

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
    # ~ sick_leave = fields.Boolean(string='Sick Leave', default=False,
                                 # ~ help='If checked, it will automatically check if any day will be a deferred period')

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

