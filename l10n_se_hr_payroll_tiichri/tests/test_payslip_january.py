# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.tests import common

# Test with somthing like this
# $ sudo su odoo
# $ odoo --test-tags /l10n_se_payroll_tiichri -c /etc/odoo/odoo.conf
#

class TestPayslipJanuary(common.SavepointCase):


    def _create_leave(self, employee_id,code,date_from,date_to,number_of_days): 
        leave = cls.env["hr.leave"].create({    
                            "holiday_status_id": cls.env["hr.leave.type"].search([('code','=','sjk_kar')]).mapped('id')[0],
                            "request_date_from": fields.Date.from_string("2020-01-07"),
                            "request_date_to": fields.Date.from_string("2020-01-07"),
                            "number_of_days": 1.0,
                            'holiday_type': 'employee',
                            'employee_id': cls.employee_asse,
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
        # Asse Asse Aronsson
        cls.employee_asse = self.env.ref('hr_person1_employee')  # asse_employee
        cls.asse_kar = self.create_leave(cls.employee_asse,'sjk_kar',"2020-01-07","2020-01-07",1.0)
        cls.asse_kar.action_approve()
            
        # Camilla Cobolt
        # Doris Dahlin
        # Frans Filipsson
        # Gustav Groth
        # Helmer Henriksson
        # Karin Kullberg
        
       

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
