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

<<<<<<< HEAD

class hr_attendance(models.Model):
    _inherit = 'hr.attendance'

    def _altern_si_so(self, cr, uid, ids, context=None):
        """ Alternance sign_in/sign_out check.
            Previous (if exists) must be of opposite action.
            Next (if exists) must be of opposite action.
        """
        return True
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
    _constraints = [(lambda f: True, 'Error ! Sign in (resp. Sign out) must follow Sign out (resp. Sign in)', ['action'])]
    _constraints = []
    def _auto_init(self, cr, context=None):
        
        self._constraints = [(lambda f: True, 'Error ! Sign in (resp. Sign out) must follow Sign out (resp. Sign in)', ['action'])]
        raise Warning(self._constraints)
        super(hr_attendance, self)._auto_init(cr, context)
=======
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
>>>>>>> 107e45bfaa707ab23f72391771972bfe729e7934

class hr_payslip_run(models.Model):
    _inherit = 'hr.payslip.run'

    @api.model
    def generate_csv(self):
        temp = tempfile.NamedTemporaryFile(mode='w+t',suffix='.csv')
        rules = self.env['hr.salary.rule'].search([('active', '=', True), ('appears_on_payslip', '=', True)], order='sequence, salary_art')
        labelwriter = None
        for slip in self.slip_ids.sorted(key=lambda s: s.employee_id.contract_id.name):
            if not labelwriter:
                columns = ['Anst nr', 'Name']
                labelwriter = csv.DictWriter(temp, columns + ['%s\n%s' %(r.name.replace(u'ö', 'o').replace(u'å', 'a').replace(u'ä', 'a').encode('ascii', 'ignore'), r.salary_art) for r in rules if r.salary_art])
                labelwriter.writeheader()
            labelwriter.writerow(slip.get_payslip_run_row(rules))
        temp.seek(0)
        self.env['ir.attachment'].create({
            'name': self.name.replace(' ', '_') + '.csv',
            'res_name': self.name,
            'res_model': self._name,
            'res_id': self.id,
            'datas': base64.encodestring(temp.read()),
            'datas_fname': self.name.replace(' ', '_') + '.csv',
        })
        temp.close()
        return True

    @api.one
    def _company_id(self):
        self.company_id = self.env['res.company'].browse(self.env['res.users'].browse(self._uid)._get_company())
    company_id = fields.Char(compute="_company_id")

    # fields match Arbetsgivardeklaration document from Swelon.se
    @api.one
    def _nbr_employee(self):
        self.nbr_employee = len(self.slip_ids)
    nbr_employee = fields.Integer(compute="_nbr_employee")

    @api.one
    def _taxable_salary(self): #50
        self.taxable_salary = sum([s.get_slip_line('bl')[0]['total'] for s in self.slip_ids if s.get_slip_line('bl')])
    taxable_salary = fields.Integer(compute="_taxable_salary")

    @api.one
    def _social_normal_fees(self): #55 & 56
        self.fully_social_normal_fees = sum([s.get_slip_line('san')[0]['amount'] for s in self.slip_ids if s.get_slip_line('san')])
        self.social_normal_fees = sum([s.get_slip_line('san')[0]['total'] for s in self.slip_ids if s.get_slip_line('san')])
    fully_social_normal_fees = fields.Integer(compute="_social_normal_fees")
    social_normal_fees = fields.Integer(compute="_social_normal_fees")

    @api.one
    def _social_youth_fees(self): #57 & 58
        self.fully_social_youth_fees = sum([s.get_slip_line('sau')[0]['amount'] for s in self.slip_ids if s.get_slip_line('sau')])
        self.social_youth_fees = sum([s.get_slip_line('sau')[0]['total'] for s in self.slip_ids if s.get_slip_line('sau')])
    fully_social_youth_fees = fields.Integer(compute="_social_youth_fees")
    social_youth_fees = fields.Integer(compute="_social_youth_fees")

    @api.one
    def _social_retired_fees(self): #59 & 60
        self.fully_social_retired_fees = sum([s.get_slip_line('sap')[0]['amount'] for s in self.slip_ids if s.get_slip_line('sap')])
        self.social_retired_fees = sum([s.get_slip_line('sap')[0]['total'] for s in self.slip_ids if s.get_slip_line('sap')])
    fully_social_retired_fees = fields.Integer(compute="_social_retired_fees")
    social_retired_fees = fields.Integer(compute="_social_retired_fees")

    @api.one
    def _total_tax(self): #82/88
        self.total_tax = sum([s.get_slip_line('pre')[0]['total'] for s in self.slip_ids if s.get_slip_line('pre')])
    total_taxable = fields.Integer(compute="_total_tax")

    @api.one
    def _general_payroll_tax(self): #70/78
        self.general_payroll_tax = sum([s.get_slip_line('sa')[0]['total'] for s in self.slip_ids if s.get_slip_line('sa')])
    general_payroll_tax = fields.Integer(compute="_general_payroll_tax")

    @api.one
    def _net_salary(self): #81
        self.net_salary = sum([s.get_slip_line('net')[0]['total'] for s in self.slip_ids if s.get_slip_line('net')])
    net_salary = fields.Integer(compute="_net_salary")

class hr_payslip(models.Model):
    _inherit = 'hr.payslip'

    @api.model
    def get_payslip_run_row(self, rules):
        rec = {
            'Anst nr': self.employee_id.contract_id.name.encode('utf-8') if self.employee_id.contract_id else 'N/A',
            'Name': self.employee_id.name.encode('utf-8'),
        }
        for r in rules:
            if r.salary_art and self.get_slip_line(r.code):
                rec['%s\n%s' %(r.name.replace(u'ö', 'o').replace(u'å', 'a').replace(u'ä', 'a').encode('ascii', 'ignore'), r.salary_art)] = self.get_slip_line(r.code)[0]['total']
        return rec

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
