import urllib.request
import json
import logging
from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import UserError
from urllib.error import HTTPError, URLError

_logger = logging.getLogger(__name__)


class PayrollTaxableWizard(models.Model):
    _name = "payroll.taxtable.wizard"
    _description = "Payroll Taxable Wizard"

    taxable_url = fields.Char(string="Taxable URL")

    def action_sync_taxable(self):
        raise UserError(
            _(f"action_sync_taxable is no longer implemented, odoo-l10n_se_payroll/l10n_se_payroll_taxtable/."))


class PayrollTaxable(models.Model):
    _name = "payroll.taxtable"
    _description = " Payroll Taxtable"

    name = fields.Char(string="Name")
    taxable_lines = fields.One2many("payroll.taxtable.line", "payroll_taxable_id", string="Taxable Lines")

    # -------------------------------------------------------------------------
    # Cron job: automatic sync of Swedish tax tables from Skatteverket API
    # -------------------------------------------------------------------------

    @api.model
    def _cron_sync_all_taxtables(self):
        """Sync tax tables for all active contract table numbers.

        Scheduled job to keep tax tables up to date. Swedish tax tables
        (skattetabeller) are published annually by Skatteverket, typically
        available in December/January for the upcoming tax year.

        The sync is idempotent — existing lines are skipped.
        """
        _logger.info("Cron: Starting sync of Swedish tax tables from Skatteverket")
        current_year = fields.Date.today().year

        contracts = self.env['hr.contract'].search([
            ('state', '=', 'open'),
            ('table_number', '!=', False),
        ])
        table_numbers = set(contracts.mapped('table_number'))

        if not table_numbers:
            _logger.info("Cron: No active contracts with table numbers — skipping")
            return

        # Sync current and next year to catch newly published tables early
        years = (current_year, current_year + 1)
        synced = 0
        failed = 0

        for year in years:
            for tn in sorted(table_numbers):
                try:
                    count = self._sync_table_number(year, tn)
                    synced += count
                    self.env.cr.commit()
                except Exception as e:
                    failed += 1
                    self.env.cr.rollback()
                    _logger.error(
                        f"Cron: Failed to sync table {tn} for year {year}: {e}",
                        exc_info=True,
                    )

        _logger.info(
            f"Cron: Tax table sync complete — {synced} new lines, "
            f"{failed} failures across {len(table_numbers)} tables "
            f"for years {years}"
        )

    @api.model
    def _sync_table_number(self, year, table_number):
        """Fetch and store all tax table lines for a given year + table number.

        Uses Skatteverket's EntryScape REST API. Existing lines are
        skipped (matched on all fields).

        Returns the number of newly created lines.
        """
        taxtable_url = (
            "https://skatteverket.entryscape.net/rowstore/dataset/"
            "88320397-5c32-4c16-ae79-d36d95b17b95"
        )
        url_offset = 0
        url_limit = 500

        taxtable_name = f"Skattetabell {year}"
        taxtable = self.search([('name', 'like', f'%{year}%')], limit=1)
        if not taxtable:
            taxtable = self.create({'name': taxtable_name})

        new_lines = 0
        next_page = True

        while next_page:
            request_url = (
                f"{taxtable_url}?tabellnr={table_number}"
                f"&%C3%A5r={year}&_limit={url_limit}&_offset={url_offset}"
            )
            response = self._taxtable_api_request(request_url)
            results = response.get("results", [])
            total = response.get("resultCount", 0)

            if not results:
                break

            to_create = []
            for item in results:
                income_from = float(item['inkomst fr.o.m.'])
                year_str = str(item['år'])
                days_str = str(item['antal dgr'])
                cols = self._normalize_tax_columns(item, income_from)

                existing = self.env['payroll.taxtable.line'].search([
                    ('year', '=', year_str),
                    ('number_of_days', '=', days_str),
                    ('table_number', '=', int(item['tabellnr'])),
                    ('income_from', '=', income_from),
                ], limit=1)

                if not existing:
                    to_create.append({
                        'year': year_str,
                        'number_of_days': days_str,
                        'table_number': int(item['tabellnr']),
                        'income_from': income_from,
                        'income_to': float(item['inkomst t.o.m.'] or 999999999),
                        'column1': cols[0],
                        'column2': cols[1],
                        'column3': cols[2],
                        'column4': cols[3],
                        'column5': cols[4],
                        'column6': cols[5],
                        'column7': cols[6],
                        'payroll_taxable_id': taxtable.id,
                    })

            if to_create:
                self.env['payroll.taxtable.line'].create(to_create)
                new_lines += len(to_create)

            url_offset += url_limit
            next_page = url_offset < total

        return new_lines

    @api.model
    def _taxtable_api_request(self, request_url):
        """Perform a GET request against the Skatteverket taxtable API.

        Centralised error handling so callers get consistent UserErrors.
        """
        try:
            response = urllib.request.urlopen(request_url, timeout=30)
            return json.loads(response.read())
        except HTTPError as e:
            raise UserError(
                _("Skatteverket API error: HTTP %(code)s for %(url)s",
                  code=e.code, url=request_url))
        except URLError as e:
            raise UserError(
                _("Skatteverket API unreachable: %(reason)s for %(url)s",
                  reason=e.reason, url=request_url))

    @api.model
    def _normalize_tax_columns(self, item, income_from):
        """Convert percentage-based tax columns to absolute currency amounts.

        Skatteverket returns percentages for high incomes (> ~60 000 kr).
        We convert those to absolute amounts for consistency.
        """
        cols = []
        for i in range(1, 8):
            key = f'kolumn {i}'
            raw = item.get(key, '')
            if raw == '' or raw is None:
                cols.append(0.0)
            else:
                val = float(raw)
                if income_from > 60000 and val < 100:
                    # Percentage → absolute amount (rounded to whole kronor)
                    val = int(income_from * val / 100)
                cols.append(float(val))
        return cols


class PayrollTaxableLine(models.Model):
    _name = "payroll.taxtable.line"
    _description = "Payroll Tax Table Line"
    _order = "year desc, table_number, income_from"

    name = fields.Char(
        string="Name",
        compute='_compute_name',
        store=True)
    year = fields.Char(
        string="Year",
        required=True,
        index=True)
    number_of_days = fields.Char(
        string="Number of Days",
        required=True,
        index=True)
    table_number = fields.Integer(
        string="Table Number",
        required=True,
        index=True)
    income_from = fields.Float(
        string="Income From",
        required=True,
        index=True)
    income_to = fields.Float(
        string="Income To",
        required=True)
    column1 = fields.Float(string="Column 1", required=True)
    column2 = fields.Float(string="Column 2", required=True)
    column3 = fields.Float(string="Column 3", required=True)
    column4 = fields.Float(string="Column 4", required=True)
    column5 = fields.Float(string="Column 5", required=True)
    column6 = fields.Float(string="Column 6", required=True)
    column7 = fields.Float(string="Column 7", required=True, default=0.0)
    payroll_taxable_id = fields.Many2one(
        'payroll.taxtable',
        string="Payroll Taxable",
        ondelete="cascade",
        required=True,
        index=True)

    @api.depends('year', 'table_number', 'number_of_days')
    def _compute_name(self):
        for line in self:
            period_label = {'1': 'dag', '7': 'vecka', '14': '14-dagar', '31': 'månad'}
            period = period_label.get(line.number_of_days, f'{line.number_of_days}d')
            line.name = f"Skattetabell {line.year} tabell {line.table_number} ({period})"
