from odoo import models, fields


class HrNyk(models.Model):
    _name = 'hr.nyk'
    _description = 'NYK - Swedish Occupational Classification Code'
    _order = 'code'

    code = fields.Char(string='NYK-kod (6 siffror)', required=True, index=True)
    name = fields.Char(string='Yrkesbenämning', required=True, translate=True)
    category = fields.Char(string='Kategori/Yrkesområde')
    description = fields.Text(string='Beskrivning av ansvarsnivå / Arbetsuppgifter')
