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
# $ odoo --test-tags /l10n_se_payroll_twenty_six -c /etc/odoo/odoo.conf
# $ odoo -c /etc/odoo/odoo.conf -d DATABASNAMN -i l10n_se_hr_payroll_twenty_six --test-enable
# $ odoo -c /etc/odoo/odoo.conf -d odoo-twenty_six -i l10n_se_hr_payroll_twenty_six --test-enable
#

@tagged('at_install', 'l10n_se_payroll_twenty_six', 'may')
class TestPayslipMay(TransactionCase):
    ## Test 1
    def test_asse_net(self):   

        payslip = self.env.ref('l10n_se_hr_payroll_twenty_six.hr_payslip_asse_05')

        net_line = payslip.line_ids.filtered(lambda l: l.code == 'nl')

        self.assertTrue(net_line, "Kunde inte hitta fältet 'nl' (Nettolön) för Asse.")
        self.assertAlmostEqual(net_line.total, 33247.0, msg=f"Fel nettolön för Asse! Fick: {net_line.total}, förväntat: 33247.0.")
        _logger.info(f"SUCCESS: Asse net pay correct: {net_line.total}")


              
    ## Test 4
    def test_frans_net(self):

        payslip = self.env.ref('l10n_se_hr_payroll_twenty_six.hr_payslip_frans_05')

        net_line = payslip.line_ids.filtered(lambda l: l.code == 'nl')

        self.assertTrue(net_line, "Kunde inte hitta fältet 'nl' (Nettolön) för Frans.")
        self.assertAlmostEqual(net_line.total, 28440.0, msg=f"Fel nettolön för Frans! Fick: {net_line.total}, förväntat: 28440.0.")
        _logger.info(f"SUCCESS: Frans net pay correct: {net_line.total}")


    ## Test 3
    def test_doris_net(self):

        payslip = self.env.ref('l10n_se_hr_payroll_twenty_six.hr_payslip_doris_05')

        net_line = payslip.line_ids.filtered(lambda l: l.code == 'nl')

        self.assertTrue(net_line, "Kunde inte hitta fältet 'nl' (Nettolön) för Doris.")
        self.assertAlmostEqual(net_line.total, 16734.0, msg=f"Fel nettolön för Doris! Fick: {net_line.total}, förväntat: 16734.0.")
        _logger.info(f"SUCCESS: Doris net pay correct: {net_line.total}")


    ## Test 2
    def test_camilla_net(self):

        payslip = self.env.ref('l10n_se_hr_payroll_twenty_six.hr_payslip_camilla_05')

        net_line = payslip.line_ids.filtered(lambda l: l.code == 'nl')

        self.assertTrue(net_line, "Kunde inte hitta fältet 'nl' (Nettolön) för Camilla.")
        self.assertAlmostEqual(net_line.total, 17750.0, msg=f"Fel nettolön för Camilla! Fick: {net_line.total}, förväntat: 17750.0.")
        _logger.info(f"SUCCESS: Camilla net pay correct: {net_line.total}")



    ## Test 5
    def test_gustav_net(self):

        payslip = self.env.ref('l10n_se_hr_payroll_twenty_six.hr_payslip_gustav_05')

        net_line = payslip.line_ids.filtered(lambda l: l.code == 'nl')

        self.assertTrue(net_line, "Kunde inte hitta fältet 'nl' (Nettolön) för Gustav.")
        self.assertAlmostEqual(net_line.total, 19537.0, msg=f"Fel nettolön för Gustav! Fick: {net_line.total}, förväntat: 19537.0.")
        _logger.info(f"SUCCESS: Gustav net pay correct: {net_line.total}")


    ## Test 6
    def test_helmer_net(self):

        payslip = self.env.ref('l10n_se_hr_payroll_twenty_six.hr_payslip_helmer_05')

        net_line = payslip.line_ids.filtered(lambda l: l.code == 'nl')

        self.assertTrue(net_line, "Kunde inte hitta fältet 'nl' (Nettolön) för Helmer.")
        self.assertAlmostEqual(net_line.total, 18118.0, msg=f"Fel nettolön för Helmer! Fick: {net_line.total}, förväntat: 18118.0.")
        _logger.info(f"SUCCESS: Helmer net pay correct: {net_line.total}")
