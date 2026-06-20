# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2024- Vertel AB (<https://vertel.se>).
#
##############################################################################

from odoo import fields, models


class ArbetsgivarintygTjanstledighet(models.Model):
    """Leave of absence periods for arbetsgivarintyg."""
    _name = 'l10n_se.arbetsgivarintyg.tjanstledighet'
    _description = 'Arbetsgivarintyg Tjänstledighet'
    _order = 'start'

    intyg_id = fields.Many2one(
        'l10n_se.arbetsgivarintyg',
        string='Arbetsgivarintyg',
        required=True,
        ondelete='cascade',
    )
    start = fields.Date(
        string='Start (8)',
        required=True,
        help='Startdatum för tjänstledigheten.',
    )
    slut = fields.Date(
        string='Slut (9)',
        required=True,
        help='Slutdatum för tjänstledigheten.',
    )
    omfattning_procent = fields.Integer(
        string='Omfattning % (10)',
        help='Tjänstledighetens omfattning i procent (0-100).',
    )
    orsak = fields.Text(
        string='Orsak',
        help='Orsak till tjänstledighet (fritext).',
    )


class ArbetsgivarintygArbetadTid(models.Model):
    """Monthly worked time records for arbetsgivarintyg (up to 13 months)."""
    _name = 'l10n_se.arbetsgivarintyg.arbetad_tid'
    _description = 'Arbetsgivarintyg Arbetad Tid'
    _order = 'ar desc, manad desc'

    intyg_id = fields.Many2one(
        'l10n_se.arbetsgivarintyg',
        string='Arbetsgivarintyg',
        required=True,
        ondelete='cascade',
    )
    ar = fields.Integer(
        string='År',
        required=True,
    )
    manad = fields.Integer(
        string='Månad',
        required=True,
        help='Månad 1-12.',
    )
    arbetade_timmar = fields.Float(
        string='Arbetade timmar (37)',
        digits=(18, 2),
        help='Antal arbetade timmar (exkl. övertid, mertid).',
    )
    franvaro = fields.Float(
        string='Frånvaro (38)',
        digits=(18, 2),
        help='Frånvaro i timmar (med löneavdrag).',
    )
    overtid = fields.Float(
        string='Övertid (39)',
        digits=(18, 2),
        help='Övertid i timmar.',
    )
    mertid = fields.Float(
        string='Mertid (40)',
        digits=(18, 2),
        help='Mertid/fyllnadstid i timmar.',
    )


class ArbetsgivarintygLonetillagg(models.Model):
    """Additional salary supplements for arbetsgivarintyg."""
    _name = 'l10n_se.arbetsgivarintyg.lonetillagg'
    _description = 'Arbetsgivarintyg Lönetillägg'
    _order = 'ar desc, manad desc'

    intyg_id = fields.Many2one(
        'l10n_se.arbetsgivarintyg',
        string='Arbetsgivarintyg',
        required=True,
        ondelete='cascade',
    )
    ar = fields.Integer(
        string='År (61)',
        required=True,
    )
    manad = fields.Integer(
        string='Månad (59)',
        required=True,
        help='Månad 1-12.',
    )
    belopp = fields.Float(
        string='Belopp (64)',
        digits=(18, 2),
    )
    dagar = fields.Float(
        string='Dagar (60)',
        digits=(18, 2),
    )
    timmar = fields.Float(
        string='Timmar (61)',
        digits=(18, 2),
    )
    beskrivning = fields.Char(
        string='Beskrivning (63)',
        size=256,
    )
    lonetillaggstyp = fields.Selection(
        selection=[
            ('Inget', 'Inget'),
            ('Sjuklon', 'Sjuklön'),
            ('Overtidstillagg', 'Övertidstillägg'),
            ('Mertid', 'Mertid'),
            ('Jour', 'Jour'),
            ('OB', 'OB'),
            ('AndraFormaner', 'Andra förmåner'),
        ],
        string='Typ av lönetillägg',
        default='Inget',
        required=True,
    )
