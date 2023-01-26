# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, tools

import logging

_logger = logging.getLogger(__name__)


class ReportSalaryTaskUser(models.Model):
    _name = "report.salary.task"
    _description = "Salary Analysis"
    _auto = False


    payslip_id = fields.Many2one(comodel_name='hr.payslip')
    date = fields.Date(string="date")

    code = fields.Char()
    net = fields.Float()
    prej = fields.Float()
    sa = fields.Float()
    bl = fields.Float()

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Employee",
    )
    period_id = fields.Many2one(
        comodel_name='account.period', 
        string="Period",
        readonly=True,
    )
    payslip_run_id = fields.Many2one(
        comodel_name="hr.payslip.run",
        string="Payslip Batches",
    )

    def _select_salary(self, fields=None):
        if not fields:
            fields = {}
        
        select_str = """
            t.id as id,
            t.id as payslip_id,
            t.employee_id,
            t.period_id,
            t.payslip_run_id,
            l.code,
            CASE WHEN l.code='bl' THEN sum(l.total) ELSE 0 END as bl,
            CASE WHEN l.code='net' THEN sum(l.total) ELSE 0 END as net,
            CASE WHEN l.code='prej' THEN sum(l.total) ELSE 0 END as prej,
            CASE WHEN l.code='sa' THEN sum(l.total) ELSE 0 END as sa,
            t.date_from as date
           
            """
        for field in fields.values():
            select_str += field
        return select_str

    def _group_by_salary(self, groupby=''):
        group_by_str = """
            t.id,
            t.employee_id,
            t.period_id,
            t.payslip_run_id,
            l.code,
            t.date_from
            """
        return group_by_str

    def _from_sale(self, from_clause=''):
        from_ = """
                hr_payslip_line l
                      right outer join hr_payslip t on (t.id=l.slip_id)
                      join hr_employee employee on t.employee_id = employee.id
                        left join account_period p on (t.period_id=p.id)
                %s
        """ % from_clause
        return from_

    def _query(self, with_clause='', fields=None, groupby='', from_clause=''):
        if not fields:
            fields = {}
        with_ = ("WITH %s" % with_clause) if with_clause else ""
        return '%s (SELECT %s FROM %s GROUP BY %s)' % \
               (with_, self._select_salary(fields), self._from_sale(from_clause), self._group_by_salary(groupby))


    def init(self):
        tools.drop_view_if_exists(self._cr,self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))


