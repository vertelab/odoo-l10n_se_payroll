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

class TestPayslipMay(common.SavepointCase):



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

        # Asse Aronsson
        cls.employee_asse = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_asse_employee')  # asse_employee
        cls.asse_501 = cls._create_leave(cls.employee_asse, "sjk_kar" ,"2022-05-09","2022-05-09",1)
        cls.asse_502 = cls._create_leave(cls.employee_asse, "sjk_214" ,"2022-05-10","2022-05-13",4)
        cls.asse_503 = cls._create_leave(cls.employee_asse, "sjk_214" ,"2022-05-16","2022-05-18",3)
            
        # Frans Filipsson -- Låt stå! :-) Inte sjuk i maj
        # ~ cls.employee_frans = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_frans_employee')  # frans_employee
        # ~ cls.frans_kar = cls._create_leave(cls.employee_frans.id, "sjk_kar" ,"2022-05-09","2022-05-09",1)
        # ~ cls.frans_kar = cls._create_leave(cls.employee_frans.id, "sjk_214" ,"2022-05-10","2022-05-13",4)
        # ~ cls.frans_kar = cls._create_leave(cls.employee_frans.id, "sjk_214" ,"2022-05-16","2022-05-18",3)

        # Doris Dahlin -- Låt stå! :-) Inte sjuk i maj
        # ~ cls.employee_doris = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_doris_employee')  # doris_employee
        # ~ cls.doris_kar = cls._create_leave(cls.employee_doris.id, "sjk_kar" ,"2022-04-06","2022-04-06",1)
        # ~ cls.doris_kar = cls._create_leave(cls.employee_doris.id, "sjk_214" ,"2022-04-07","2022-04-07",1)
        # ~ cls.doris_kar = cls._create_leave(cls.employee_doris.id, "sjk_214" ,"2022-04-11","2022-04-13",3)

        # Camilla Cobolt -- Låt stå! :-) Inte sjuk i maj
        # ~ cls.employee_camilla = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_camilla_employee')  # camilla_employee
        # ~ cls.camilla_kar = cls._create_leave(cls.employee_camilla.id, "sjk_kar" ,"2022-04-19","2022-04-19",1)
        # ~ cls.camilla_kar = cls._create_leave(cls.employee_camilla.id, "sjk_214" ,"2022-04-20","2022-04-21",2)

        # Gustav Groth -- Låt stå! :-) Inte sjuk i maj
        # ~ cls.employee_gustav = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_gustav_employee')  # gustav_employee
        # ~ cls.gustav_kar = cls._create_leave(cls.employee_gustav.id, "sjk_kar" ,"2022-04-13","2022-04-13",1)
        # ~ cls.gustav_kar = cls._create_leave(cls.employee_gustav.id, "sjk_214" ,"2022-04-14","2022-04-14",1)
        # ~ cls.gustav_kar = cls._create_leave(cls.employee_gustav.id, "sjk_214" ,"2022-04-19","2022-04-22",4)
        # ~ cls.gustav_kar = cls._create_leave(cls.employee_gustav.id, "sjk_214" ,"2022-04-25","2022-04-28",4)
       
        # Helmer Henriksson
        cls.employee_helmer = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_helmer_employee')  # helmer_employee
        cls.helmer_kar = cls._create_leave(cls.employee_helmer.id, "sjk_kar" ,"2022-05-19","2022-05-19",1)
        cls.helmer_kar = cls._create_leave(cls.employee_helmer.id, "sjk_214" ,"2022-05-20","2022-05-20",1)
        cls.helmer_kar = cls._create_leave(cls.employee_helmer.id, "sjk_kar" ,"2022-05-27","2022-05-27",1)
        cls.helmer_kar = cls._create_leave(cls.employee_helmer.id, "sjk_214" ,"2022-05-30","2022-05-30",1)

        # Karin Kullberg
        # Anställning per timme, påbörjad 2022-06-01
        
       

    def test_asse(self):
        payslip = self._create_payslip(cls.employee_asse,'2022-01-25',[
                {'code': 'kvaltim','amount_qty': 2.0},
                {},
            ])
        payslip.compute_slip()
        self.assertEqual(payslip.state, 'draft')
        self.assertAlmostEqual(payslip.net, 29531.0)

    def test_camilla(self):
        pass
