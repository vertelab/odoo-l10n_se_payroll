import openerp.exceptions
from openerp import models, fields, api, _
import datetime
from datetime import timedelta, date

import logging
_logger = logging.getLogger(__name__)


class HrPayslip(models.Model):
    _inherit = "hr.payslip"
    
    
    
    
