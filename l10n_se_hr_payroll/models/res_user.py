# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from odoo import fields, models, api, _

from odoo.exceptions import UserError, ValidationError, RedirectWarning, Warning

class HrPayslip(models.TransientModel):
    _name = "user.payslip"

    name = fields.Char(
        string="Payslip Name", readonly=True, states={"draft": [("readonly", False)]}
    )
    number = fields.Char(
        string="Reference",
        readonly=True,
    )
    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Employee",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("verify", "Waiting"),
            ("done", "Done"),
            ("cancel", "Rejected"),
        ],
        string="Status",
        readonly=True,
        help="""* When the payslip is created the status is \'Draft\'
        \n* If the payslip is under verification, the status is \'Waiting\'.
        \n* If the payslip is confirmed then status is set to \'Done\'.
        \n* When user cancel payslip the status is \'Rejected\'.""",
    )
    paid = fields.Boolean(
        string="Made Payment Order ? ",
        readonly=True,
    )
    credit_note = fields.Boolean(
        string="Credit Note",
        readonly=True,
        help="Indicates this payslip has a refund of another",
    )
    payslip_run_id = fields.Many2one(
        comodel_name="hr.payslip.run",
        string="Payslip Batches",
    )
    period_id = fields.Many2one(comodel_name='account.period', string="Period",
        readonly=True,)

    def payslip_report(self):
        # ~ data = self.read(cr, uid, ids)[0]
        payslip = self.env['hr.payslip'].sudo().browse(self.id)
        
        # ~ action = self.env.ref('l10n_se_hr_payroll.payslip').report_action(docids=payslip, data={}, config=False)
        report_name = "l10n_se_hr_payroll.payslip"
        # ~ pdf = self.env['user.payslip'].sudo().get_pdf(payslip, report_name)
        
        
        # ~ lines = self.with_context(print_mode=True).get_pdf_lines(line_data)
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        rcontext = {
            'mode': 'print',
            'base_url': base_url,
        }

        view_id = self.env['ir.ui.view'].sudo().get_view_id("l10n_se_hr_payroll.payslip")
        view_obj = self.env['ir.ui.view'].sudo().browse(view_id)
        # ~ raise Warning(view_obj._render({},'ir.qweb'))


        # ~ body = self.env['ir.ui.view']._render_template(
            # ~ "l10n_se_hr_payroll.payslip",{}
            # ~ values=dict(rcontext, lines=payslip, report=self, context=self),
        # ~ )

        header = self.env['ir.actions.report']._render_template("web.internal_layout", values=rcontext)
        header = self.env['ir.actions.report']._render_template("web.minimal_layout", values=dict(rcontext, subst=True, body=header))

        body = self.env['ir.actions.report']._render_template("l10n_se_hr_payroll.payslip_2_report", values=dict(datas=payslip))


        pdf  = self.env['ir.actions.report']._run_wkhtmltopdf(
            [body],
            header=header,
            landscape=False,
            specific_paperformat_args={'data-report-margin-top': 10, 'data-report-header-spacing': 10}
        )
        
        file = base64.b64encode(pdf)

        data = {
       # ~ 'from_date': self.from_date,
       # ~ 'to_date': self.to_date
        }
       # docids = self.env['sale.order'].search([]).ids
        return self.env.ref('l10n_se_hr_payroll.payslip').report_action(payslip, data={})


        return file
        # ~ datas = {
             # ~ 'ids': context.get('active_ids',[]),
             # ~ 'model': 'account.analytic.account',
             # ~ 'form': data
                 # ~ }
        # ~ return {
            # ~ 'type': 'ir.actions.report.xml',
            # ~ 'report_name': 'account.analytic.account.balance',
            # ~ 'datas': datas,
            # ~ }


    
class ResUsers(models.Model):
    _inherit = "res.users"

    def _payslip_nbr(self):
        self.payslip_nbr = len(self.employee_id.sudo().slip_ids if self.employee_id else 0)
    payslip_nbr = fields.Integer(string="Number Payslips",compute=_payslip_nbr)

    def payslip_action(self):
        self.env['user.payslip'].search([]).unlink()
        for slip in self.employee_id.sudo().slip_ids:
            self.env['user.payslip'].create({
                'name': slip.name,
                'number': slip.number,
                'employee_id': self.employee_id.id,
                'period_id': slip.period_id.id,
                'payslip_run_id': slip.payslip_run_id.id,
                'credit_note': slip.credit_note,
                'paid': slip.paid,
                'state': slip.state,
            })

        # ~ formview_ref = self.env.ref("payroll.hr_payslip_view_form", False)
        treeview_ref = self.env.ref("l10n_se_hr_payroll.user_payslip_view_tree", False)
        return {
            "name": _("Payslips"),
            "view_mode": "tree, form",
            "view_id": False,
            "res_model": "user.payslip",
            "type": "ir.actions.act_window",
            "target": "current",
            # ~ "domain": "[('id', 'in', %s)]" % copied_payslip.ids,
            "views": [
                (treeview_ref and treeview_ref.id or False, "tree"),
                # ~ (formview_ref and formview_ref.id or False, "form"),
            ],
            "context": {},
        }





