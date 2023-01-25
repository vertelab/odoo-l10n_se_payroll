# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2018 Vertel AB (<http://vertel.se>).
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

from odoo import models, fields, api, _, tools

import logging
_logger = logging.getLogger(__name__)

class ContractType(models.Model):
    _inherit = "hr.contract.type"
    _description = "Contract Type"
    
    work_time = fields.Selection([('none', 'None'),('schema_hour', 'Schema Hour')], string='Work Time', default='none', help="Type of work time")
    #type_id

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

