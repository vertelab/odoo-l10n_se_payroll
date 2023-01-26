# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.tests import common
import logging
_logger = logging.getLogger(__name__)

# Test with somthing like this
# $ sudo service odoo stop
# $ sudo su odoo
# $ odoo --test-tags /l10n_se_payroll_tiichri -c /etc/odoo/odoo.conf
#

class TestPayslipAugust(common.SavepointCase):


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
    def _create_leave(cls, employee_id, code, date_from, date_to, number_of_days,from_hours=False,to_hours=False): 
        if from_hours and to_hour:
            leave = cls.env["hr.leave"].create({    
                                "holiday_status_id": cls.env["hr.leave.type"].search([('code','=', code )]).mapped('id')[0],
                                "request_date_from": date_from,
                                "request_date_to": date_to,
                                "number_of_days": number_of_days,
                                'holiday_type': 'employee',
                                'employee_id': employee_id,
                                'request_hour_from':from_hours,
                                'request_hour_to':to_hours,
                            })
        else:
            leave = cls.env["hr.leave"].create({    
                                "holiday_status_id": cls.env["hr.leave.type"].search([('code','=', code )]).mapped('id')[0],
                                "request_date_from": date_from,
                                "request_date_to": date_to,
                                "number_of_days": number_of_days,
                                'holiday_type': 'employee',
                                'employee_id': employee_id,
                                })
            
        _logger.warning('test ***  %s ' % leave.state)
        return leave

        
    def _create_payslip(self, employee_id,date,input_recs): 
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
        # Asse Aronsson -- Låt stå! :-) Inte sjuk i juli
        cls.employee_asse = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_asse_employee')  # asse_employee
        cls.asse_kar = cls._create_leave(cls.employee_asse.id, "sjk_kar" ,"2022-08-12","2022-08-12",1)
        cls.asse_kar = cls._create_leave(cls.employee_asse.id, "sjk_214" ,"2022-08-15","2022-08-19",5)
        cls.asse_kar = cls._create_leave(cls.employee_asse.id, "sjk_214" ,"2022-08-22","2022-08-26",5)
        cls.asse_kar = cls._create_leave(cls.employee_asse.id, "sjk_214" ,"2022-08-29","2022-08-31",3)
            
        # Frans Filipsson
        cls.employee_frans = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_frans_employee')  # frans_employee
        cls.frans_kar = cls._create_leave(cls.employee_frans.id, "sjk_kar" ,"2022-07-01","2022-07-01",1)
        cls.frans_kar = cls._create_leave(cls.employee_frans.id, "sjk_214" ,"2022-07-04","2022-07-08",5)
        cls.frans_kar = cls._create_leave(cls.employee_frans.id, "sjk_214" ,"2022-07-11","2022-07-12",2)

        # Doris Dahlin
        cls.employee_doris = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_doris_employee')  # doris_employee
        cls.doris_kar = cls._create_leave(cls.employee_doris.id, "sjk_kar" ,"2022-07-04","2022-07-04",1)
        cls.doris_kar = cls._create_leave(cls.employee_doris.id, "sjk_214" ,"2022-07-05","2022-07-07",3)
        cls.doris_kar = cls._create_leave(cls.employee_doris.id, "sjk_214" ,"2022-07-11","2022-07-14",4)

        # Camilla Cobolt
        cls.employee_camilla = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_camilla_employee')  # camilla_employee
        cls.camilla_kar = cls._create_leave(cls.employee_camilla.id, "sjk_kar" ,"2022-07-11","2022-07-11",1)
        cls.camilla_kar = cls._create_leave(cls.employee_camilla.id, "sjk_kar" ,"2022-07-18","2022-07-18",1)
        cls.camilla_kar = cls._create_leave(cls.employee_camilla.id, "sjk_214" ,"2022-07-19","2022-07-19",1)

        # Gustav Groth
        cls.employee_gustav = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_gustav_employee')  # gustav_employee
        cls.gustav_kar = cls._create_leave(cls.employee_gustav.id, "sjk_214" ,"2022-07-01","2022-07-01",1)
        cls.gustav_kar = cls._create_leave(cls.employee_gustav.id, "sjk_214" ,"2022-07-05","2022-07-08",4)
       
        # Helmer Henriksson
        cls.employee_helmer = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_helmer_employee')  # helmer_employee
        cls.helmer_kar = cls._create_leave(cls.employee_helmer.id, "sjk_kar" ,"2022-07-07","2022-07-07",1)
        cls.helmer_kar = cls._create_leave(cls.employee_helmer.id, "sjk_214" ,"2022-07-08","2022-07-08",1)
        cls.helmer_kar = cls._create_leave(cls.employee_helmer.id, "sjk_214" ,"2022-07-11","2022-07-11",1)

        # Karin Kullberg
        cls.employee_karin = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_karin_employee')  # karin_employee
        cls.karin_kar = cls._create_leave(cls.employee_karin.id, "sjk_kar" ,"2022-07-11","2022-07-11",1)
        cls.karin_kar = cls._create_leave(cls.employee_karin.id, "sjk_214" ,"2022-07-12","2022-07-14",3)
        
       

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
