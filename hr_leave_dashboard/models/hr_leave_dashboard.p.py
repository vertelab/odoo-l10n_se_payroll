# -*- coding: utf-8 -*-
from datetime import date, datetime
from odoo import fields, models, api, _
from odoo.exceptions import AccessError

import logging

_logger = logging.getLogger(__name__)


class HrLeaveDashboard(models.AbstractModel):
    """Dashboard model providing leave data for managers.
    Displays subordinates' leave status, today's absentees,
    upcoming holidays, and pending approvals."""

    _name = 'hr.leave.dashboard'
    _description = 'HR Leave Dashboard'

    @api.model
    def get_dashboard_data(self):
        """Return all data needed for the leave dashboard."""
        employee = self.env.user.employee_id
        if not employee:
            return {}

        subordinates = self._get_subordinates(employee)
        return {
            'current_employee': {
                'name': employee.name,
                'job_title': employee.job_id.name or '',
                'department': employee.department_id.name or '',
                'subordinate_count': len(subordinates),
            },
            'subordinates': subordinates,
            'today_absentees': self._get_today_absentees(employee),
            'upcoming_holidays': self._get_upcoming_holidays(),
            'pending_approvals': self._get_pending_approvals(employee),
            'today': date.today().isoformat(),
        }

    def _get_subordinates(self, employee):
        """Get all direct subordinates with their leave balances."""
        result = []
        children = employee.child_ids.filtered(lambda e: e.active)
        for child in children:
            allocations = self.env['hr.leave.allocation'].search([
                ('employee_id', '=', child.id),
                ('state', '=', 'validate'),
            ])
            leave_balances = []
            for alloc in allocations:
                remaining = alloc.number_of_days - alloc.leaves_taken
                if remaining > 0:
                    leave_balances.append({
                        'type': alloc.holiday_status_id.name,
                        'remaining': round(remaining, 1),
                        'allocated': alloc.number_of_days,
                    })

            result.append({
                'id': child.id,
                'name': child.name,
                'job_title': child.job_id.name or '',
                'leave_balances': leave_balances,
                'is_absent_today': self._is_absent_today(child),
            })
        return result

    def _is_absent_today(self, employee):
        """Check if employee is on leave today."""
        today = date.today()
        leaves = self.env['hr.leave'].search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'validate'),
            ('request_date_from', '<=', today),
            ('request_date_to', '>=', today),
        ])
        return bool(leaves)

    def _get_today_absentees(self, employee):
        """Get all subordinates who are absent today."""
        today = date.today()
        children = employee.child_ids.filtered(lambda e: e.active)
        if not children:
            return []

        leaves = self.env['hr.leave'].search([
            ('employee_id', 'in', children.ids),
            ('state', '=', 'validate'),
            ('request_date_from', '<=', today),
            ('request_date_to', '>=', today),
        ])

        return [{
            'employee_name': leave.employee_id.name,
            'leave_type': leave.holiday_status_id.name,
            'from_date': leave.request_date_from.isoformat(),
            'to_date': leave.request_date_to.isoformat(),
            'days': leave.number_of_days,
        } for leave in leaves]

    def _get_upcoming_holidays(self, days_ahead=30):
        """Get upcoming public holidays within the next N days."""
        today = date.today()
        end_date = today + fields.Date.timedelta(days=days_ahead)

        holidays = self.env['resource.calendar.leaves'].search([
            ('resource_id', '=', False),
            ('date_from', '>=', fields.Datetime.to_string(today)),
            ('date_from', '<=', fields.Datetime.to_string(end_date)),
        ], order='date_from asc')

        return [{
            'name': h.name or _('Public Holiday'),
            'date_from': h.date_from.date().isoformat(),
            'date_to': h.date_to.date().isoformat(),
        } for h in holidays[:10]]

    def _get_pending_approvals(self, employee):
        """Get leave requests from subordinates that need approval."""
        children = employee.child_ids.filtered(lambda e: e.active)
        if not children:
            return []

        pending = self.env['hr.leave'].search([
            ('employee_id', 'in', children.ids),
            ('state', 'in', ('confirm', 'validate1')),
        ], order='request_date_from asc', limit=20)

        return [{
            'id': leave.id,
            'employee_name': leave.employee_id.name,
            'leave_type': leave.holiday_status_id.name,
            'from_date': leave.request_date_from.isoformat(),
            'to_date': leave.request_date_to.isoformat(),
            'days': leave.number_of_days,
            'state': leave.state,
        } for leave in pending]
