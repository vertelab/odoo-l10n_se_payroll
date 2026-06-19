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

@tagged('at_install', 'l10n_se_payroll_twenty_six', 'july')
class TestPayslipJuly(TransactionCase):
    ## Test 1
    def test_asse_net(self):   

        payslip = self.env.ref('l10n_se_hr_payroll_twenty_six.hr_payslip_asse_07')

        net_line = payslip.line_ids.filtered(lambda l: l.code == 'nl')

        self.assertTrue(net_line, "Kunde inte hitta fältet 'nl' (Nettolön) för Asse.")
        self.assertAlmostEqual(net_line.total, 31056.0, msg=f"Fel nettolön för Asse! Fick: {net_line.total}, förväntat: 31056.0.")
        _logger.info(f"SUCCESS: Asse net pay correct: {net_line.total}")


              
    ## Test 4
    def test_frans_net(self):

        payslip = self.env.ref('l10n_se_hr_payroll_twenty_six.hr_payslip_frans_07')

        net_line = payslip.line_ids.filtered(lambda l: l.code == 'nl')

        self.assertTrue(net_line, "Kunde inte hitta fältet 'nl' (Nettolön) för Frans.")
        self.assertAlmostEqual(net_line.total, 26409.0, msg=f"Fel nettolön för Frans! Fick: {net_line.total}, förväntat: 26409.0.")
        _logger.info(f"SUCCESS: Frans net pay correct: {net_line.total}")


    ## Test 3
    def test_doris_net(self):

        payslip = self.env.ref('l10n_se_hr_payroll_twenty_six.hr_payslip_doris_07')

        net_line = payslip.line_ids.filtered(lambda l: l.code == 'nl')

        self.assertTrue(net_line, "Kunde inte hitta fältet 'nl' (Nettolön) för Doris.")
        self.assertAlmostEqual(net_line.total, 13317.0, msg=f"Fel nettolön för Doris! Fick: {net_line.total}, förväntat: 13317.0.")
        _logger.info(f"SUCCESS: Doris net pay correct: {net_line.total}")


    ## Test 2
    def test_camilla_net(self):

        payslip = self.env.ref('l10n_se_hr_payroll_twenty_six.hr_payslip_camilla_07')

        net_line = payslip.line_ids.filtered(lambda l: l.code == 'nl')

        self.assertTrue(net_line, "Kunde inte hitta fältet 'nl' (Nettolön) för Camilla.")
        self.assertAlmostEqual(net_line.total, 23915.0, msg=f"Fel nettolön för Camilla! Fick: {net_line.total}, förväntat: 23915.0.")
        _logger.info(f"SUCCESS: Camilla net pay correct: {net_line.total}")



    ## Test 5
    def test_gustav_net(self):

        payslip = self.env.ref('l10n_se_hr_payroll_twenty_six.hr_payslip_gustav_07')

        net_line = payslip.line_ids.filtered(lambda l: l.code == 'nl')

        self.assertTrue(net_line, "Kunde inte hitta fältet 'nl' (Nettolön) för Gustav.")
        self.assertAlmostEqual(net_line.total, 17981.0, msg=f"Fel nettolön för Gustav! Fick: {net_line.total}, förväntat: 17981.0.")
        _logger.info(f"SUCCESS: Gustav net pay correct: {net_line.total}")


    ## Test 6
    def test_helmer_net(self):

        payslip = self.env.ref('l10n_se_hr_payroll_twenty_six.hr_payslip_helmer_07')

        net_line = payslip.line_ids.filtered(lambda l: l.code == 'nl')

        self.assertTrue(net_line, "Kunde inte hitta fältet 'nl' (Nettolön) för Helmer.")
        self.assertAlmostEqual(net_line.total, 23326.0, msg=f"Fel nettolön för Helmer! Fick: {net_line.total}, förväntat: 23326.0.")
        _logger.info(f"SUCCESS: Helmer net pay correct: {net_line.total}")


    ## Test 7
    def test_karin_net(self):

        payslip = self.env.ref('l10n_se_hr_payroll_twenty_six.hr_payslip_karin_07')

        net_line = payslip.line_ids.filtered(lambda l: l.code == 'nl')

        self.assertTrue(net_line, "Kunde inte hitta fältet 'nl' (Nettolön) för Karin.")
        self.assertAlmostEqual(net_line.total, 12776.0, msg=f"Fel nettolön för Karin! Fick: {net_line.total}, förväntat: 12776.0.")
        _logger.info(f"SUCCESS: Karin net pay correct: {net_line.total}")
