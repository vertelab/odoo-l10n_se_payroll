# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2024- Vertel AB (<https://vertel.se>).
#
##############################################################################

from odoo import fields, models


class ResCompany(models.Model):
    """Extend res.company with API configuration for arbetsgivarintyg.nu."""
    _inherit = 'res.company'

    arbetsgivarintyg_api_nyckel = fields.Char(
        string='API-nyckel',
        help='Företagets unika API-nyckel från arbetsgivarintyg.nu '
             '(hämtas under "Redigera företag" på portalen).',
        groups='payroll.group_payroll_manager',
    )
    arbetsgivarintyg_arbetsgivar_id = fields.Char(
        string='Arbetsgivar-ID',
        help='Företagets unika Arbetsgivar-ID från arbetsgivarintyg.nu '
             '(hämtas under "Redigera företag" på portalen).',
        groups='payroll.group_payroll_manager',
    )
    arbetsgivarintyg_test_mode = fields.Boolean(
        string='Testläge',
        help='Använd testmiljön (arbetsgivarportalentest.samorg.org) '
             'istället för produktionsmiljön.',
        groups='payroll.group_payroll_manager',
    )
    arbetsgivarintyg_api_url = fields.Char(
        string='API URL',
        compute='_compute_arbetsgivarintyg_api_url',
        help='SOAP endpoint URL baserat på test/produktionsläge.',
    )

    def _compute_arbetsgivarintyg_api_url(self):
        for company in self:
            if company.arbetsgivarintyg_test_mode:
                company.arbetsgivarintyg_api_url = (
                    'https://arbetsgivarintygtest.samorg.org'
                    '/HR_SystemService/ArbetsgivarintygService.svc'
                )
            else:
                company.arbetsgivarintyg_api_url = (
                    'https://arbetsgivarintyg.nu'
                    '/HR_SystemService/ArbetsgivarintygService.svc'
                )
