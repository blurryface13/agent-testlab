"""No-model contract tests for the TestLab control plane."""
from __future__ import annotations

import time
import unittest

from app.testing.catalog import list_catalog
from app.testing.runner import badcases, compute_preview_hash, get_run, preview, start


class TestCatalogContracts(unittest.TestCase):
    def test_catalog_has_separated_targets_and_levels(self):
        cases = list_catalog()
        self.assertGreaterEqual(len(cases), 10)
        self.assertIn("asteria-agent", {case["target"] for case in cases})
        self.assertIn("performance", {case["level"] for case in cases})
        for case in cases:
            self.assertTrue(case["id"])
            self.assertTrue(case["tools"])
            self.assertTrue(case["assertions"])

    def test_preview_rejects_unknown_or_mismatched_selection(self):
        unknown = preview(target="unknown", case_ids=["U-T01"], tool="pytest", mode="mock", fault_mode="none")
        self.assertFalse(unknown["accepted"])
        mismatch = preview(target="asteria-agent", case_ids=["U-T01"], tool="pytest", mode="mock", fault_mode="none")
        self.assertFalse(mismatch["accepted"])

    def test_target_cases_keep_target_specific_tool_assets(self):
        asteria = next(item for item in list_catalog(target="asteria-agent") if item["id"] == "A-A01")
        t2i = next(item for item in list_catalog(target="t2i-safety") if item["id"] == "A-T01")
        asteria_postman = next(item for item in asteria["tool_details"] if item["id"] == "postman")
        t2i_postman = next(item for item in t2i["tool_details"] if item["id"] == "postman")
        self.assertEqual(asteria_postman["asset"], "asteria-postman")
        self.assertEqual(t2i_postman["asset"], "postman")

    def test_local_execution_is_limited_to_one_registered_contract(self):
        other_target = preview(target="asteria-agent", case_ids=["U-T01"], tool="pytest", mode="local", fault_mode="none")
        multiple_cases = preview(target="t2i-safety", case_ids=["U-T01", "U-T02"], tool="pytest", mode="local", fault_mode="none")
        allowed = preview(target="t2i-safety", case_ids=["U-T01"], tool="pytest", mode="local", fault_mode="none")
        asteria = preview(target="asteria-agent", case_ids=["U-A01"], tool="pytest", mode="local", fault_mode="none")
        requests_smoke = preview(target="asteria-agent", case_ids=["A-A01"], tool="requests", mode="local", fault_mode="none")
        self.assertFalse(other_target["accepted"])
        self.assertFalse(multiple_cases["accepted"])
        self.assertTrue(allowed["accepted"])
        self.assertTrue(asteria["accepted"])
        self.assertTrue(requests_smoke["accepted"])

    def test_preview_token_is_required_before_run(self):
        config = dict(target="t2i-safety", case_ids=["A-T02"], tool="requests", mode="mock", fault_mode="none")
        checked = preview(**config)
        self.assertTrue(checked["accepted"])
        rejected = start(**config)
        self.assertFalse(rejected["accepted"])
        accepted = start(**config, preview_hash=compute_preview_hash(checked))
        self.assertTrue(accepted["accepted"])
        run_id = accepted["run"]["id"]
        for _ in range(30):
            current = get_run(run_id)
            if current and current["status"] == "completed":
                break
            time.sleep(0.03)
        self.assertEqual(get_run(run_id)["status"], "completed")

    def test_fault_is_visible_as_badcase(self):
        config = dict(target="asteria-agent", case_ids=["E-R01", "F-R01"], tool="agent-eval", mode="mock", fault_mode="tool_error")
        checked = preview(**config)
        accepted = start(**config, preview_hash=compute_preview_hash(checked))
        self.assertTrue(accepted["accepted"])
        run_id = accepted["run"]["id"]
        for _ in range(40):
            current = get_run(run_id)
            if current and current["status"] == "completed":
                break
            time.sleep(0.03)
        failures = [item for item in badcases() if item["run_id"] == run_id]
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["failure_type"], "tool_error")


if __name__ == "__main__":
    unittest.main()
