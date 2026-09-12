"""Prevent the standalone PLAR edition from silently falling behind the app."""
import unittest
from plar.prepare_runner import ROOT, runner_source


class PlarSourceTests(unittest.TestCase):
    def test_runner_matches_current_source_and_icon(self):
        self.assertEqual(
            (ROOT / "plar/runner_screen_spotlight.py").read_text(encoding="utf-8"),
            runner_source(),
            "Run py plar/prepare_runner.py after changing the app or icon.",
        )
