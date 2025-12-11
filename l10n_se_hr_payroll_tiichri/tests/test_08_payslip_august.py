# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from pytz import utc
from datetime import date, datetime, time
from odoo import fields
from odoo.tests import Form, tagged
from odoo.tests.common import TransactionCase
from odoo.tests.common import tagged

import logging
_logger = logging.getLogger(__name__)

# Test with somthing like this
# $ sudo service odoo stop
# $ sudo su odoo
# $ odoo --test-tags /l10n_se_payroll_tiichri -c /etc/odoo/odoo.conf
# $ odoo -c /etc/odoo/odoo.conf -d DATABASNAMN -i l10n_se_hr_payroll_tiichri --test-enable
# $ odoo -c /etc/odoo/odoo.conf -d odoo-tiichri -i --test-enable
#

@tagged('l10n_se_payroll_tiichri', 'august')
class TestPayslipAugust(TransactionCase):

    @classmethod
    def _create_leave(cls, employee_id, code, date_from, date_to, number_of_days): 
        cls.leave_type = cls.env["hr.leave.type"].search([('code', '=', code)])

        leave_form = Form(cls.env['hr.leave'])
        leave_form.employee_id = employee_id
        leave_form.name = "test1"
        leave_form.date_from = date_from
        leave_form.request_date_from = date_from
        leave_form.date_to = date_to
        leave_form.request_date_to = date_to
        leave_form.name = number_of_days
        leave_form.number_of_days = number_of_days
        leave_form.holiday_type = 'employee'
        leave_form.holiday_status_id = cls.leave_type

        leave_form = leave_form.save()
    
        if leave_form.state == 'confirm':
            leave_form.action_validate()
            
        return leave_form

    @classmethod
    def _create_payslip(cls, employee_id, contract_id, input_recs): 

        _logger.info(f"TEST PAYSLIP: Employee: {employee_id.name} | Period: {cls.period.name} | Inputs: {input_recs}")
        payslip_form = Form(cls.env['hr.payslip'])
        payslip_form.employee_id = employee_id
        payslip_form.date_from = cls.date_start
        payslip_form.period_id = cls.period
        payslip_form.contract_id = contract_id
        payslip_form = payslip_form.save()

        payslip_form.action_payslip_draft()

        payslip_form.onchange_dates()  
        payslip_form.compute_sheet()
    
        for input_rec in input_recs:
            line = cls.env["hr.payslip.input"].search([('code','=',input_rec['code']),('payslip_id','=',payslip_form.id)])
            line.amount = input_rec['amount']
            line.amount_qty = input_rec['amount']              
        return payslip_form

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.date_start = fields.Date.from_string('2022-08-01')
        cls.date_stop = fields.Date.from_string('2022-08-31')
        cls.company = cls.env['res.company'].search([('name', '=', 'Aronssons Montage AB')])
        cls.struct = cls.env['hr.payroll.structure'].search([('code', '=', 'bas2018-tj')])

        cls.fiscal_year = cls.env['account.fiscalyear'].create({
            'name': 'Unittest fiscal year',
            'code': 'UFY',
            'company_id': cls.company.id,
            'date_start': cls.date_start,
            'date_stop': cls.date_stop,
        })

        cls.period_type = cls.env['date.range.type'].create({
            'name': 'Unittest Month Type',
            'company_id': cls.company.id,
            'allow_overlap': True
        })

        cls.period = cls.env['account.period'].create({
            'name': 'Unittest period',
            'company_id': cls.company.id,
            'fiscalyear_id': cls.fiscal_year.id,
            'date_start': cls.date_start,
            'date_end': cls.date_stop,
            'type_id': cls.period_type.id,
        })


        # Asse Aronsson -- Låt stå! :-) Inte sjuk i juli
        cls.employee_asse = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_asse_employee')  # asse_employee
        cls.asse_801 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_asse_801') 
        cls.asse_802 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_asse_802')
        cls.asse_803 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_asse_803')
        cls.asse_804 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_asse_804')
            
        # Frans Filipsson
        cls.employee_frans = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_frans_employee')  # frans_employee
        cls.frans_801 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_frans_801') 
        cls.frans_802 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_frans_802')
        cls.frans_803 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_frans_803')

        # Doris Dahlin
        cls.employee_doris = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_doris_employee')  # doris_employee
        cls.doris_801 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_doris_801')
        cls.doris_802 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_doris_802')
        cls.doris_803 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_doris_803')

        # Camilla Cobolt
        cls.employee_camilla = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_camilla_employee')  # camilla_employee
        cls.camilla_801 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_camilla_801')
        cls.camilla_802 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_camilla_802')
        cls.camilla_803 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_camilla_803')

        # Gustav Groth
        cls.employee_gustav = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_gustav_employee')  # gustav_employee
        cls.gustav_801 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_gustav_801')
        cls.gustav_802 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_gustav_802')
       
        # Helmer Henriksson
        cls.employee_helmer = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_helmer_employee')  # helmer_employee
        cls.helmer_801 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_helmer_801')
        cls.helmer_802 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_helmer_802')
        cls.helmer_803 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_helmer_803')

        # Karin Kullberg
        cls.employee_karin = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_karin_employee')  # karin_employee
        cls.karin_801 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_karin_801')
        cls.karin_802 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_karin_802')
        
       

    ## Test xx
    def test_asse(self):   
        payslip_form = self._create_payslip(self.employee_asse, self.employee_asse.contract_id, [
                {'code': 'mertidtim','amount': 8.0},
                {'code': 'kvaltim','amount': 6.0},
            ])

        found_net = False
        for detail in payslip_form.dynamic_filtered_payslip_lines:
            if detail.code == 'net':
                # FACIT: Ska vara 25148.0
                self.assertAlmostEqual(detail.total, 25148.0, msg=f"Wrong net pay for Asse! Got: {detail.total}, expected 25148.0")
                _logger.info(f"SUCCESS: Asse net pay correct: {detail.total}")
                found_net = True
        
        self.assertTrue(found_net, "Could not find field 'net' for Asse.")

    ## Test xx
    def test_frans(self):
        payslip_form = self._create_payslip(self.employee_frans, self.employee_frans.contract_id, [
                {'code': 'mertidtim','amount': 8.0},
                {'code': 'kvaltim','amount': 3.0},
            ])

        found_net = False
        for detail in payslip_form.dynamic_filtered_payslip_lines:
            if detail.code == 'net':
                found_net = True
                # FACIT: Ska vara 20013.0
                self.assertAlmostEqual(detail.total, 20013.0, msg=f"Wrong net pay for Frans! Got: {detail.total}, expected 20013.0")
                _logger.info(f"SUCCESS: Frans net pay correct: {detail.total}")
                found_net = True
        
        self.assertTrue(found_net, "Could not find field 'net' for Frans.")
        
        
    ## Doris xx
    def test_doris(self):
        payslip_form = self._create_payslip(self.employee_doris, self.employee_doris.contract_id, [
                {'code': 'mertidtim','amount': 8.0},
                {'code': 'kvaltim','amount': 2.0},
            ])

        found_net = False
        for detail in payslip_form.dynamic_filtered_payslip_lines:
            if detail.code == 'net':
                found_net = True
                # FACIT: Ska vara 8815.0
                self.assertAlmostEqual(detail.total, 8815.0, msg=f"Wrong net pay for Doris! Got: {detail.total}, expected 8815.0")
                _logger.info(f"SUCCESS: Doris net pay correct: {detail.total}")
                found_net = True
        
        self.assertTrue(found_net, "Could not find field 'net' for Doris.")


    ## Camilla xx
    def test_camilla(self):
        payslip_form = self._create_payslip(self.employee_camilla, self.employee_camilla.contract_id, [
                {'code': 'mertidtim','amount': 8.0},
                {'code': 'kvaltim','amount': 4.0},
            ])

        found_net = False
        for detail in payslip_form.dynamic_filtered_payslip_lines:
            if detail.code == 'net':
                found_net = True
                # FACIT: Ska vara 13165.0
                self.assertAlmostEqual(detail.total, 13165.0, msg=f"Wrong net pay for Camilla! Got: {detail.total}, expected 13165.0")
                _logger.info(f"SUCCESS: Camilla net pay correct: {detail.total}")
                found_net = True
        
        self.assertTrue(found_net, "Could not find field 'net' for Camilla.")

    ## Test xx
    def test_gustav(self):
        payslip_form = self._create_payslip(self.employee_gustav, self.employee_gustav.contract_id, [
                {'code': 'mertidtim','amount': 8.0},
                {'code': 'kvaltim','amount': 4.0},
            ])

        found_net = False
        for detail in payslip_form.dynamic_filtered_payslip_lines:
            if detail.code == 'net':
                found_net = True
                # FACIT: Ska vara 15209.0
                self.assertAlmostEqual(detail.total, 15209.0, msg=f"Wrong net pay for Gustav! Got: {detail.total}, expected 15209.0")
                _logger.info(f"SUCCESS: Gustav net pay correct: {detail.total}")
                found_net = True

        self.assertTrue(found_net, "Could not find field 'net' for Gustav.")

    ## Test xx
    def test_helmer(self):
        payslip_form = self._create_payslip(self.employee_helmer, self.employee_helmer.contract_id, [
                {'code': 'mertidtim','amount': 8.0},
                {'code': 'kvaltim','amount': 10.0},
            ])

        found_net = False
        for detail in payslip_form.dynamic_filtered_payslip_lines:
            if detail.code == 'net':
                found_net = True
                # FACIT: Ska vara 11484.0
                self.assertAlmostEqual(detail.total, 11484.0, msg=f"Wrong net pay for Helmer! Got: {detail.total}, expected 11484.0")
                _logger.info(f"SUCCESS: Helmer net pay correct: {detail.total}")
                found_net = True

        self.assertTrue(found_net, "Could not find field 'net' for Helmer.")

    ## Test xx
    def test_karin(self):
        payslip_form = self._create_payslip(self.employee_karin, self.employee_karin.contract_id, [
                {'code': 'mertidtim','amount': 8.0},
                {'code': 'kvaltim','amount': 8.0},
            ])

        found_net = False
        for detail in payslip_form.dynamic_filtered_payslip_lines:
            if detail.code == 'net':
                found_net = True
                # FACIT: Ska vara 15206.0
                self.assertAlmostEqual(detail.total, 15206.0, msg=f"Wrong net pay for Karin! Got: {detail.total}, expected 15206.0")
                _logger.info(f"SUCCESS: Karin net pay correct: {detail.total}")
                found_net = True

        self.assertTrue(found_net, "Could not find field 'net' for Karin.")
