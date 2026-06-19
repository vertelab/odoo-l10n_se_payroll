import logging

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class HrContract(models.Model):
    _inherit = 'hr.contract'

    benefit_ids = fields.One2many(
        comodel_name="hr.contract.benefit",
        inverse_name='contract_id',
        string="Förmåner")

    benefit_summary = fields.Text(
        string="Förmånssammanställning",
        compute='_compute_benefit_summary')

    @api.depends('benefit_ids', 'benefit_ids.value', 'benefit_ids.date_start', 'benefit_ids.date_end')
    def _compute_benefit_summary(self):
        for contract in self:
            if not contract.benefit_ids:
                contract.benefit_summary = ''
                continue
            lines = []
            for b in contract.benefit_ids:
                period = ''
                if b.date_start or b.date_end:
                    period = f" ({b.date_start or '∞'} – {b.date_end or '∞'})"
                lines.append(f"{b.name.name}: {b.value:,.0f} kr/mån{period}")
            contract.benefit_summary = '\n'.join(lines)

    def benefit_value(self, code, date_from=None, date_to=None):
        """Return total benefit value for given code and date range."""
        self.ensure_one()
        benefits = self.benefit_ids.filtered(lambda b: 
            b.name.name == code or 
            (b.name.code_id and b.name.code_id.code == code)
        )
        if date_from and date_to:
            benefits = benefits.filtered(lambda b: (
                (not b.date_start or b.date_start <= date_to) and
                (not b.date_end or b.date_end >= date_from)
            ))
        return sum(benefits.mapped('value'))

    def benefit_sum(self, date_from=None, date_to=None):
        """Return total value of all benefits for date range."""
        self.ensure_one()
        total = 0.0
        for benefit in self.benefit_ids:
            if date_from and date_to:
                if (benefit.date_start and benefit.date_start > date_to):
                    continue
                if (benefit.date_end and benefit.date_end < date_from):
                    continue
            total += benefit.value
        return total


class HrContractBenefit(models.Model):
    _name = 'hr.contract.benefit'
    _description = 'Kontraktsförmån'

    contract_id = fields.Many2one(
        comodel_name="hr.contract",
        string="Kontrakt",
        required=True,
        ondelete='cascade')

    currency_id = fields.Many2one(
        'res.currency',
        related='contract_id.company_id.currency_id',
        string="Valuta")

    name = fields.Many2one(
        comodel_name='hr.benefit',
        string="Förmånstyp",
        required=True)

    desc = fields.Char(
        string="Beskrivning",
        related='name.desc',
        readonly=False)

    value = fields.Float(
        string="Värde/mån",
        required=True,
        help="Förmånsvärde per månad (beskattningsvärde)")

    date_start = fields.Date(
        string="Gäller fr.o.m.",
        help="Från vilket datum förmånen gäller. Tomt = från kontraktsstart.")

    date_end = fields.Date(
        string="Gäller t.o.m.",
        help="Sista dag förmånen gäller. Tomt = tillsvidare.")

    note = fields.Text(string="Notering")


class HrBenefit(models.Model):
    _name = 'hr.benefit'
    _description = 'Förmånstyp'

    name = fields.Char(
        string="Kod",
        required=True,
        help="Unik kod för förmånen, t.ex. 'forman_carbru'")

    desc = fields.Char(
        string="Benämning",
        required=True,
        help="Läsbar beskrivning, t.ex. 'Bilförmån brutto'")

    code_id = fields.Many2one(
        comodel_name='hr.salary.rule',
        string="Kopplad löneregel",
        help="Löneregeln som beräknar förmånsvärdet på lönespecen")

    category = fields.Selection([
        ('vehicle', 'Bil / Motorfordon'),
        ('housing', 'Bostad'),
        ('meal', 'Måltider / Lunchkuponger'),
        ('travel', 'Resor / Traktamente'),
        ('other', 'Övrigt'),
    ], string="Kategori", default='other')

    note = fields.Text(string="Notering")

    active = fields.Boolean(string="Aktiv", default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Förmånskoden måste vara unik!'),
    ]
