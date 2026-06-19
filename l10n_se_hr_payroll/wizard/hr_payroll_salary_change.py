# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2024- Vertel AB (<https://vertel.se>).
#
##############################################################################

from odoo import _, fields, models, api
from datetime import timedelta


class HrPayrollSalaryChange(models.TransientModel):
    _name = 'hr.payroll.salary.change'
    _description = 'Löneändring'

    company_id = fields.Many2one(
        'res.company', string='Företag', required=True,
        default=lambda self: self.env.company)

    employee_ids = fields.Many2many(
        'hr.employee', string='Anställda',
        domain="[('company_id', '=', company_id)]",
        help="Välj de anställda som ska få löneändring")

    change_type = fields.Selection([
        ('percentage', 'Procentuell förändring'),
        ('absolute', 'Fast nytt belopp'),
    ], string='Typ', default='percentage', required=True)

    percentage = fields.Float(
        string='Procent (%)', default=2.5,
        help="Positivt = ökning. T.ex. 2.5 för 2.5% ökning")

    new_wage = fields.Float(
        string='Ny månadslön',
        help="Samma nya lön för samtliga valda anställda")

    effective_date = fields.Date(
        string='Gäller fr.o.m.', required=True,
        default=fields.Date.today)

    preview_text = fields.Text(
        string='Förhandsvisning', readonly=True,
        compute='_compute_preview')

    @api.depends('employee_ids', 'change_type', 'percentage', 'new_wage')
    def _compute_preview(self):
        for wiz in self:
            if not wiz.employee_ids:
                wiz.preview_text = 'Välj anställda för att se förhandsvisning.'
                continue
            lines = []
            total_old = total_new = 0.0
            name_w = max(len(e.name) for e in wiz.employee_ids)
            for emp in wiz.employee_ids.sorted('name'):
                contract = emp.contract_id
                old = contract.wage if contract else 0.0
                if wiz.change_type == 'percentage':
                    new = round(old * (1 + wiz.percentage / 100))
                else:
                    new = wiz.new_wage or old
                total_old += old
                total_new += new
                diff = new - old
                sign = '+' if diff >= 0 else ''
                lines.append(
                    f'{emp.name:<{name_w}}  {old:>10,.0f}  →  {new:>10,.0f} kr  ({sign}{diff:,.0f} kr)')
            lines.append('─' * (name_w + 40))
            lines.append(
                f'{"Totalt":<{name_w}}  {total_old:>10,.0f}  →  {total_new:>10,.0f} kr  (+{total_new - total_old:,.0f} kr)')
            wiz.preview_text = '\n'.join(lines)

    def apply_salary_changes(self):
        """Stäng gamla kontrakt och skapa nya med uppdaterad lön."""
        self.ensure_one()
        Contract = self.env['hr.contract']
        created = 0

        for employee in self.employee_ids:
            old = employee.contract_id
            if not old:
                continue
            if self.change_type == 'percentage':
                new_wage_val = round(old.wage * (1 + self.percentage / 100))
            else:
                new_wage_val = self.new_wage
            if new_wage_val == old.wage:
                continue

            day_before = self.effective_date - timedelta(days=1)
            if old.date_start and day_before < old.date_start:
                day_before = old.date_start

            old.write({'date_end': day_before})

            old.copy(default={
                'date_start': self.effective_date,
                'date_end': False,
                'wage': new_wage_val,
                'name': f"{old.name or employee.name} (fr.o.m. {self.effective_date})",
                'first_contract_date': old.first_contract_date or old.date_start,
            })
            created += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Löneändring klar'),
                'message': _('%d kontrakt uppdaterade') % created,
                'type': 'success',
            }
        }
