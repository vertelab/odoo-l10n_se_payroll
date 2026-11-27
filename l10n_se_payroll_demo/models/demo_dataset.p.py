"""Payroll demo: load payslips quarter by quarter.

The data is split into one JSON file per quarter (2023Q4..2027Q4). Each
file holds the contracts, the leaves and the payslips for that quarter
only. Loading is driven by demo.dataset, which owns the sequence rule —
this module only knows how to turn a quarter's JSON into hr.payslip
records and how to take them away again.

Order inside a quarter: contracts, leaves, payslip runs, payslips. The
payslips are computed after they exist (compute_sheet needs the leaves),
then marked done (which posts the entry through OCA's payroll_account),
then paid from the bank.
"""
import gzip
import json
import logging
import os

from odoo import models

_logger = logging.getLogger(__name__)

LOADER_VERSION = 'v1-json-quarter'

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'payslips')


class DemoDataset(models.Model):
    _inherit = 'demo.dataset'

    def _load_data(self):
        """Load this quarter's payroll."""
        self.ensure_one()
        if self.source != 'payroll':
            return super()._load_data()
        self.env['hr.payslip']._payroll_demo_load_quarter(self)

    def _unload_data(self):
        """Remove this quarter's payroll."""
        self.ensure_one()
        if self.source != 'payroll':
            return super()._unload_data()
        self.env['hr.payslip']._payroll_demo_unload_quarter(self)

    def _unreconcile_data(self):
        """Withdraw the wage payments so the quarter can be matched by hand."""
        self.ensure_one()
        if self.source != 'payroll':
            return super()._unreconcile_data()
        self.env['hr.payslip']._payroll_demo_unreconcile_quarter(self)


def read_quarter(dataset):
    """Return the JSON payload for one demo.dataset row, or None."""
    path = os.path.join(DATA_DIR, f"{dataset.name.lower()}.json.gz")
    if not os.path.exists(path):
        _logger.warning('payroll_demo: no data file for %s (%s)',
                        dataset.name, path)
        return None
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        return json.load(f)
