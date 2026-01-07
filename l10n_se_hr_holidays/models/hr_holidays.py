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
        holiday_status_cl = ir_model_data._xmlid_lookup('hr_holidays.holiday_status_cl')[1]
        self.env['hr.leave.type'].browse(holiday_status_cl).write({
            'name': 'Legal Leaves ' + str(fields.Date.from_string(fields.Datetime.now()).year - 1),
            'legal_leave': True,
            'limit': False,
            # 'allocation_type': 'fixed_allocation',
            'date_earning_start': fields.Date.to_string(date(date.today().year - 2, 4, 1)),
            'date_earning_end': fields.Date.to_string(date(date.today().year - 1, 3, 31)),
        })
        holiday_status_unpaid = ir_model_data._xmlid_lookup('hr_holidays.holiday_status_unpaid')[1]
        self.env['hr.leave.type'].browse(holiday_status_unpaid).write({
            'name': 'Legal Leaves unpaid',
            'legal_leave': False,
            # 'allocation_type': 'no',
            'limit': True,
            # 'unpaid': True,
        })
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


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
