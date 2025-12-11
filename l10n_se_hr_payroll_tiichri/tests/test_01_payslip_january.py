# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

# DOCUMENTAION // RECOURCES
# https://docs.python.org/3/library/unittest.html
# https://www.odoo.com/forum/help-1/using-self-env-to-go-over-all-module-record-and-create-new-record-in-another-module-144407
# https://stackoverflow.com/questions/17534345/typeerror-missing-1-required-positional-argument-self
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
# $ odoo -c /etc/odoo/odoo.conf -d odoo-tiichri -i l10n_se_hr_payroll_tiichri --test-enable

@tagged('l10n_se_payroll_tiichri', 'january')
class TestPayslipJanuary(TransactionCase):


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

        _logger.info(f"TEST PAYSLIP: Employee: {employee_id.name} | Period: {cls.period.name} | Inputs: {input_recs}")
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
        payslip_form.period_id = cls.period
        payslip_form.contract_id = contract_id
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


        # ~ Leave of Absence less than 5 days = pem
        # ~ Leave of Absence more than 5 days = pem_5
        # Asse Aronsson
        
        cls.employee_asse = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_asse_employee')
        cls.asse_101 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_asse_101')  # leave_asse_101
        cls.asse_102 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_asse_102')  # leave_asse_102
        cls.asse_103 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_asse_103')  # leave_asse_103
        cls.asse_104 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_asse_104')  # leave_asse_104
        cls.asse_105 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_asse_105')  # leave_asse_105
        cls.asse_106 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_asse_106')  # leave_asse_106
        cls.asse_107 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_asse_107')  # leave_asse_107
        cls.asse_108 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_asse_108')  # leave_asse_108
        cls.asse_109 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_asse_109')  # leave_asse_109
        cls.asse_110 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_asse_110')  # leave_asse_110
        cls.asse_111 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_asse_111')  # leave_asse_111
        cls.asse_112 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_asse_112')  # leave_asse_112
            
        # # Frans Filipsson
        cls.employee_frans = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_frans_employee')  # frans_employee
        cls.frans_101 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_frans_101')  # leave_frans_101
        cls.frans_102 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_frans_102')  # leave_frans_102
        cls.frans_103 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_frans_103')  # leave_frans_103
        cls.frans_104 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_frans_104')  # leave_frans_104
        cls.frans_105 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_frans_105')  # leave_frans_105
        cls.frans_106 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_frans_106')  # leave_frans_106

        # # Doris Dahlin
        cls.employee_doris = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_doris_employee')  # doris_employee
        cls.doris_101 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_doris_101')  # leave_doris_101
        cls.doris_102 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_doris_102')  # leave_doris_102
        cls.doris_103 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_doris_103')  # leave_doris_103
        cls.doris_104 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_doris_104')  # leave_doris_104
        cls.doris_105 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_doris_105')  # leave_doris_105

        # # Camilla Cobolt -- Låt stå! :-) Inte sjuk i januari
        cls.employee_camilla = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_camilla_employee')  # camilla_employee
        cls.camilla_101 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_camilla_101')  # leave_camilla_101
        cls.camilla_102 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_camilla_102')  # leave_camilla_102

        # # # Gustav Groth
        cls.employee_gustav = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_gustav_employee')  # gustav_employee
        cls.gustav_101 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_gustav_101')  # leave_gustav_101
        cls.gustav_102 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_gustav_102')  # leave_gustav_102
        cls.gustav_103 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_gustav_103')  # leave_gustav_103
        cls.gustav_104 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_gustav_104')  # leave_gustav_104
        
        # # # Helmer Henriksson
        cls.employee_helmer = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_helmer_employee')  # helmer_employee
        cls.helmer_101 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_helmer_101')  # leave_helmer_101
        cls.helmer_102 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_helmer_102')  # leave_helmer_102
        cls.helmer_103 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_helmer_103')  # leave_helmer_103
        cls.helmer_104 = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_leave_helmer_104')  # leave_helmer_104

        # Karin Kullberg
        # Anställning per timme, påbörjad 2022-06-01

    ## Test 1
    def test_asse(self):   
        payslip_form = self._create_payslip(self.employee_asse, self.employee_asse.contract_id, [
                {'code': 'kvaltim','amount': 4.0},
            ])

        found_net = False
        for detail in payslip_form.dynamic_filtered_payslip_lines:
            if detail.code == 'net':
                # FACIT: Ska vara 27734.0
                self.assertAlmostEqual(detail.total, 27734.0, msg=f"Wrong net pay for Asse! Got: {detail.total}, expected: 27734.0.")
                _logger.info(f"SUCCESS: Asse net pay correct: {detail.total}")
                found_net = True

        self.assertTrue(found_net, "Could not find field 'net' for Asse.")

              
    ## Test 4
    def test_frans(self):
        payslip_form = self._create_payslip(self.employee_frans, self.employee_frans.contract_id, [
                {'code': 'kvaltim','amount': 3.0},
                {'code': 'mertidtim','amount': 2.0},
            ])

        found_net = False
        for detail in payslip_form.dynamic_filtered_payslip_lines:
            if detail.code == 'net':
                # FACIT: Ska vara 23008.0
                self.assertAlmostEqual(detail.total, 23008.0, msg=f"Wrong net pay for Frans! Got: {detail.total}, expected: 23008.0.")
                _logger.info(f"SUCCESS: Frans net pay correct: {detail.total}")
                found_net = True

        self.assertTrue(found_net, "Could not find field 'net' for Frans.")


    ## Test 3
    def test_doris(self):
        payslip_form = self._create_payslip(self.employee_doris, self.employee_doris.contract_id, [
                {'code': 'kvaltim','amount': 2.0},
                {'code': 'mertidtim','amount': 8.0},
            ])

        found_net = False
        for detail in payslip_form.dynamic_filtered_payslip_lines:
            if detail.code == 'net':
                # FACIT: Ska vara 19538.0
                self.assertAlmostEqual(detail.total, 19538.0, msg=f"Wrong net pay for Doris! Got: {detail.total}, expected: 19538.0.")
                _logger.info(f"SUCCESS: Doris net pay correct: {detail.total}")
                found_net = True

        self.assertTrue(found_net, "Could not find field 'net' for Doris.")


    ## Test 2
    def test_camilla(self):
        payslip_form = self._create_payslip(self.employee_camilla, self.employee_camilla.contract_id, [
                {'code': 'kvaltim','amount': 2.0},
                {'code': 'mertidtim','amount': 8.0},
            ])

        found_net = False
        for detail in payslip_form.dynamic_filtered_payslip_lines:
            if detail.code == 'net':
                # FACIT: Ska vara 15524.0
                self.assertAlmostEqual(detail.total, 15524.0, msg=f"Wrong net pay for Camilla! Got: {detail.total}, expected: 15524.0.")
                _logger.info(f"SUCCESS: Camilla net pay correct: {detail.total}")
                found_net = True

        self.assertTrue(found_net, "Could not find field 'net' for Camilla.")


    ## Test 5
    def test_gustav(self):
        payslip_form = self._create_payslip(self.employee_gustav, self.employee_gustav.contract_id, [
                {'code': 'kvaltim','amount': 4.0},
            ])

        found_net = False
        for detail in payslip_form.dynamic_filtered_payslip_lines:
            if detail.code == 'net':
                # FACIT: Ska vara 20540.0
                self.assertAlmostEqual(detail.total, 20540.0, msg=f"Wrong net pay for Gustav! Got: {detail.total}, expected: 20540.0.")
                _logger.info(f"SUCCESS: Gustav net pay correct: {detail.total}")
                found_net = True

        self.assertTrue(found_net, "Could not find field 'net' for Gustav.")


    ## Test 6
    def test_helmer(self):
        payslip_form = self._create_payslip(self.employee_helmer, self.employee_helmer.contract_id, [
                {'code': 'kvaltim','amount': 4.0},
            ])

        found_net = False
        for detail in payslip_form.dynamic_filtered_payslip_lines:
            if detail.code == 'net':
                # FACIT: Ska vara 20104.0
                self.assertAlmostEqual(detail.total, 20104.0, msg=f"Wrong net pay for Helmer! Got: {detail.total}, expected: 20104.0.")
                _logger.info(f"SUCCESS: Helmer net pay correct: {detail.total}")
                found_net = True

        self.assertTrue(found_net, "Could not find field 'net' for Helmer.")






