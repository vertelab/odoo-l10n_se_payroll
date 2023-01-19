# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

# DOCUMENTAION // RECOURCES
# https://docs.python.org/3/library/unittest.html
# https://www.odoo.com/forum/help-1/using-self-env-to-go-over-all-module-record-and-create-new-record-in-another-module-144407
# https://stackoverflow.com/questions/17534345/typeerror-missing-1-required-positional-argument-self


from odoo import fields
from odoo.tests import common
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
        leave = cls.env["hr.leave"].create({    
                            "holiday_status_id": cls.env["hr.leave.type"].search([('code','=', code )]).mapped('id')[0],
                            "request_date_from": date_from,
                            "request_date_to": date_to,
                            "number_of_days": number_of_days,
                            'holiday_type': 'employee',
                            'employee_id': employee_id,
                            # ~ 'state': 'confirm',
                        })
        # ~ leave.state = 'draft'
        # ~ leave.state = 'confirm'
        _logger.warning('jakob ***  %s ' % leave.state)
        # ~ leave.action_confirm()
        # ~ leave.action_approve()
        return leave
    
    @classmethod
    def _create_payslip(cls, employee_id,date,input_recs): 
        payslip = cls.env["hr.payslip"].create({
                            'employee_id': employee_id,
                            'date':  fields.Date.from_string(date),
            })
        for input_rec in input_recs:
            line = cls.env["hr.payslip.input"].search([('code','=',input_rec['code']),('slip_id','=',payslip.id)])[0]
            line.amount = input_rec['amount']
            line.amount_qty = input_rec['amount_qty']            
        return payslip
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Asse Aronsson = id 15
        cls.employee_asse = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_asse_employee')  # asse_employee
        cls.asse_kar = cls._create_leave(cls.employee_asse.id, "sjk_kar" ,"2022-01-07","2022-01-07",1)
        cls.asse_kar = cls._create_leave(cls.employee_asse.id, "sjk_kar" ,"2022-01-12","2022-01-12",1)
        cls.asse_kar = cls._create_leave(cls.employee_asse.id, "sjk_214" ,"2022-01-13","2022-01-13",1)
        cls.asse_kar = cls._create_leave(cls.employee_asse.id, "sjk_kar" ,"2022-01-24","2022-01-24",1)
            
        # Frans Filipsson
        cls.employee_frans = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_frans_employee')  # frans_employee
        cls.frans_kar = cls._create_leave(cls.employee_frans.id, "sjk_kar" ,"2022-01-07","2022-01-07",1)
        cls.frans_kar = cls._create_leave(cls.employee_frans.id, "sjk_kar" ,"2022-01-10","2022-01-10",1)
        cls.frans_kar = cls._create_leave(cls.employee_frans.id, "sjk_214" ,"2022-01-11","2022-01-12",2)

        # Doris Dahlin
        cls.employee_doris = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_doris_employee')  # doris_employee
        cls.doris_kar = cls._create_leave(cls.employee_doris.id, "sjk_kar" ,"2022-01-04","2022-01-04",1)
        cls.doris_kar = cls._create_leave(cls.employee_doris.id, "sjk_214" ,"2022-01-05","2022-01-05",1)
        cls.doris_kar = cls._create_leave(cls.employee_doris.id, "sjk_kar" ,"2022-01-10","2022-01-10",1)
        cls.doris_kar = cls._create_leave(cls.employee_doris.id, "sjk_214" ,"2022-01-11","2022-01-12",2)

        # Camilla Cobolt -- Låt stå! :-) Inte sjuk i januari
        # ~ cls.employee_camilla = self.env.ref('hr_camilla_employee')  # camilla_employee
        # ~ cls.camilla_kar = self.create_leave(cls.employee_camilla,'sjk_kar',"2022-01-07","2022-01-07",1.0)
        # ~ cls.camilla_kar.action_approve()
        # ~ cls.camilla_kar = self.create_leave(cls.employee_camilla,'sjk_kar',"2022-01-10","2022-01-12",3.0)
        # ~ cls.camilla_kar.action_approve()

        # Gustav Groth
        cls.employee_gustav = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_gustav_employee')  # gustav_employee
        cls.gustav_kar = cls._create_leave(cls.employee_gustav.id, "sjk_kar" ,"2022-01-07","2022-01-07",1)
        cls.gustav_kar = cls._create_leave(cls.employee_gustav.id, "sjk_214" ,"2022-01-10","2022-01-14",5)
        cls.gustav_kar = cls._create_leave(cls.employee_gustav.id, "sjk_214" ,"2022-01-17","2022-01-21",5)
        cls.gustav_kar = cls._create_leave(cls.employee_gustav.id, "sjk_214" ,"2022-01-24","2022-01-25",2)
        
        # Helmer Henriksson
        cls.employee_helmer = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_helmer_employee')  # helmer_employee
        cls.helmer_kar = cls._create_leave(cls.employee_helmer.id, "sjk_kar" ,"2022-01-04","2022-01-04",1)
        cls.helmer_kar = cls._create_leave(cls.employee_helmer.id, "sjk_214" ,"2022-01-05","2022-01-05",1)
        cls.helmer_kar = cls._create_leave(cls.employee_helmer.id, "sjk_kar" ,"2022-01-12","2022-01-12",1)
        cls.helmer_kar = cls._create_leave(cls.employee_helmer.id, "sjk_214" ,"2022-01-13","2022-01-14",2)

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
