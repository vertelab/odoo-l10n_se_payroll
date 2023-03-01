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
    
    work_time = fields.Selection([('none', 'None'),('schema_hour', 'Schema Hour')], string='Work Type', default='none', help="Type of work time")


class hr_contract(models.Model):
    _inherit = 'hr.contract'

    type_id = fields.Many2one('hr.contract.type', string="Employee Category",
                              required=False, help="Employee category",
                              default=lambda self: self.env['hr.contract.type'].search([], limit=1))
    
    work_time = fields.Selection(related='type_id.work_time', readonly=False, default='none')


class ContractType(models.Model):
    _inherit = "hr.contract.type"
    _description = "Contract Type"
    
    work_time = fields.Selection([('none', 'None'),('schema_hour', 'Schema Hour')], string='Work Type', default='none', help="Type of work time")
    name = fields.Char(required=False)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

