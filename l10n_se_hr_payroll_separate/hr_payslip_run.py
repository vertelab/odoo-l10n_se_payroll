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

    def _altern_si_so(self, cr, uid, ids, context=None):
        """ Alternance sign_in/sign_out check.
            Previous (if exists) must be of opposite action.
            Next (if exists) must be of opposite action.
        """
        return False
        for att in self.browse(cr, uid, ids, context=context):
            # search and browse for first previous and first next records
            prev_att_ids = self.search(cr, uid, [('employee_id', '=', att.employee_id.id), ('name', '<', att.name), ('action', 'in', ('sign_in', 'sign_out'))], limit=1, order='name DESC')
            next_add_ids = self.search(cr, uid, [('employee_id', '=', att.employee_id.id), ('name', '>', att.name), ('action', 'in', ('sign_in', 'sign_out'))], limit=1, order='name ASC')
            prev_atts = self.browse(cr, uid, prev_att_ids, context=context)
            next_atts = self.browse(cr, uid, next_add_ids, context=context)
            # check for alternance, return False if at least one condition is not satisfied
            if prev_atts and prev_atts[0].action == att.action: # previous exists and is same action
                return False
            if next_atts and next_atts[0].action == att.action: # next exists and is same action
                return False
            if (not prev_atts) and (not next_atts) and att.action != 'sign_in': # first attendance must be sign_in
                return False
        return True
        
    
    _constraints = [(_altern_si_so, 'Error ! Sign in (resp. Sign out) must follow Sign out (resp. Sign in)', ['action'])]
    #~ _constraints = [(lambda f: True, 'Error ! Sign in (resp. Sign out) must follow Sign out (resp. Sign in)', ['action'])]
    #~ _constraints = []
    def _auto_init(self, cr, context=None):
        self._constraints = [(lambda f: True, 'Error ! Sign in (resp. Sign out) must follow Sign out (resp. Sign in)', ['action'])]
        #raise Warning(self._constraints)
        super(hr_attendance, self)._auto_init(cr, context)
        
        
    @api.multi
    def _validate_fields(self, field_names):
        return True
        field_names = set(field_names)

        # old-style constraint methods
        trans = self.env['ir.translation']
        cr, uid, context = self.env.args
        ids = self.ids
        errors = []
        raise Warning(self._constraints)
        for fun, msg, names in self._constraints:
            try:
                # validation must be context-independent; call ``fun`` without context
                valid = names and not (set(names) & field_names)
                valid = valid or fun(self._model, cr, uid, ids)
                extra_error = None
            except Exception, e:
                _logger.debug('Exception while validating constraint', exc_info=True)
                valid = False
                extra_error = tools.ustr(e)
            if not valid:
                if callable(msg):
                    res_msg = msg(self._model, cr, uid, ids, context=context)
                    if isinstance(res_msg, tuple):
                        template, params = res_msg
                        res_msg = template % params
                else:
                    res_msg = trans._get_source(self._name, 'constraint', self.env.lang, msg)
                if extra_error:
                    res_msg += "\n\n%s\n%s" % (_('Error details:'), extra_error)
                errors.append(
                    _("Field(s) `%s` failed against a constraint: %s") %
                        (', '.join(names), res_msg)
                )
        if errors:
            raise ValidationError('\n'.join(errors))

        # new-style constraint methods
        for check in self._constraint_methods:
            if set(check._constrains) & field_names:
                try:
                    check(self)
                except ValidationError, e:
                    raise
                except Exception, e:
                    raise ValidationError("Error while validating constraint\n\n%s" % tools.ustr(e))


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




# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
