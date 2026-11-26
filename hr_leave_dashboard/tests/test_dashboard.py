# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestHrLeaveDashboard(TransactionCase):
    """Smoke test: the dashboard model loads and its main method runs.

    Kept deliberately version-agnostic so it runs on 18.0, 19.0 and 20.0.
    """

    def test_get_dashboard_data_returns_dict(self):
        dashboard = self.env['hr.leave.dashboard']
        result = dashboard.get_dashboard_data()
        self.assertIsInstance(result, dict)

    def test_model_is_registered(self):
        self.assertIn('hr.leave.dashboard', self.env)
