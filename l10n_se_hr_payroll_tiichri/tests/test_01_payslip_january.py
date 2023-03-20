# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

# DOCUMENTAION // RECOURCES
# https://docs.python.org/3/library/unittest.html
# https://www.odoo.com/forum/help-1/using-self-env-to-go-over-all-module-record-and-create-new-record-in-another-module-144407
# https://stackoverflow.com/questions/17534345/typeerror-missing-1-required-positional-argument-self
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
# $ odoo -c /etc/odoo/odoo.conf -d odoo-tiichri4 -i l10n_se_hr_payroll_tiichri --test-enable


class TestPayslipJanuary(common.SavepointCase):


    # ~ def _create_leave(self, employee_id,code,date_from,date_to,number_of_days): 
        # ~ leave = cls.env["hr.leave"].create({    
                            # ~ "holiday_status_id": cls.env["hr.leave.type"].search([('code','=','sjk_kar')]).mapped('id')[0],
                            # ~ "request_date_from": fields.Date.from_string("2022-01-07"),
                            # ~ "request_date_to": fields.Date.from_string("2022-01-07"),
                            # ~ "number_of_days": 1.0,
                            # ~ 'holiday_type': 'employee',
                            # ~ 'employee_id': cls.employee_asse,
                        # ~ })
        # ~ return leave
    
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

        # leave = cls.env["hr.leave"].create({
        #                     "name":"test1",    
        #                     "holiday_status_id": cls.env["hr.leave.type"].search([('code','=', code )]).mapped('id')[0],
        #                     "date_from": date_from,
        #                     "date_to": date_to,
        #                     "number_of_days": number_of_days,
        #                     'holiday_type': 'employee',
        #                     'employee_id': employee_id,
        #                     # ~ 'state': 'confirm',
        #                 })
        # _logger.warning(f"{cls.env["hr.leave.type"].search([('code','=', code )]).mapped('id')[0]=}")
        # _logger.warning(f"{leave.holiday_status_id.time_type=}")

        # _logger.warning(f"leave status id and stuff: {leave.holiday_status_id} {leave.holiday_status_id.display_name}")
        
        # leave.action_approve()
        # leave.action_validate()
        # ~ leave.state = 'draft'
        # ~ leave.state = 'confirm'
        # _logger.warning('jakob ***  %s ' % leave.state)
        # _logger.warning(f"leave state: {leave.state}")
        # leave.action_draft()
        # leave.action_confirm()
        # leave.action_approve()
        if leave_form.state == 'confirm':
            leave_form.action_validate()

        # day_from_fix = datetime.combine(fields.Date.from_string(date_from), time.min)
        # day_to_fix = datetime.combine(fields.Date.from_string(date_to), time.max)

        # vals_list = []
        # work_hours_data = cls.employee_asse.list_work_time_per_day(day_from_fix, day_to_fix)
        # for index, (day_date, work_hours_count) in enumerate(work_hours_data):
        #     vals_list.append(leave_form._timesheet_prepare_line_values(index, work_hours_data, day_date, work_hours_count))
                
        # timesheets = cls.env['account.analytic.line'].sudo().create(vals_list)
        # leave_form.timesheet_ids = [(4, timesheets[0].id)]
        # leave_form = leave_form.save()

        return leave_form
    
    @classmethod
    def _create_payslip(cls, employee_id, contract_id, input_recs): 
        # payslip = cls.env["hr.payslip"].create({
        #                     'employee_id': employee_id.id,
        #                     'date_from': cls.date_start,
        #                     'date_to': cls.date_stop,
        #                     'period_id': cls.period.id,
        #                     'contract_id': contract_id[0].id,
        #                     'struct_id': cls.struct.id,
        #     })

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

        # _logger.warning(f"TESTTEST {payslip.get_worked_day_lines(payslip.contract_id, cls.date_start, cls.date_stop)}")
        # payslip.onchange_employee()
        # payslip._compute_details_by_salary_rule_category()
        # # _logger.warning(f"checkpoint1 {payslip.worked_days_line_ids}")
        # payslip.get_worked_day_lines(payslip.contract_id, cls.date_start, cls.date_stop)
        # # payslip.get_payslip_vals(cls.date_start, cls.date_stop, cls.employee_asse.id, contract_id[0].id, cls.struct)
        # payslip.onchange_struct_id()
        # payslip.compute_sheet()


        # _logger.warning(f"{payslip.onchange_employee()=}")
        # _logger.warning(f"{payslip._compute_details_by_salary_rule_category()=}")
        # _logger.warning(f"{payslip.get_worked_day_lines(payslip.contract_id, cls.date_start, cls.date_stop)=}")
        # _logger.warning(f"{payslip.onchange_struct_id()=}")
        # _logger.warning(f"{payslip.compute_sheet()=}")

        # date_start_2 = fields.Date.from_string('2023-01-01')
        # date_stop_2 = fields.Date.from_string('2023-01-31')
        # day_from_2 = datetime.combine(date_start_2, time.min)
        # day_to_2 = datetime.combine(date_stop_2, time.max)
        # day_from = datetime.combine(cls.date_start, time.min)
        # day_to = datetime.combine(cls.date_stop, time.max)
        # contract_id = cls.env['hr.contract'].search([('name', '=', f"{' '.join(cls.employee_asse.name.split(' ')[:2])} Avtal")])
        # mitchell = cls.env['res.users'].browse(2)
   
        # _logger.warning(f"{employee_id.resource_calendar_id._leave_intervals_batch(day_from.replace(tzinfo=utc), day_to.replace(tzinfo=utc), resources=contract_id.resource_calendar_id)[0]._items=}")
        # _logger.warning(f"{mitchell.employee_id.resource_calendar_id._leave_intervals_batch(day_from_2.replace(tzinfo=utc), day_to_2.replace(tzinfo=utc))=}")
        

        # _logger.warning(f"{payslip._compute_leave_days(contract_id, day_from, day_to)=}")

        # for something in payslip.get_payslip_vals(cls.date_start, cls.date_stop, cls.employee_asse.id, contract_id[0].id, cls.struct)['value']['worked_days_line_ids']:
        #     _logger.warning(f"something: {something}")

        # _logger.warning(f"{employee_id.list_leaves(day_from, day_to, calendar=contract_id.resource_calendar_id)=}")

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

        # Asse Aronsson
        cls.employee_asse = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_asse_employee')
        cls.asse_1 = cls._create_leave(cls.employee_asse, "sjk_kar" ,"2022-01-07","2022-01-07",1)
        cls.asse_2 = cls._create_leave(cls.employee_asse, "sjk_kar" ,"2022-01-12","2022-01-12",1)
        cls.asse_3 = cls._create_leave(cls.employee_asse, "sjk_214" ,"2022-01-13","2022-01-13",1)
        cls.asse_4 = cls._create_leave(cls.employee_asse, "sjk_214" ,"2022-01-24","2022-01-24",1)
        cls.asse_5 = cls._create_leave(cls.employee_asse, "vab" ,"2022-01-25","2022-01-25",1)
        cls.asse_6 = cls._create_leave(cls.employee_asse, "vab", "2022-01-26", "2022-01-26",1)
        cls.asse_7 = cls._create_leave(cls.employee_asse, "Leave of Absence less than 5 days", "2022-01-03", "2022-01-03",1)
        cls.asse_8 = cls._create_leave(cls.employee_asse, "Leave of Absence less than 5 days", "2022-01-14", "2022-01-14",1)
        cls.asse_9 = cls._create_leave(cls.employee_asse, "Leave of Absence less than 5 days", "2022-01-17", "2022-01-17",1)
        cls.asse_10 = cls._create_leave(cls.employee_asse, "Leave of Absence less than 5 days", "2022-01-18", "2022-01-18",1)
        cls.asse_11 = cls._create_leave(cls.employee_asse, "Leave of Absence less than 5 days", "2022-01-19", "2022-01-19",1)
        cls.asse_12 = cls._create_leave(cls.employee_asse, "Leave of Absence more than 5 days", "2022-01-20", "2022-01-20",1)
            
        # Frans Filipsson
        cls.employee_frans = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_frans_employee')  # frans_employee
        cls.frans_1 = cls._create_leave(cls.employee_frans, "sjk_kar" ,"2022-01-07","2022-01-07",1)
        cls.frans_2 = cls._create_leave(cls.employee_frans, "sjk_kar" ,"2022-01-10","2022-01-10",1)
        cls.frans_3 = cls._create_leave(cls.employee_frans, "sjk_214" ,"2022-01-11","2022-01-12",2)
        cls.frans_4 = cls._create_leave(cls.employee_frans, "Leave of Absence less than 5 days" ,"2022-01-20","2022-01-21",2)
        cls.frans_5 = cls._create_leave(cls.employee_frans, "Leave of Absence less than 5 days" ,"2022-01-24","2022-01-26",3)
        cls.frans_6 = cls._create_leave(cls.employee_frans, "Leave of Absence more than 5 days" ,"2022-01-27","2022-01-27",1)

        # Doris Dahlin
        cls.employee_doris = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_doris_employee')  # doris_employee
        cls.doris_1 = cls._create_leave(cls.employee_doris, "sjk_kar" ,"2022-01-04","2022-01-04",1)
        cls.doris_2 = cls._create_leave(cls.employee_doris, "sjk_214" ,"2022-01-05","2022-01-05",1)
        cls.doris_3 = cls._create_leave(cls.employee_doris, "sjk_kar" ,"2022-01-10","2022-01-10",1)
        cls.doris_4 = cls._create_leave(cls.employee_doris, "sjk_214" ,"2022-01-11","2022-01-12",2)
        cls.doris_5 = cls._create_leave(cls.employee_doris, "Leave of Absence less than 5 days" ,"2022-01-13","2022-01-13",1)

        # Camilla Cobolt -- Låt stå! :-) Inte sjuk i januari
        cls.employee_camilla = self.env.ref('hr_camilla_employee')  # camilla_employee
        cls.camilla_1 = cls._create_leave(cls.employee_camilla, "vab" ,"2022-01-14","2022-01-14",1)
        cls.camilla_2 = cls._create_leave(cls.employee_camilla, "vab" ,"2022-01-17","2022-01-17",1)


        # # Gustav Groth
        # cls.employee_gustav = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_gustav_employee')  # gustav_employee
        # cls.gustav_kar = cls._create_leave(cls.employee_gustav.id, "sjk_kar" ,"2022-01-07","2022-01-07",1)
        # cls.gustav_kar = cls._create_leave(cls.employee_gustav.id, "sjk_214" ,"2022-01-10","2022-01-14",5)
        # cls.gustav_kar = cls._create_leave(cls.employee_gustav.id, "sjk_214" ,"2022-01-17","2022-01-21",5)
        # cls.gustav_kar = cls._create_leave(cls.employee_gustav.id, "sjk_214" ,"2022-01-24","2022-01-25",2)
        
        # # Helmer Henriksson
        # cls.employee_helmer = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_helmer_employee')  # helmer_employee
        # cls.helmer_kar = cls._create_leave(cls.employee_helmer.id, "sjk_kar" ,"2022-01-04","2022-01-04",1)
        # cls.helmer_kar = cls._create_leave(cls.employee_helmer.id, "sjk_214" ,"2022-01-05","2022-01-05",1)
        # cls.helmer_kar = cls._create_leave(cls.employee_helmer.id, "sjk_kar" ,"2022-01-12","2022-01-12",1)
        # cls.helmer_kar = cls._create_leave(cls.employee_helmer.id, "sjk_214" ,"2022-01-13","2022-01-14",2)

        # Karin Kullberg
        # Anställning per timme, påbörjad 2022-06-01

    def test_asse(self):   
        payslip_form = self._create_payslip(self.employee_asse, self.employee_asse.contract_id, [
                {'code': 'kvaltim','amount': 4.0},
            ])

        for worked_day in payslip_form.worked_days_line_ids:
            _logger.warning(f"{worked_day.name=} {worked_day.number_of_hours=}")

        for detail in payslip_form.dynamic_filtered_payslip_lines:
            _logger.warning(f"line id from input: {detail.name} {detail.total}")
            if detail.code == 'net':
                self.assertAlmostEqual(detail.total, 27734.0)

    def test_frans(self):
        payslip_form = self._create_payslip(self.employee_frans, self.employee_frans.contract_id, [
                {'code': 'kvaltim','amount': 3.0},
            ])

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
                self.assertAlmostEqual(detail.total, 23008.0)   

    def test_doris(self):
        payslip_form = self._create_payslip(self.employee_doris, self.employee_doris.contract_id, [
                {'code': 'kvaltim','amount': 2.0},
                {'code': 'mertidtim','amount': 8.0},
            ])

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
                self.assertAlmostEqual(detail.total, 19538.0)   


    def test_camilla(self):
        payslip_form = self._create_payslip(self.employee_doris, self.employee_doris.contract_id, [
                {'code': 'kvaltim','amount': 2.0},
                {'code': 'mertidtim','amount': 8.0},
            ])

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
                self.assertAlmostEqual(detail.total, 15524.0)   

