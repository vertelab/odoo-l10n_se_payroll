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
from odoo import models, fields, api, _

import logging

_logger = logging.getLogger(__name__)

class HrPayslipWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'

    def has_legal_leaves(self, leave_code):
        for line in self:
            if line.work_entry_type_id and line.work_entry_type_id.code == leave_code:
                if line.number_of_days > 0:
                    return True
        return False

    def get_legal_leaves_days(self, leave_code):
        total_days = 0
        for line in self:
            if line.work_entry_type_id and line.work_entry_type_id.code == leave_code:
                total_days += line.number_of_days
        return total_days

class hr_payslip(models.Model):
    _inherit = 'hr.payslip'

    #@api.model
    def has_legal_leaves(self, code):
        result = self.worked_days_line_ids.filtered(lambda h: h.code == code).mapped('number_of_days')
        return len(result) > 0

    #@api.model
    def get_legal_leaves_days(self, code):
        result = sum(self.worked_days_line_ids.filtered(lambda h: h.code == code).mapped('number_of_days'))
        return result

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
