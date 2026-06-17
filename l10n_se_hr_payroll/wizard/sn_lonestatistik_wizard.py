from odoo import models, fields, api, _
import csv
import base64
import io
from datetime import date


class SnLonestatistikWizard(models.TransientModel):
    _name = 'sn.lonestatistik.wizard'
    _description = 'Svenskt Näringsliv Lönestatistik'

    year = fields.Selection(selection=lambda self: self._get_year_selection(), string="Year", required=True, default=lambda self: str(date.today().year))
    company_id = fields.Many2one('res.company', string="Company", required=True, default=lambda self: self.env.company)
    csv_file = fields.Binary(string="CSV File", readonly=True)
    csv_filename = fields.Char(string="Filename", default="salary_statistics.csv")

    def _get_year_selection(self):
        year = date.today().year
        return [(str(y), str(y)) for y in range(year - 10, year + 1)]

    def action_export_csv(self):
        self.ensure_one()
        csv_content = self._generate_csv()
        self.write({
            'csv_file': base64.b64encode(csv_content.encode('utf-8-sig')),
            'csv_filename': f"lonestatistik_{self.year}_09.csv",
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sn.lonestatistik.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {},
        }

    def action_print_report(self):
        return self.env.ref('l10n_se_hr_payroll.action_report_sn_lonestatistik').report_action(self)

    def _generate_csv(self):
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')
        writer.writerow([
            'Personnummer', 'Kon', 'Fodelsear', 'Anstallningsform',
            'Arbetstid_timmar', 'NYK_kod', 'Grundlon', 'Rorliga_tillagg',
            'Formaner', 'Avdrag', 'Totalt_utbetalt'
        ])

        period_start = date(int(self.year), 9, 1)
        period_end = date(int(self.year), 9, 30)

        employees = self.env['hr.employee'].search([
            ('company_id', '=', self.company_id.id),
            ('active', '=', True),
        ])

        for employee in employees:
            contract = employee.contract_id
            if not contract or contract.state != 'open':
                continue

            payslip = self.env['hr.payslip'].search([
                ('employee_id', '=', employee.id),
                ('date_from', '=', period_start),
                ('date_to', '=', period_end),
                ('state', 'in', ('done', 'paid')),
                ('company_id', '=', self.company_id.id),
            ], limit=1)

            if not payslip:
                continue

            gl = bl = nl = total_skatt = sa = 0.0
            for line in payslip.line_ids:
                code = line.salary_rule_id.code
                val = abs(line.total)
                if code == 'gl':
                    gl = val
                elif code == 'bl':
                    bl = val
                elif code == 'nl':
                    nl = val
                elif code == 'total_skatt':
                    total_skatt = val
                elif code == 'sa':
                    sa = val

            gender = {'male': 'Man', 'female': 'Kvinna', 'other': 'Annat'}.get(employee.gender, '')
            birth_year = str(employee.birthday.year) if employee.birthday else ''
            employment_form = 'Heltid' if contract.schedule_pay == 'monthly' else 'Deltid'

            nyk_code = employee.nyk_id.code if employee.nyk_id else ''

            rorliga = bl - gl if bl > gl else 0.0
            formaner = sum(abs(line.total) for line in payslip.line_ids
                          if line.salary_rule_id.code in ('fm', 'fmn_total', 'forman_carbru', 'drivmedel_fmn'))
            avdrag = total_skatt

            writer.writerow([
                employee.registration_number or '',
                gender,
                birth_year,
                employment_form,
                '',  # arbetstid timmar
                nyk_code,
                round(gl, 2),
                round(rorliga, 2),
                round(formaner, 2),
                round(avdrag, 2),
                round(nl, 2),
            ])

        return output.getvalue()
