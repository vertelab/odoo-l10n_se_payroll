# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from pytz import utc
from datetime import date, datetime, time
from odoo import fields
from odoo.tests import common, Form

import logging
_logger = logging.getLogger(__name__)

# Test with somthing like this
# $ sudo service odoo stop
# $ sudo su odoo
# $ odoo --test-tags /l10n_se_payroll_tiichri -c /etc/odoo/odoo.conf
# $ odoo -c /etc/odoo/odoo.conf -d DATABASNAMN -i l10n_se_hr_payroll_tiichri --test-enable
# $ odoo -c /etc/odoo/odoo.conf -d odoo-tiichri -i l10n_se_hr_payroll_tiichri --test-enable
#

class TestPayslipFebruary(common.SavepointCase):

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

        payslip_form = Form(cls.env['hr.payslip'])
        payslip_form.employee_id = employee_id
        payslip_form.date_from = cls.date_start
        payslip_form.date_to = cls.date_stop
        payslip_form.period_id = cls.period
        payslip_form.contract_id = contract_id
        payslip_form.struct_id = cls.struct
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
        cls.date_start = fields.Date.from_string('2022-02-01')
        cls.date_stop = fields.Date.from_string('2022-02-28')
        cls.company = cls.env['res.company'].search([('name', '=', 'Aronssons Montage AB')])
        cls.struct = cls.env['hr.payroll.structure'].search([('code', '=', 'bas2018-tj')])

        cls.fiscal_year = cls.env['account.fiscalyear'].create({
            'name': 'Unittest fiscal year',
            'code': 'UFY',
            'company_id': cls.company.id,
            'date_start': cls.date_start,
            'date_stop': cls.date_stop,
        })

        cls.period = cls.env['account.period'].create({
            'name': 'Unittest period',
            'fiscalyear_id': cls.fiscal_year.id,
            'date_start': cls.date_start,
            'date_stop': cls.date_stop,
        })

        
        # ~ Leave of Absence less than 5 days = pem
        # ~ Leave of Absence more than 5 days = pem_5
        
        # Asse Aronsson -- Låt stå! :-) Inte sjuk i februari
        cls.employee_asse = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_asse_employee')  # asse_employee
        # ~ cls.asse_kar = self.create_leave(cls.employee_asse,'sjk_kar',"2022-01-07","2022-01-07",1.0)
            
        # Frans Filipsson -- Låt stå! :-) Inte sjuk i februari
        cls.employee_frans = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_frans_employee')  # frans_employee
        # ~ cls.frans_kar = self.create_leave(cls.employee_frans,'sjk_kar',"2022-01-07","2022-01-07",1.0)
            
        # Doris Dahlin
        cls.employee_doris = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_doris_employee')  # doris_employee
        cls.doris_201 = cls._create_leave(cls.employee_doris, "sjk_kar" ,"2022-02-01","2022-02-01",1)
        cls.doris_202 = cls._create_leave(cls.employee_doris, "sjk_214" ,"2022-02-02","2022-02-03",2)
        cls.doris_203 = cls._create_leave(cls.employee_doris, "sjk_kar" ,"2022-02-07","2022-02-07",1)
        cls.doris_204 = cls._create_leave(cls.employee_doris, "sjk_214" ,"2022-02-08","2022-02-10",3)


        # Camilla Cobolt
        cls.employee_camilla = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_camilla_employee')  # camilla_employee
        cls.camilla_201 = cls._create_leave(cls.employee_camilla, "sjk_kar" ,"2022-02-03","2022-02-03",1)
        cls.camilla_202 = cls._create_leave(cls.employee_camilla, "sjk_214" ,"2022-02-04","2022-02-04",1)
        cls.camilla_203 = cls._create_leave(cls.employee_camilla, "sjk_214" ,"2022-02-07","2022-02-11",5)

        # Gustav Groth -- Låt stå! :-) Inte sjuk i februari
        cls.employee_gustav = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_gustav_employee')  # gustav_employee
        # ~ cls.gustav_kar = self.create_leave(cls.employee_gustav,'sjk_kar',"2022-01-07","2022-01-07",1.0)
        
        # Helmer Henriksson
        cls.employee_helmer = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_helmer_employee')  # helmer_employee
        cls.helmer_1 = cls._create_leave(cls.employee_helmer, "sjk_kar" ,"2022-02-03","2022-02-03",1)
        cls.helmer_2 = cls._create_leave(cls.employee_helmer, "sjk_214" ,"2022-02-04","2022-02-04",1)

        # Karin Kullberg
        # Anställning per timme, påbörjad 2022-06-01
       

    ## Test 1
    def test_asse(self):   
        payslip_form = self._create_payslip(self.employee_asse, self.employee_asse.contract_id, [
                {'code': 'kvaltim','amount': 7.0},
            ])

        _logger.warning(f"--------------")

        for line in payslip_form.input_line_ids:
            if line.amount != 0.0:
                _logger.warning(f"{line.name=} {line.amount_qty=} {line.amount=}")

        _logger.warning(f"--------------") 

        for worked_day in payslip_form.worked_days_line_ids:
            _logger.warning(f"{worked_day.name=} {worked_day.number_of_hours=}")

        _logger.warning(f"--------------") 

        for detail in payslip_form.dynamic_filtered_payslip_lines:
            _logger.warning(f"line id from input: {detail.name} {detail.total}")
            if detail.code == 'net':
                self.assertAlmostEqual(detail.total, 27680.0)


    ## Test 4
    def test_frans(self):
        payslip_form = self._create_payslip(self.employee_frans, self.employee_frans.contract_id, [
                {'code': 'kvaltim','amount': 4.0},
                # ~ {'code': 'mertidtim','amount': 2.0},
            ])

        _logger.warning(f"--------------")

        for line in payslip_form.input_line_ids:
            if line.amount != 0.0:
                _logger.warning(f"{line.name=} {line.amount_qty=} {line.amount=}")

        _logger.warning(f"--------------") 

        for worked_day in payslip_form.worked_days_line_ids:
            _logger.warning(f"{worked_day.name=} {worked_day.number_of_hours=}")

        _logger.warning(f"--------------") 

        for detail in payslip_form.dynamic_filtered_payslip_lines:
            _logger.warning(f"line id from input: {detail.name} {detail.total}")
            if detail.code == 'net':
                self.assertAlmostEqual(detail.total, 25468.0)
        
    ## Test 3
    def test_doris(self):
        payslip_form = self._create_payslip(self.employee_doris, self.employee_doris.contract_id, [
                {'code': 'kvaltim','amount': 2.0},
                {'code': 'mertidtim','amount': 8.0},
            ])

        _logger.warning(f"--------------")

        for line in payslip_form.input_line_ids:
            if line.amount != 0.0:
                _logger.warning(f"{line.name=} {line.amount_qty=} {line.amount=}")

        _logger.warning(f"--------------")

        for worked_day in payslip_form.worked_days_line_ids:
            _logger.warning(f"{worked_day.name=} {worked_day.number_of_hours=}")

        _logger.warning(f"--------------")    

        for detail in payslip_form.dynamic_filtered_payslip_lines:
            _logger.warning(f"line id from input: {detail.name} {detail.total}")
            if detail.code == 'net':
                self.assertAlmostEqual(detail.total, 9067.0)   

    ## Test 2
    def test_camilla(self):
        payslip_form = self._create_payslip(self.employee_camilla, self.employee_camilla.contract_id, [
                # ~ {'code': 'kvaltim','amount': 2.0},
                # ~ {'code': 'mertidtim','amount': 8.0},
            ])

        _logger.warning(f"--------------")

        for line in payslip_form.input_line_ids:
            if line.amount != 0.0:
                _logger.warning(f"{line.name=} {line.amount_qty=} {line.amount=}")

        _logger.warning(f"--------------")

        for worked_day in payslip_form.worked_days_line_ids:
            _logger.warning(f"{worked_day.name=} {worked_day.number_of_hours=}")

        _logger.warning(f"--------------")    

        for detail in payslip_form.dynamic_filtered_payslip_lines:
            _logger.warning(f"line id from input: {detail.name} {detail.total}")
            if detail.code == 'net':
                self.assertAlmostEqual(detail.total, 24895.0)   

    ## Test 5
    def test_gustav(self):
        payslip_form = self._create_payslip(self.employee_gustav, self.employee_gustav.contract_id, [
                {'code': 'kvaltim','amount': 4.0},
            ])

        _logger.warning(f"--------------")

        for line in payslip_form.input_line_ids:
            if line.amount != 0.0:
                _logger.warning(f"{line.name=} {line.amount_qty=} {line.amount=}")

        _logger.warning(f"--------------")

        for worked_day in payslip_form.worked_days_line_ids:
            _logger.warning(f"{worked_day.name=} {worked_day.number_of_hours=}")

        _logger.warning(f"--------------")    

        for detail in payslip_form.dynamic_filtered_payslip_lines:
            _logger.warning(f"line id from input: {detail.name} {detail.total}")
            if detail.code == 'net':
                self.assertAlmostEqual(detail.total, 21963.0)   

    ## Test 6
    def test_helmer(self):
        payslip_form = self._create_payslip(self.employee_helmer, self.employee_helmer.contract_id, [
                {'code': 'kvaltim','amount': 4.0},
            ])

        _logger.warning(f"--------------")

        for line in payslip_form.input_line_ids:
            if line.amount != 0.0:
                _logger.warning(f"{line.name=} {line.amount_qty=} {line.amount=}")

        _logger.warning(f"--------------")

        for worked_day in payslip_form.worked_days_line_ids:
            _logger.warning(f"{worked_day.name=} {worked_day.number_of_hours=}")

        _logger.warning(f"--------------")    

        for detail in payslip_form.dynamic_filtered_payslip_lines:
            _logger.warning(f"line id from input: {detail.name} {detail.total}")
            if detail.code == 'net':
                self.assertAlmostEqual(detail.total, 16290.0)
