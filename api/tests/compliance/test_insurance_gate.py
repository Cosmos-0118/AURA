import unittest

from rules.insurance_compliance import InsuranceComplianceGate, check_compliance


class InsuranceComplianceGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.gate = InsuranceComplianceGate()

    def test_absolute_claim_fails_with_auditable_issue(self) -> None:
        result = self.gate.check("Guaranteed protection with 100% covered benefits")
        self.assertEqual((result.result, result.risk), ("FAIL", "HIGH"))
        self.assertEqual(result.rules, ["CLAIM_001", "CLAIM_002"])
        self.assertEqual(result.issues[0].text, "Guaranteed")
        self.assertNotIn("guaranteed", result.suggested_revision.lower())

    def test_specific_claim_rule_takes_precedence(self) -> None:
        result = self.gate.check("Claim guaranteed")
        self.assertEqual(result.rules, ["CLAIM_005"])

    def test_unsupported_breadth_requires_review(self) -> None:
        result = self.gate.check("Get comprehensive coverage")
        self.assertEqual((result.result, result.risk), ("REVIEW", "MEDIUM"))
        self.assertEqual(result.rules, ["REVIEW_001"])

    def test_fail_outweighs_review(self) -> None:
        result = self.gate.check("Instant coverage and zero risk")
        self.assertEqual((result.result, result.risk), ("FAIL", "HIGH"))
        self.assertEqual(result.rules, ["REVIEW_002", "CLAIM_003"])

    def test_repeated_rule_is_reported_once(self) -> None:
        result = self.gate.check("Guaranteed coverage, guaranteed peace of mind")
        self.assertEqual(result.rules, ["CLAIM_001"])

    def test_clean_copy_passes(self) -> None:
        result = self.gate.check("Explore plans and review the applicable policy terms.")
        self.assertEqual((result.result, result.risk), ("PASS", "LOW"))
        self.assertEqual(result.rules, [])
        self.assertIsNone(result.suggested_revision)

    def test_empty_copy_cannot_pass(self) -> None:
        result = self.gate.check(" \n ")
        self.assertEqual((result.result, result.risk), ("REVIEW", "MEDIUM"))

    def test_matches_whole_words_only(self) -> None:
        result = self.gate.check("Our coverage is not described as non-guaranteedness.")
        self.assertEqual(result.result, "PASS")

    def test_pipeline_contract_entry_point(self) -> None:
        result = check_compliance("Claim guaranteed", "doctorshield", "linkedin")
        self.assertEqual(result.rules, ["CLAIM_005"])

    def test_more_absolute_coverage_and_claim_phrases_fail(self) -> None:
        for text, rule in (
            ("100% coverage", "CLAIM_002"),
            ("All claims are approved", "CLAIM_008"),
            ("You are fully covered", "CLAIM_004"),
            ("Risk-free coverage", "CLAIM_003"),
        ):
            with self.subTest(text=text):
                result = self.gate.check(text)
                self.assertEqual(result.result, "FAIL")
                self.assertEqual(result.rules, [rule])

    def test_explicit_negation_does_not_trigger_guarantee_rule(self) -> None:
        result = self.gate.check("We do not offer guaranteed returns")
        self.assertEqual(result.result, "PASS")


if __name__ == "__main__":
    unittest.main()
