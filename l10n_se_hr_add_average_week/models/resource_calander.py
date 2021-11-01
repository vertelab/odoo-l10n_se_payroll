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

class ResourceCalendar(models.Model):
   _inherit = "resource.calendar"
   
   hours_per_week = fields.Float("Hours per week", compute = "_compute_hours_per_week")
   
   @api.onchange('attendance_ids')
   def _compute_hours_per_week(self):
       for rec in self:
          rec.hours_per_week = 0
          for attendance in self.attendance_ids:
            rec.hours_per_week += attendance.hour_to - attendance.hour_from
   

    
