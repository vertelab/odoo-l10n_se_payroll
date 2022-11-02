# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2014- Vertel AB (<http://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
# ~ from odoo.modules.registry import RegistryManager
from dateutil.relativedelta import relativedelta
from odoo.modules.registry import Registry
from odoo.exceptions import except_orm, Warning, RedirectWarning
from odoo import models, fields, api, _
from odoo import http
from odoo.http import request
from odoo import tools

import random

import logging

_logger = logging.getLogger(__name__)

from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from datetime import timedelta, date, datetime

import odoo.addons.decimal_precision as dp


# ~ This adds a default credit/debit account field for the account journal, since the fields loss/profit_account_id
# seems to have specific purposes that i don't understand
class account_journal(models.Model):
    _inherit = 'account.journal'

    default_credit_account_id = fields.Many2one(comodel_name='account.account', check_company=True, copy=False,
                                                ondelete='restrict', string='Default Credit Account',
                                                domain=[('deprecated', '=', False)],
                                                help="It acts as a default account for credit amount, is used for the "
                                                     "general journal type, so that we can confirm a payslip since "
                                                     "its function wants a default_credit_account_id")

    default_debit_account_id = fields.Many2one(comodel_name='account.account', check_company=True, copy=False,
                                               ondelete='restrict', string='Default Debit Account',
                                               domain=[('deprecated', '=', False)],
                                               help="It acts as a default account for debit amount, is used for the "
                                                    "general journal type, so that we can confirm a payslip since its "
                                                    "function wants a default_debit_account_id")

    @api.onchange('default_debit_account_id')
    def onchange_debit_account_id(self):
        if not self.default_credit_account_id:
            self.default_credit_account_id = self.default_debit_account_id

    @api.onchange('default_credit_account_id')
    def onchange_credit_account_id(self):
        if not self.default_debit_account_id:
            self.default_debit_account_id = self.default_credit_account_id
