"""Final safety presentation must fail closed for withheld legacy corrections."""
import unittest

from live_demo_v2.server.app import _build_safety_checks


class FinalSafetyChecksTests(unittest.TestCase):
    def test_legacy_splice_unavailable_is_blocked_not_passed(self):
        checks = _build_safety_checks({
            "correction": {
                "status": "correction_splice_unavailable",
                "reverification": None,
                "sibling_regressions": [],
            }
        })
        self.assertTrue(checks)
        self.assertIn("BLOCK", {row["result"] for row in checks})
        self.assertNotEqual(checks[-1]["result"], "PASS")

    def test_correction_failed_without_reverification_is_blocked(self):
        checks = _build_safety_checks({
            "correction": {
                "status": "correction_failed",
                "reverification": None,
                "sibling_regressions": [],
            }
        })
        self.assertIn("BLOCK", {row["result"] for row in checks})

    def test_sibling_regression_is_blocked(self):
        checks = _build_safety_checks({
            "correction": {
                "status": "correction_sibling_regression",
                "reverification": {"verdict": "ENTAILED", "confidence": 0.99},
                "sibling_regressions": [{"claim_id": "sibling-1"}],
            }
        })
        self.assertIn("BLOCK", {row["result"] for row in checks})


if __name__ == "__main__":
    unittest.main()
