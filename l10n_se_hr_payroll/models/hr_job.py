# -*- coding: utf-8 -*-
from odoo import fields, models, api


class HrJob(models.Model):
    _inherit = 'hr.job'

    company_currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id',
        string='Företagsvaluta')

    nyk_id = fields.Many2one(
        'hr.nyk',
        string='NYK-kod',
        help='Swedish Occupational Classification Code (NYK)'
    )

    # ---- Salary statistics ----

    employee_count = fields.Integer(
        string='Antal anställda',
        compute='_compute_statistics', store=True,
        help='Antal anställda med denna befattning')

    avg_wage = fields.Float(
        string='Snittlön',
        compute='_compute_statistics', store=True,
        help='Genomsnittlig månadslön för anställda med denna befattning')

    min_wage = fields.Float(
        string='Lägsta lön',
        compute='_compute_statistics', store=True)

    max_wage = fields.Float(
        string='Högsta lön',
        compute='_compute_statistics', store=True)

    male_count = fields.Integer(
        string='Män',
        compute='_compute_statistics', store=True)

    female_count = fields.Integer(
        string='Kvinnor',
        compute='_compute_statistics', store=True)

    other_gender_count = fields.Integer(
        string='Annat/ej angivet',
        compute='_compute_statistics', store=True)

    avg_age = fields.Float(
        string='Snittålder',
        compute='_compute_statistics', store=True,
        help='Genomsnittlig ålder för anställda med denna befattning')

    avg_seniority_days = fields.Integer(
        string='Snitt anställningstid (dagar)',
        compute='_compute_statistics', store=True,
        help='Genomsnittlig anställningstid i dagar')

    wage_trend = fields.Float(
        string='Lönetrend (%)',
        compute='_compute_statistics', store=True,
        help='Procentuell löneförändring senaste året (baserat på kontrakt)')

    @api.depends('employee_ids', 'employee_ids.contract_id', 'employee_ids.contract_id.wage',
                 'employee_ids.gender', 'employee_ids.birthday', 'employee_ids.contract_id.date_start')
    def _compute_statistics(self):
        for job in self:
            employees = job.employee_ids.filtered(lambda e: e.active)
            contracts = employees.mapped('contract_id').filtered(lambda c: c.active)

            job.employee_count = len(employees)
            if contracts:
                wages = contracts.mapped('wage')
                job.avg_wage = sum(wages) / len(wages) if wages else 0.0
                job.min_wage = min(wages) if wages else 0.0
                job.max_wage = max(wages) if wages else 0.0
            else:
                job.avg_wage = job.min_wage = job.max_wage = 0.0

            job.male_count = len(employees.filtered(lambda e: e.gender == 'male'))
            job.female_count = len(employees.filtered(lambda e: e.gender == 'female'))
            job.other_gender_count = len(employees.filtered(lambda e: e.gender not in ('male', 'female')))

            ages = []
            seniorities = []
            today = fields.Date.today()
            for emp in employees:
                if emp.birthday:
                    age = (today - emp.birthday).days / 365.25
                    ages.append(age)
                first_contract = emp.contract_id.first_contract_date or emp.contract_id.date_start
                if first_contract:
                    seniorities.append((today - first_contract).days)

            job.avg_age = sum(ages) / len(ages) if ages else 0.0
            job.avg_seniority_days = int(sum(seniorities) / len(seniorities)) if seniorities else 0

            # Wage trend: compare current wage to oldest ended contract
            trend = 0.0
            if contracts:
                for emp in employees:
                    all_contracts = self.env['hr.contract'].search([
                        ('employee_id', '=', emp.id),
                    ], order='date_start')
                    if len(all_contracts) >= 2:
                        oldest_wage = all_contracts[0].wage
                        current_wage = all_contracts[-1].wage
                        if oldest_wage and oldest_wage > 0:
                            trend += ((current_wage - oldest_wage) / oldest_wage) * 100
                if len(employees) > 0 and trend != 0:
                    trend = trend / len(employees)
            job.wage_trend = round(trend, 1)

    # ---- Actions ----

    def action_view_employees(self):
        return {
            'name': 'Anställda',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'view_mode': 'kanban,tree,form',
            'domain': [('job_id', '=', self.id)],
        }
