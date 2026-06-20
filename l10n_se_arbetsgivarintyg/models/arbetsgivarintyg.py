# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2024- Vertel AB (<https://vertel.se>).
#
##############################################################################

import logging
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class Arbetsgivarintyg(models.Model):
    """Swedish employer certificate (arbetsgivarintyg) for a-kassa.

    Based on the technical specification from Sveriges a-kassor:
    https://stsakassa.se/sites/default/files/2018-11/
    Teknisk%20specifikation%20arbetsgivarintyg.nu_.pdf
    """
    _name = 'l10n_se.arbetsgivarintyg'
    _description = 'Arbetsgivarintyg (Employer Certificate)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    # -- Active / State ------------------------------------------------------
    active = fields.Boolean(default=True)
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('populated', 'Populated'),
            ('sent', 'Sent'),
            ('signed', 'Signed'),
            ('done', 'Done'),
            ('error', 'Error'),
        ],
        string='Status',
        default='draft',
        tracking=True,
        required=True,
        copy=False,
    )

    # -- Relations -----------------------------------------------------------
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
    )
    contract_id = fields.Many2one(
        'hr.contract',
        string='Contract',
        domain="[('employee_id', '=', employee_id)]",
    )

    # -- Metadata ------------------------------------------------------------
    name = fields.Char(
        string='Reference',
        compute='_compute_name',
        store=True,
    )
    agp_version = fields.Char(
        string='API Version',
        default='1.0',
        help='Version av AGP API som används.',
    )
    skickat_tidpunkt = fields.Datetime(
        string='Sent at',
        readonly=True,
        copy=False,
    )
    api_result_code = fields.Integer(
        string='API Result Code',
        readonly=True,
        copy=False,
    )
    api_result_message = fields.Text(
        string='API Result Message',
        readonly=True,
        copy=False,
    )

    # -- Samtycke ------------------------------------------------------------
    samtycke = fields.Boolean(
        string='Samtycke',
        required=True,
        help='Samtycke från arbetstagaren att skicka in uppgifterna.',
    )

    # === ARBETSGIVARE (Employer) [56-58] ====================================
    anvand_registrerad_info = fields.Boolean(
        string='Use Registered Information',
        default=True,
        help='Använd den företagsinformation som redan är registrerad '
             'på arbetsgivarintyg.nu istället för nedanstående uppgifter.',
    )
    ag_namn = fields.Char(string='Företagsnamn (56)', size=50)
    ag_orgnummer = fields.Char(string='Organisationsnummer (58)', size=16)
    ag_gatuadress = fields.Char(string='Gatuadress', size=50)
    ag_co = fields.Char(string='Care Of', size=50)
    ag_ort = fields.Char(string='Ort', size=30)
    ag_postnummer = fields.Char(string='Postnummer', size=6)
    ag_epost = fields.Char(string='E-postadress', size=256)
    ag_telefon = fields.Char(string='Telefonnummer', size=15)

    # === ARBETSTAGARE (Employee) [1-3] =====================================
    at_fornamn = fields.Char(string='Förnamn (1)', size=20, required=True)
    at_efternamn = fields.Char(string='Efternamn (2)', size=35, required=True)
    at_personnummer = fields.Char(string='Personnummer (3)', size=16, required=True)
    at_epost = fields.Char(string='E-postadress', size=256)
    at_telefon = fields.Char(string='Telefonnummer', size=15)
    at_skicka_sms = fields.Boolean(string='Skicka SMS')

    # === ANSTÄLLNING (Employment) [4-13] ====================================
    befattning = fields.Char(string='Befattning (7)', size=60, required=True)
    anstallning_start = fields.Date(string='Anställning start (4)', required=True)
    anstallning_slut = fields.Date(string='Anställning slut (5)')
    fortfarande_anstalld = fields.Boolean(string='Fortfarande anställd (6)')
    anstallningsform = fields.Selection(
        selection=[
            ('Ingen', 'Ingen'),
            ('Provanstallning', 'Provanställning'),
            ('Tidsbegransad', 'Tidsbegränsad'),
            ('Behovsanstalld', 'Behovsanställd'),
            ('Tillsvidare', 'Tillsvidare'),
        ],
        string='Anställningsform (11)',
        required=True,
        default='Tillsvidare',
    )
    provanstallning_slut = fields.Date(string='Provanställning slutdatum (12)')
    tidsbegransad_slut = fields.Date(string='Tidsbegränsad anställning slutdatum (13)')

    # === TJÄNSTLEDIGHET (Leave of Absence) [8-10] ===========================
    tjanstledig = fields.Boolean(string='Tjänstledig', required=True, default=False)
    tjanstledighet_ids = fields.One2many(
        'l10n_se.arbetsgivarintyg.tjanstledighet',
        'intyg_id',
        string='Tjänstledigheter',
        copy=True,
    )

    # === ARBETSTID (Working Hours) [15-19] ==================================
    arbetstid_typ = fields.Selection(
        selection=[
            ('Ingen', 'Ingen'),
            ('Heltid', 'Heltid'),
            ('Deltid', 'Deltid'),
            ('VarierandeArbetstid', 'Varierande arbetstid'),
        ],
        string='Arbetstid typ (15)',
        required=True,
        default='Heltid',
    )
    arbetstid_heltid_tim = fields.Float(
        string='Heltid tim/vecka (16)',
        digits=(18, 2),
    )
    arbetstid_deltid_tim = fields.Float(
        string='Deltid tim/vecka (17)',
        digits=(18, 2),
    )
    arbetstid_procent = fields.Float(
        string='Procent av heltid (18)',
        digits=(18, 2),
    )
    anstalld_bemanning = fields.Boolean(
        string='Anställd i bemanning (19)',
        required=True,
        default=False,
    )
    skiftarbete = fields.Boolean(
        string='Skiftarbete',
        required=True,
        default=False,
    )

    # === UPPHÖRANDEORSAK (Termination) [20-24] ==============================
    upphorandeorsak = fields.Selection(
        selection=[
            ('Ingen', 'Ingen'),
            ('UppsagdArbetsbrist', 'Uppsagd pga arbetsbrist'),
            ('TidsbegransadAnstallning', 'Tidsbegränsad anställning upphör'),
            ('EgenBegaran', 'Egen begäran'),
            ('SlutProvanstallningAnstalldBeslut', 'Provanställning avslutad av anställd'),
            ('SlutProvanstallningArbetsgivareBeslut', 'Provanställning avslutad av arbetsgivare'),
            ('Konkurs', 'Konkurs'),
            ('AnnanOrsak', 'Annan orsak'),
        ],
        string='Upphörandeorsak (20)',
        required=True,
        default='Ingen',
    )
    beskedsdatum = fields.Date(string='Beskedsdatum (21)')
    tidsbegransad_besked = fields.Date(
        string='Datum för besked om tidsbegränsad anställning (22)',
    )
    annan_orsak_text = fields.Char(string='Annan orsak (23)', size=256)
    avgangsvederlag_avtal = fields.Boolean(
        string='Avgångsvederlag — ingått avtal (24)',
        required=True,
        default=False,
    )

    # === ERBJUDANDE OM FORTSATT ARBETE [25-34] =============================
    erbjudande_finns = fields.Boolean(
        string='Erbjudande finns (25)',
        required=True,
        default=False,
    )
    erbjudande_start = fields.Date(string='Erbjudande omfattning start (26)')
    erbjudande_slut = fields.Date(string='Erbjudande omfattning slut (27)')
    erbjudande_tillsvidare = fields.Boolean(string='Tillsvidareanställning (28)')
    erbjudande_heltid_tim = fields.Float(
        string='Tim/vecka heltid (29)',
        digits=(18, 2),
    )
    erbjudande_deltid_tim = fields.Float(
        string='Tim/vecka deltid (30)',
        digits=(18, 2),
    )
    erbjudande_procent = fields.Float(
        string='Procent av heltid (31)',
        digits=(18, 2),
    )
    erbjudande_arbetstid = fields.Selection(
        selection=[
            ('Ingen', 'Ingen'),
            ('Heltid', 'Heltid'),
            ('Deltid', 'Deltid'),
            ('VarierandeArbetstid', 'Varierande arbetstid'),
        ],
        string='Arbetstid erbjudande (32)',
    )
    erbjudande_accepterat = fields.Boolean(string='Accepterat erbjudande (33)')
    erbjudande_avbojt_datum = fields.Date(string='Datum avböjt erbjudande (34)')

    # === LÖN (Salary) [43-49] ===============================================
    lon_ar = fields.Integer(string='Löneår (43)')
    lon_typ = fields.Selection(
        selection=[
            ('Ingen', 'Ingen'),
            ('Manadslon', 'Månadslön'),
            ('Veckolon', 'Veckolön'),
            ('Daglon', 'Daglön'),
            ('Timlon', 'Timlön'),
        ],
        string='Typ av lön (44)',
        required=True,
        default='Manadslon',
    )
    lon_belopp = fields.Float(
        string='Lönebelopp (45)',
        digits=(18, 2),
        required=True,
    )
    lon_varierande_timlon = fields.Boolean(string='Varierande timlön (46)')
    lon_overtid = fields.Float(string='Övertidstillägg (47)', digits=(18, 2))
    lon_mertid = fields.Float(string='Mertidstillägg (48)', digits=(18, 2))
    lon_extra = fields.Boolean(
        string='Extra lön (49)',
        required=True,
        default=False,
    )
    lonetillagg_ids = fields.One2many(
        'l10n_se.arbetsgivarintyg.lonetillagg',
        'intyg_id',
        string='Andra lönetillägg',
        copy=True,
    )

    # === ARBETAD TID (Worked Time) [35-42] ==================================
    arbetad_tid_start = fields.Date(string='Arbetad tid start (35)')
    arbetad_tid_slut = fields.Date(string='Arbetad tid slut (36)')
    arbetad_tid_ids = fields.One2many(
        'l10n_se.arbetsgivarintyg.arbetad_tid',
        'intyg_id',
        string='Arbetad tid per månad',
        copy=True,
    )
    undervisningstid = fields.Boolean(
        string='Undervisningstid',
        required=True,
        default=False,
    )
    undervisningstimmar = fields.Float(
        string='Undervisningstimmar (42)',
        digits=(18, 2),
    )

    # === LÄRARLÖN (Teacher Salary) [50-54] ==================================
    ferielon = fields.Boolean(
        string='Ferielön (50)',
        required=True,
        default=False,
    )
    ferielon_dagar = fields.Integer(string='Ferielön dagar (51)')
    ferielon_belopp = fields.Float(string='Ferielön belopp (52)', digits=(18, 2))
    uppehallslon = fields.Boolean(
        string='Uppehållslön (53)',
        required=True,
        default=False,
    )
    uppehallslon_belopp = fields.Float(
        string='Uppehållslön belopp (54)',
        digits=(18, 2),
    )
    semester_start = fields.Date(string='Semester start')
    semester_slut = fields.Date(string='Semester slut')

    # === ÖVRIGT (Other) [55] ================================================
    ovrig_upplysning = fields.Text(string='Övrig upplysning (55)')

    # === SOFTWARE INFO ======================================================
    software_supplier = fields.Char(
        string='Leverantör',
        default='Vertel AB',
    )
    software_name = fields.Char(
        string='Mjukvarunamn',
        default='Odoo l10n_se_payroll',
    )
    software_version = fields.Char(
        string='Version',
        default='1.0',
    )
    software_build = fields.Char(string='Build')

    # ========================================================================
    # COMPUTED FIELDS
    # ========================================================================

    @api.depends('employee_id', 'create_date')
    def _compute_name(self):
        for record in self:
            if record.employee_id:
                emp = record.employee_id.name
                dt = record.create_date or fields.Datetime.now()
                record.name = f'{emp} — {dt.strftime("%Y-%m-%d")}'
            else:
                record.name = _('New Certificate')

    # ========================================================================
    # CONSTRAINTS
    # ========================================================================

    @api.constrains('at_personnummer')
    def _check_personnummer(self):
        for record in self:
            if record.at_personnummer and len(record.at_personnummer.replace('-', '')) != 12:
                raise ValidationError(
                    _('Personnummer måste vara ÅÅÅÅMMDD-XXXX (12 siffror).'))

    @api.constrains('samtycke')
    def _check_samtycke(self):
        for record in self:
            if record.state in ('sent', 'signed', 'done') and not record.samtycke:
                raise ValidationError(
                    _('Samtycke från arbetstagaren krävs för att skicka intyget.'))

    # ========================================================================
    # ACTIONS
    # ========================================================================

    def action_populate_from_employee(self):
        """Auto-populate certificate data from Odoo employee/contract/payslip."""
        self.ensure_one()
        employee = self.employee_id
        contract = self.contract_id or employee.contract_id
        company = self.company_id

        if not employee:
            raise UserError(_('No employee selected.'))

        # -- Arbetstagare --
        self.at_fornamn = self.at_fornamn or employee.first_name or ''
        self.at_efternamn = self.at_efternamn or employee.last_name or ''
        # Try to get personnummer from employee identification_id or private fields
        if not self.at_personnummer:
            self.at_personnummer = (
                employee.identification_id
                or (employee.address_home_id and employee.address_home_id.vat)
                or ''
            )
        self.at_epost = self.at_epost or employee.work_email or ''
        self.at_telefon = self.at_telefon or employee.work_phone or employee.mobile_phone or ''

        # -- Arbetsgivare --
        if company:
            self.ag_namn = self.ag_namn or company.name or ''
            self.ag_orgnummer = self.ag_orgnummer or company.vat or ''
            if company.partner_id:
                addr = company.partner_id
                self.ag_gatuadress = self.ag_gatuadress or addr.street or ''
                self.ag_ort = self.ag_ort or addr.city or ''
                self.ag_postnummer = self.ag_postnummer or addr.zip or ''
                self.ag_epost = self.ag_epost or addr.email or ''
                self.ag_telefon = self.ag_telefon or addr.phone or ''

        # -- Anställning --
        if contract:
            self.contract_id = contract
            self.befattning = self.befattning or contract.job_id.name or ''
            self.anstallning_start = self.anstallning_start or contract.date_start
            self.anstallning_slut = self.anstallning_slut or contract.date_end
            self.fortfarande_anstalld = not bool(contract.date_end)
            self.arbetstid_procent = self.arbetstid_procent or contract.resource_calendar_id and 100.0 or 0.0

            # Map contract type to anstallningsform
            if not self.anstallningsform or self.anstallningsform == 'Ingen':
                contract_type_map = {
                    'CDI': 'Tillsvidare',
                    'CDD': 'Tidsbegransad',
                }
                self.anstallningsform = contract_type_map.get(
                    contract.contract_type_id and contract.contract_type_id.code or '',
                    'Tillsvidare',
                )

            # Lön
            if contract.wage:
                self.lon_belopp = self.lon_belopp or contract.wage
                wage_type_map = {
                    'monthly': 'Manadslon',
                    'hourly': 'Timlon',
                    'daily': 'Daglon',
                    'weekly': 'Veckolon',
                }
                struct = contract.structure_type_id
                if struct:
                    self.lon_typ = wage_type_map.get(
                        struct.default_schedule_pay or 'monthly', 'Manadslon')
                else:
                    self.lon_typ = 'Manadslon'

        # -- Arbetad tid (from payslips, last 13 months) --
        self._populate_arbetad_tid()

        # -- Tjänstledigheter (from hr.leave) --
        self._populate_tjanstledighet()

        self.state = 'populated'
        self.message_post(body=_('Data populated from employee/contract/payslip.'))

    def _populate_arbetad_tid(self):
        """Generate arbetad_tid lines from payslip records (last 13 months)."""
        self.ensure_one()
        if self.arbetad_tid_ids:
            return  # Already populated

        end_date = self.anstallning_slut or date.today()
        start_date = end_date - relativedelta(months=13)

        # Get payslips
        payslips = self.env['hr.payslip'].search([
            ('employee_id', '=', self.employee_id.id),
            ('date_from', '>=', start_date),
            ('date_to', '<=', end_date),
            ('state', 'in', ['done', 'paid']),
        ], order='date_from')

        if not payslips:
            return

        # Collect monthly data
        monthly = {}
        for slip in payslips:
            key = (slip.date_to.year, slip.date_to.month)
            if key not in monthly:
                monthly[key] = {
                    'arbetade_timmar': 0.0,
                    'franvaro': 0.0,
                    'overtid': 0.0,
                    'mertid': 0.0,
                }
            for line in slip.line_ids:
                code = line.salary_rule_id.code or ''
                if code in ('WORK100', 'BASIC'):
                    # This is regular work - count from worked_days
                    pass
                elif code in ('ABSENCE', 'FRANV'):
                    monthly[key]['franvaro'] += line.number_of_hours or line.amount
                elif code in ('OVERTIME', 'OVERTID'):
                    monthly[key]['overtid'] += line.number_of_hours or line.amount
                elif code in ('MERTID',):
                    monthly[key]['mertid'] += line.number_of_hours or line.amount

            # Add worked days hours
            for wd in slip.worked_days_line_ids:
                if wd.code in ('WORK100',):
                    monthly[key]['arbetade_timmar'] += wd.number_of_hours

        # Create lines
        self.arbetad_tid_start = start_date
        self.arbetad_tid_slut = end_date

        lines = []
        for key, data in sorted(monthly.items()):
            lines.append((0, 0, {
                'ar': key[0],
                'manad': key[1],
                'arbetade_timmar': data['arbetade_timmar'],
                'franvaro': data['franvaro'],
                'overtid': data['overtid'],
                'mertid': data['mertid'],
            }))
        self.arbetad_tid_ids = lines

    def _populate_tjanstledighet(self):
        """Generate tjanstledighet lines from hr.leave records."""
        self.ensure_one()
        if self.tjanstledighet_ids:
            return

        leaves = self.env['hr.leave'].search([
            ('employee_id', '=', self.employee_id.id),
            ('state', '=', 'validate'),
            ('date_from', '>=', self.anstallning_start),
        ])

        if not leaves:
            return

        self.tjanstledig = True
        lines = []
        for leave in leaves:
            lines.append((0, 0, {
                'start': leave.date_from.date(),
                'slut': leave.date_to.date(),
                'omfattning_procent': 100,  # Full leave by default
                'orsak': leave.holiday_status_id.name or '',
            }))
        self.tjanstledighet_ids = lines

    def action_send_to_api(self):
        """Open the wizard to send certificate to arbetsgivarintyg.nu."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Skicka till arbetsgivarintyg.nu'),
            'res_model': 'l10n_se.arbetsgivarintyg.send.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_intyg_id': self.id,
            },
        }

    def action_reset_to_draft(self):
        """Reset certificate to draft state."""
        self.ensure_one()
        self.state = 'draft'
        self.api_result_code = 0
        self.api_result_message = ''

    def action_mark_signed(self):
        """Mark certificate as signed (manual step after employer signs in portal)."""
        self.ensure_one()
        if self.state != 'sent':
            raise UserError(_('Only sent certificates can be marked as signed.'))
        self.state = 'signed'

    def action_mark_done(self):
        """Mark certificate as done (employee has sent to a-kassa)."""
        self.ensure_one()
        if self.state != 'signed':
            raise UserError(_('Only signed certificates can be marked as done.'))
        self.state = 'done'
