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

class TestPayslipMars(common.SavepointCase):


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
                        })
        _logger.warning('test ***  %s ' % leave.state)
        return leave
        
    def _create_leave(self, employee_id,code,date_from,date_to,number_of_days): 
        leave = cls.env["hr.leave"].create({    
                            "holiday_status_id": code,
                            "request_date_from": date_from,
                            "request_date_to": date_to,
                            "number_of_days": number_of_days,
                            'holiday_type': 'employee',
                            'employee_id': employee_id,
                        })
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
        # Asse Aronsson
        cls.employee_asse = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_asse_employee')  # asse_employee
        cls.asse_kar = cls._create_leave(cls.employee_asse.id, "sjk_kar" ,"2022-03-01","2022-03-01",1)
        cls.asse_kar = cls._create_leave(cls.employee_asse.id, "sjk_214" ,"2022-03-02","2022-03-04",3)
        cls.asse_kar = cls._create_leave(cls.employee_asse.id, "sjk_214" ,"2022-03-07","2022-03-09",3)

        # Frans Filipsson
        cls.employee_frans = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_frans_employee')  # frans_employee
        cls.frans_kar = cls._create_leave(cls.employee_frans.id, "sjk_kar" ,"2022-03-04","2022-03-04",1)
        cls.frans_kar = cls._create_leave(cls.employee_frans.id, "sjk_214" ,"2022-03-07","2022-03-11",5)
        cls.frans_kar = cls._create_leave(cls.employee_frans.id, "sjk_214" ,"2022-03-14","2022-03-16",3)

        # Doris Dahlin -- Låt stå! :-) Inte sjuk i mars

        # Camilla Cobolt -- Låt stå! :-) Inte sjuk i mars

        # Gustav Groth
        cls.employee_gustav = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_gustav_employee')  # gustav_employee
        cls.gustav_kar = cls._create_leave(cls.employee_gustav.id, "sjk_kar" ,"2022-03-02","2022-03-02",1)
        cls.gustav_kar = cls._create_leave(cls.employee_gustav.id, "sjk_214" ,"2022-03-03","2022-03-03",1)
        
        # Helmer Henriksson
        cls.employee_helmer = cls.env.ref('l10n_se_hr_payroll_tiichri.hr_helmer_employee')  # helmer_employee
        cls.helmer_kar = cls._create_leave(cls.employee_helmer.id, "sjk_kar" ,"2022-03-03","2022-03-03",1)
        cls.helmer_kar = cls._create_leave(cls.employee_helmer.id, "sjk_214" ,"2022-03-04","2022-03-04",1)
        cls.helmer_kar = cls._create_leave(cls.employee_helmer.id, "sjk_kar" ,"2022-03-16","2022-03-16",1)

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
