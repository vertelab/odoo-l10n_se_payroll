from odoo import _, fields, models, api


class VacationDebtReportWizard(models.TransientModel):
    _name = 'vacation.debt.report.wizard'
    _description = 'Vacation Debt Report Wizard'

    company_id = fields.Many2one('res.company', string='Company', required=True,
                                  default=lambda self: self.env.company)
    date_to = fields.Date(string='Beräkningsdatum', required=True,
                           default=fields.Date.today)

    def _get_vacation_debt_data(self):
        employees = self.env['hr.employee'].search([
            ('company_id', '=', self.company_id.id),
            ('active', '=', True),
        ])
        data = []
        total_saved = 0.0
        total_remaining = 0.0
        total_gross = 0.0
        total_employer_fee = 0.0

        for employee in employees:
            contract = employee.contract_id
            if not contract or not contract.wage:
                continue
            saved_days = employee.vacation_saved_remaining
            remaining_days = employee.vacation_paid_remaining
            if not saved_days and not remaining_days:
                continue
            daily_wage = round(contract.wage / 26)
            gross_debt = round(remaining_days * daily_wage)
            employer_fee = round(gross_debt * 0.3142)
            total_debt = gross_debt + employer_fee
            emp_number = employee.registration_number or '000'
            data.append({
                'name': f"{employee.name} ({emp_number})",
                'saved_days': saved_days,
                'remaining_days': remaining_days,
                'daily_wage': daily_wage,
                'gross_debt': gross_debt,
                'employer_fee': employer_fee,
                'total_debt': total_debt,
            })
            total_saved += saved_days
            total_remaining += remaining_days
            total_gross += gross_debt
            total_employer_fee += employer_fee

        total = total_gross + total_employer_fee
        data.append({
            'name': 'TOTALT',
            'saved_days': total_saved,
            'remaining_days': total_remaining,
            'daily_wage': 0,
            'gross_debt': total_gross,
            'employer_fee': total_employer_fee,
            'total_debt': total,
        })
        return data

    def action_print_report(self):
        data = self._get_vacation_debt_data()
        return self.env.ref('l10n_se_hr_payroll.action_report_vacation_debt').report_action(
            [],
            data={
                'date_to': self.date_to,
                'company': self.company_id.display_name,
                'lines': data,
            },
        )
