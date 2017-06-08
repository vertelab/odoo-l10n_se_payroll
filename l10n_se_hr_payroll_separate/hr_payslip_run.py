# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2004-2016 Vertel AB (<http://vertel.se>).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import openerp.exceptions
from openerp import models, fields, api, _
import datetime
from datetime import timedelta
import csv
import os
import tempfile
import base64
from openerp.tools.safe_eval import safe_eval as eval

try:
    import odoorpc
except:
    pass

import logging
_logger = logging.getLogger(__name__)



class hr_attendance(models.Model):
    _inherit = 'hr.attendance'
    
    @api.multi
    def _validate_fields(self, field_names):
        return True
        

class HrHolidays(models.Model):
    _inherit = 'hr.holidays'
    
    @api.multi
    def _validate_fields(self, field_names):
        return True

class base_synchro(models.TransientModel):
    _inherit = 'base.synchro'
    
    base_sync_object_ids = fields.Many2many(comodel_name='base.synchro.obj', string='Create sync lines for')
    
    @api.one
    def create_base_sync_lines(self):
        server = odoorpc.ODOO(self.server_url.server_url, port=self.server_url.server_port)
        server.login(self.server_url.server_db, self.server_url.login, self.server_url.password)
        remote_model_data = server.env['ir.model.data']
        for sync_obj in self.base_sync_object_ids:
            _logger.warn(sync_obj)
            domain = eval(sync_obj.domain)
            _logger.warn(domain)
            ids = self.pool.get(sync_obj.model_id.model).search(self._cr, self.env.user.id, domain, context=self.env.context)
            _logger.warn(ids)
            for external_id in self.env['ir.model.data'].search([('model', '=', sync_obj.model_id.model), ('res_id', 'in', ids)]):
                id = remote_model_data.search([('model', '=', sync_obj.model_id.model), ('name', '=', external_id.name), ('module', '=', external_id.module)])
                _logger.warn(id)
                if id:
                    remote_id = remote_model_data.browse(id).res_id
                    _logger.warn(remote_id)
                    if not self.env['base.synchro.obj.line'].search([('remote_id', '=', remote_id), ('local_id', '=', external_id.res_id), ('obj_id', '=', sync_obj.id)]):
                        self.env['base.synchro.obj.line'].create({
                            'remote_id': remote_id,
                            'local_id': external_id.res_id,
                            'obj_id': sync_obj.id,
                            'name': '1900-01-01 00:00:00',
                        })

    @api.model
    def _init_l10n_se_hr_payroll_separate(self):
        """Disable workflow init on hr.holidays. Otherwise the workflow will corrupt synced data (the state field, and maybe more)."""
        self.env.ref('hr_holidays.wkf_holidays').on_create = False


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
