# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

# DOCUMENTAION // RECOURCES
# https://docs.python.org/3/library/unittest.html
# https://www.odoo.com/forum/help-1/using-self-env-to-go-over-all-module-record-and-create-new-record-in-another-module-144407
# https://stackoverflow.com/questions/17534345/typeerror-missing-1-required-positional-argument-self
from pytz import utc
from datetime import date, datetime, time
from odoo import fields
from odoo.tests import Form
from odoo.tests.common import TransactionCase
import logging

_logger = logging.getLogger(__name__)


# Test with somthing like this
# $ sudo service odoo stop
# $ sudo su odoo
# $ odoo --test-tags /l10n_se_payroll_tiichri -c /etc/odoo/odoo.conf
# $ odoo -c /etc/odoo/odoo.conf -d DATABASNAMN -i l10n_se_hr_payroll_tiichri --test-enable
# $ odoo -c /etc/odoo/odoo.conf -d odoo-tiichri4 -i l10n_se_hr_payroll_tiichri --test-enable



class TestPayslipJanuary(TransactionCase):


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
        cls.date_start = fields.Date.from_string('2022-01-01')
        cls.date_stop = fields.Date.from_string('2022-01-31')
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

        # # Asse Aronsson
        # cls.employee_asse = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_asse_employee')
        # cls.asse_1 = cls._create_leave(cls.employee_asse, "sjk_kar" ,"2022-01-07","2022-01-07",1)
        # cls.asse_2 = cls._create_leave(cls.employee_asse, "sjk_kar" ,"2022-01-12","2022-01-12",1)
        # cls.asse_3 = cls._create_leave(cls.employee_asse, "sjk_214" ,"2022-01-13","2022-01-13",1)
        # cls.asse_4 = cls._create_leave(cls.employee_asse, "sjk_214" ,"2022-01-24","2022-01-24",1)
        # cls.asse_5 = cls._create_leave(cls.employee_asse, "vab" ,"2022-01-25","2022-01-25",1)
        # cls.asse_6 = cls._create_leave(cls.employee_asse, "vab", "2022-01-26", "2022-01-26",1)
        # cls.asse_7 = cls._create_leave(cls.employee_asse, "Leave of Absence less than 5 days", "2022-01-03", "2022-01-03",1)
        # cls.asse_8 = cls._create_leave(cls.employee_asse, "Leave of Absence less than 5 days", "2022-01-14", "2022-01-14",1)
        # cls.asse_9 = cls._create_leave(cls.employee_asse, "Leave of Absence less than 5 days", "2022-01-17", "2022-01-17",1)
        # cls.asse_10 = cls._create_leave(cls.employee_asse, "Leave of Absence less than 5 days", "2022-01-18", "2022-01-18",1)
        # cls.asse_11 = cls._create_leave(cls.employee_asse, "Leave of Absence less than 5 days", "2022-01-19", "2022-01-19",1)
        # cls.asse_12 = cls._create_leave(cls.employee_asse, "Leave of Absence more than 5 days", "2022-01-20", "2022-01-20",1)
            
        # # Frans Filipsson
        # cls.employee_frans = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_frans_employee')  # frans_employee
        # cls.frans_1 = cls._create_leave(cls.employee_frans, "sjk_kar" ,"2022-01-07","2022-01-07",1)
        # cls.frans_2 = cls._create_leave(cls.employee_frans, "sjk_kar" ,"2022-01-10","2022-01-10",1)
        # cls.frans_3 = cls._create_leave(cls.employee_frans, "sjk_214" ,"2022-01-11","2022-01-12",2)
        # cls.frans_4 = cls._create_leave(cls.employee_frans, "Leave of Absence less than 5 days" ,"2022-01-20","2022-01-21",2)
        # cls.frans_5 = cls._create_leave(cls.employee_frans, "Leave of Absence less than 5 days" ,"2022-01-24","2022-01-26",3)
        # cls.frans_6 = cls._create_leave(cls.employee_frans, "Leave of Absence more than 5 days" ,"2022-01-27","2022-01-27",1)

        # Doris Dahlin
        cls.employee_doris = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_doris_employee')  # doris_employee
        cls.doris_1 = cls._create_leave(cls.employee_doris, "sjk_kar" ,"2022-01-04","2022-01-04",1)
        cls.doris_2 = cls._create_leave(cls.employee_doris, "sjk_214" ,"2022-01-05","2022-01-05",1)
        cls.doris_3 = cls._create_leave(cls.employee_doris, "sjk_kar" ,"2022-01-10","2022-01-10",1)
        cls.doris_4 = cls._create_leave(cls.employee_doris, "sjk_214" ,"2022-01-11","2022-01-12",2)
        cls.doris_5 = cls._create_leave(cls.employee_doris, "Leave of Absence less than 5 days" ,"2022-01-13","2022-01-13",1)

        # Camilla Cobolt -- Låt stå! :-) Inte sjuk i januari
        # ~ cls.employee_camilla = self.env.ref('hr_camilla_employee')  # camilla_employee
        # ~ cls.camilla_kar = self.create_leave(cls.employee_camilla,'sjk_kar',"2022-01-07","2022-01-07",1.0)
        # ~ cls.camilla_kar.action_approve()
        # ~ cls.camilla_kar = self.create_leave(cls.employee_camilla,'sjk_kar',"2022-01-10","2022-01-12",3.0)
        # ~ cls.camilla_kar.action_approve()


        # # Gustav Groth
        # cls.employee_gustav = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_gustav_employee')  # gustav_employee
        # cls.gustav_kar = cls._create_leave(cls.employee_gustav.id, "sjk_kar" ,"2022-01-07","2022-01-07",1)
        # cls.gustav_kar = cls._create_leave(cls.employee_gustav.id, "sjk_214" ,"2022-01-10","2022-01-14",5)
        # cls.gustav_kar = cls._create_leave(cls.employee_gustav.id, "sjk_214" ,"2022-01-17","2022-01-21",5)
        # cls.gustav_kar = cls._create_leave(cls.employee_gustav.id, "sjk_214" ,"2022-01-24","2022-01-25",2)
        
        # # Helmer Henriksson
        # cls.employee_helmer = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_helmer_employee')  # helmer_employee
        # cls.helmer_kar = cls._create_leave(cls.employee_helmer.id, "sjk_kar" ,"2022-01-04","2022-01-04",1)

    def test_doris(self):
        payslip_form = self._create_payslip(self.employee_doris, self.employee_doris.contract_id, [])

        for line in payslip_form.input_line_ids:
            if line.amount != 0.0:
                _logger.info(f"{line.name=} {line.amount_qty=} {line.amount=}", "yellow", 4, "line.amount != 0.0")

        _logger.info(f"--------------")

        for worked_day in payslip_form.worked_days_line_ids:
            _logger.info(f"{worked_day.name=} {worked_day.number_of_hours=}", "magenta", 4, "worked_day in payslip_form.worked_days_line_ids")

        _logger.info(f"--------------")    

        for detail in payslip_form.dynamic_filtered_payslip_lines:
            _logger.info(f"line id from input: {detail.name} {detail.total}", "cyan", 4, "detail in payslip_form.dynamic_filtered_payslip_lines")
            if detail.code == 'net':
                _logger.info(detail.total, "green", 10, "netto")
                self.assertAlmostEqual(detail.total, 19538.0)   
