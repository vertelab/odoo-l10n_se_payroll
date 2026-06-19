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


class hr_payslip(models.Model):
    _inherit = 'hr.payslip'

    currency_id = fields.Many2one("res.currency", related="company_id.currency_id")
    gender = fields.Selection(related="employee_id.gender", string="Kön", store=True)
    nyk_id = fields.Many2one(related="employee_id.nyk_id", string="NYK-kod", store=True)
    job_id = fields.Many2one(related="contract_id.job_id", string="Tjänst", store=True)
    gl_amount = fields.Monetary(string="Grundlön", currency_field='currency_id')
    bl_amount = fields.Monetary(string="Bruttolön", currency_field='currency_id')
    nl_amount = fields.Monetary(string="Nettolön", currency_field='currency_id')
    total_skatt_amount = fields.Monetary(string="Skatt", currency_field='currency_id')
    sa_amount = fields.Monetary(string="Arbetsgivaravgift", currency_field='currency_id')

    def _compute_amounts(self):
        salary_rule_codes = {"gl": "gl_amount", "bl": "bl_amount", "nl": "nl_amount",
                             "total_skatt": "total_skatt_amount", "sa": "sa_amount"}
        for slip in self:
            amounts = {key: 0.0 for key in salary_rule_codes.values()}
            for line in slip.line_ids:
                code = line.salary_rule_id.code
                if code in salary_rule_codes:
                    amounts[salary_rule_codes[code]] += abs(line.total)
            for fname, val in amounts.items():
                setattr(slip, fname, val)

    def compute_sheet(self):
        res = super().compute_sheet()
        self._compute_amounts()
        return res

    def action_payslip_done(self):
        res = super().action_payslip_done()
        self._compute_amounts()
        if self.payslip_run_id:
            self.payslip_run_id._compute_amounts()
        return res

    def action_payslip_cancel(self):
        res = super().action_payslip_cancel()
        if self.payslip_run_id:
            self.payslip_run_id._compute_amounts()
        return res

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
                rec.env.ref('l10n_se_hr_holidays.leave_type_vacation').id,
                rec.env.ref('l10n_se_hr_holidays.leave_type_vacation_unpaid').id,
                rec.env.ref('l10n_se_hr_holidays.leave_type_vacation_saved').id,
                rec.env.ref('l10n_se_hr_holidays.leave_type_vacation_advance').id,
                rec.env.ref('l10n_se_hr_payroll.leave_type_sick').id,
                rec.env.ref('l10n_se_hr_payroll.leave_type_vab').id,
                rec.env.ref('l10n_se_hr_payroll.leave_type_loa').id,
                rec.env.ref('l10n_se_hr_payroll.leave_type_f_led').id
            ])])

    holiday_status_ids = fields.Many2many(comodel_name="hr.leave.type", compute="_holiday_status_ids")

    @api.model
    def get_leaves_earnings_days(self, employee, date_from, date_to):
        employed_days = worked_days = absent_days = 0

        vacation_basis_codes = ['sjk', 'vab', 'f_led']

        for slip in self.env['hr.payslip'].search([
                ('employee_id', '=', employee.id), 
                ('date_from', '>=', date_from), 
                ('date_to', '<=', date_to),
                ('state', 'in', ['done', 'paid'])
            ]):

            date_start = fields.Date.from_string(slip.date_from)
            date_end = fields.Date.from_string(slip.date_to)
            employed_days += (date_end - date_start).days +1

            for line in slip.worked_days_line_ids:
                if line.code == 'WORK100':
                    worked_days += line.number_of_days
                elif line.code not in vacation_basis_codes and line.number_of_days > 0:
                    absent_days += line.number_of_days

        return {'employed_days': employed_days, 'absent_days': absent_days, 'worked_days': worked_days}

    @api.model
    def get_legal_leaves_status(self):
        if not self.employee_id:
            return self.env['hr.leave.type'].browse()

        allocations = self.env['hr.leave.allocation'].search([
            ('employee_id', '=', self.employee_id.id),
            ('state', '=', 'validate'),
            ('number_of_days', '>', 0),
        ])

        positive_types = {}
        for alloc in allocations:
            leave_type = alloc.holiday_status_id
            
            remaining = alloc.number_of_days - alloc.leaves_taken
            if remaining > 0:
                if leave_type.id not in positive_types:
                    positive_types[leave_type.id] = leave_type

        result = self.env['hr.leave.type'].browse(positive_types.keys())
        return result.sorted(key=lambda h: h.sequence)

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

    def get_advance_leave_days(self):
        days = 0.0
        for line in self.worked_days_line_ids:
            if line.code == 'sem_forsk_dagar':
                days += line.number_of_days
        return days