# -*- coding: utf-8 -*-
"""Extend res.company and res.config.settings with Växa-stöd settings."""

from odoo import fields, api, models, _
import logging

_logger = logging.getLogger(__name__)


class Company(models.Model):
    _inherit = 'res.company'

    # --- Skatteverket API: Växa-stöd endpoint ---
    skv_vaxa_api_url = fields.Char(
        string='SKV Växa-stöd API URL',
        compute='_compute_skv_vaxa_api_url',
        store=True,
        readonly=False,
        help="Skatteverket API endpoint for växa-stöd (growth support) "
             "reimbursement applications. "
             "Auto-populated based on test mode; override to customize.")

    @api.depends('skv_test_mode')
    def _compute_skv_vaxa_api_url(self):
        """Set default endpoint based on test/live mode when field is empty."""
        for company in self:
            if not company.skv_vaxa_api_url:
                if company.skv_test_mode:
                    company.skv_vaxa_api_url = (
                        'https://test.api.skatteverket.se/'
                        'arbetsgivare/v2/vaxastod')
                else:
                    company.skv_vaxa_api_url = (
                        'https://api.skatteverket.se/'
                        'arbetsgivare/v2/vaxastod')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    skv_vaxa_api_url = fields.Char(
        string='SKV Växa-stöd API URL',
        related='company_id.skv_vaxa_api_url',
        readonly=False,
        help="Skatteverket API endpoint for växa-stöd (growth support) "
             "reimbursement applications.")
