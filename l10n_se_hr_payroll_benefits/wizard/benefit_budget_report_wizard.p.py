# -*- coding: utf-8 -*-
from odoo import _, fields, models, api


class BenefitBudgetReportWizard(models.TransientModel):
    _name = 'benefit.budget.report.wizard'
    _description = 'Benefit Budget Report Wizard'

    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)

    budget_id = fields.Many2one(
        'hr.benefit.budget', string='Budget',
        domain="[('company_id', '=', company_id)]",
        help='Leave empty to show all budgets')

    date_to = fields.Date(
        string='Report Date', required=True,
        default=fields.Date.today)

    def _get_data(self):
        domain = [('company_id', '=', self.company_id.id)]
        if self.budget_id:
            domain.append(('budget_id', '=', self.budget_id.id))
        else:
            domain.append(('budget_id.year', '=', self.date_to.year))

        lines = self.env['hr.benefit.budget.line'].search(domain)
        data = []
        total_allocated = total_used = total_remaining = 0.0

        for line in lines.sorted(lambda l: (l.budget_id.name, l.employee_id.name)):
            pct = round(line.used_amount / line.allocated_amount * 100, 1) if line.allocated_amount else 0
            data.append({
                'budget': line.budget_id.name,
                'employee': line.employee_id.name,
                'allocated': line.allocated_amount,
                'used': line.used_amount,
                'remaining': line.remaining_amount,
                'pct_used': pct,
            })
            total_allocated += line.allocated_amount
            total_used += line.used_amount
            total_remaining += line.remaining_amount

        data.append({
            'budget': '',
            'employee': 'TOTAL',
            'allocated': total_allocated,
            'used': total_used,
            'remaining': total_remaining,
            'pct_used': round(total_used / total_allocated * 100, 1) if total_allocated else 0,
        })
        return data

    def action_print_report(self):
        data = self._get_data()
        return self.env.ref(
            'l10n_se_hr_payroll_benefits.action_report_benefit_budget'
        ).report_action([], data={
            'date_to': self.date_to,
            'company': self.company_id.display_name,
            'budget': self.budget_id.name if self.budget_id else 'All',
            'lines': data,
        })
