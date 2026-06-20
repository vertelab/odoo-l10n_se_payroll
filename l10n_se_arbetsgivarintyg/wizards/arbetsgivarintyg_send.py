# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2024- Vertel AB (<https://vertel.se>).
#
##############################################################################

"""
Wizard: Send arbetsgivarintyg to arbetsgivarintyg.nu via SOAP API.

This wizard shows a summary before sending and handles the API call.
"""

import logging

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ArbetsgivarintygSendWizard(models.TransientModel):
    """Wizard to confirm and send an arbetsgivarintyg to the API."""
    _name = 'l10n_se.arbetsgivarintyg.send.wizard'
    _description = 'Send Arbetsgivarintyg Wizard'

    intyg_id = fields.Many2one(
        'l10n_se.arbetsgivarintyg',
        string='Arbetsgivarintyg',
        required=True,
        readonly=True,
    )
    summary = fields.Text(
        string='Sammanfattning',
        compute='_compute_summary',
    )
    api_url = fields.Char(
        string='API URL',
        related='intyg_id.company_id.arbetsgivarintyg_api_url',
        readonly=True,
    )
    test_mode = fields.Boolean(
        string='Testläge',
        related='intyg_id.company_id.arbetsgivarintyg_test_mode',
        readonly=True,
    )

    def _compute_summary(self):
        for wizard in self:
            if wizard.intyg_id:
                intyg = wizard.intyg_id
                lines = [
                    f'Arbetsgivare: {intyg.ag_namn} ({intyg.ag_orgnummer})',
                    f'Arbetstagare: {intyg.at_fornamn} {intyg.at_efternamn} '
                    f'({intyg.at_personnummer})',
                    f'Befattning: {intyg.befattning}',
                    f'Anställning: {intyg.anstallning_start} → '
                    f'{intyg.anstallning_slut or "pågående"}',
                    f'Anställningsform: {intyg.anstallningsform}',
                    f'Lön: {intyg.lon_belopp} kr ({intyg.lon_typ})',
                    f'Arbetstid: {intyg.arbetstid_typ} '
                    f'({intyg.arbetstid_procent}%)',
                    '',
                    f'Radposter:',
                    f'  Tjänstledigheter: {len(intyg.tjanstledighet_ids)}',
                    f'  Arbetad tid månader: {len(intyg.arbetad_tid_ids)}',
                    f'  Lönetillägg: {len(intyg.lonetillagg_ids)}',
                    '',
                    f'API: {wizard.api_url}',
                    f'Testläge: {"Ja" if wizard.test_mode else "Nej"}',
                ]
                wizard.summary = '\n'.join(lines)
            else:
                wizard.summary = ''

    def action_confirm_send(self):
        """Send the certificate via SOAP API."""
        self.ensure_one()
        intyg = self.intyg_id

        # Validate required fields before sending
        self._validate_intyg(intyg)

        from ..api.arbetsgivarintyg_client import send_arbetsgivarintyg

        try:
            result = send_arbetsgivarintyg(intyg)
        except UserError:
            raise
        except Exception as e:
            _logger.error('Failed to send certificate: %s', e, exc_info=True)
            raise UserError(_(
                'Failed to send certificate.\n'
                'Error: %s'
            ) % str(e))

        if result['result_code'] == 0:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _(
                        'Certificate sent successfully!\n'
                        'The employer must now sign it on arbetsgivarintyg.nu.'
                    ),
                    'sticky': True,
                    'type': 'success',
                    'next': {
                        'type': 'ir.actions.act_window_close',
                    },
                },
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _(
                        'Failed to send certificate.\n'
                        'ResultCode: %(code)s\n'
                        'Message: %(msg)s\n\n'
                        'Certificate set to Error state. '
                        'Fix the issues and try again.',
                        code=result['result_code'],
                        msg=result['result_message'],
                    ),
                    'sticky': True,
                    'type': 'danger',
                    'next': {
                        'type': 'ir.actions.act_window_close',
                    },
                },
            }

    def _validate_intyg(self, intyg):
        """Validate that required fields are filled before sending."""
        errors = []

        if not intyg.at_fornamn:
            errors.append(_('Förnamn saknas.'))
        if not intyg.at_efternamn:
            errors.append(_('Efternamn saknas.'))
        if not intyg.at_personnummer:
            errors.append(_('Personnummer saknas.'))
        if not intyg.befattning:
            errors.append(_('Befattning saknas.'))
        if not intyg.anstallning_start:
            errors.append(_('Anställningens startdatum saknas.'))
        if not intyg.lon_belopp:
            errors.append(_('Lönebelopp saknas.'))
        if not intyg.samtycke:
            errors.append(_('Samtycke från arbetstagaren saknas.'))

        if errors:
            raise UserError(
                _('Följande obligatoriska fält saknas:\n\n') +
                '\n'.join(f'• {e}' for e in errors)
            )
