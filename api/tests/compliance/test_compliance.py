import unittest

from agents.compliance import check_compliance


class ComplianceTests(unittest.TestCase):
    def test_seeded_guaranteed_protection_fails_high_with_claim_001(self) -> None:
        result = check_compliance("Guaranteed protection", "jade", "linkedin")

        self.assertEqual(result.result, "FAIL")
        self.assertEqual(result.risk, "HIGH")
        self.assertEqual(result.rules, ["CLAIM_001"])
        self.assertEqual(result.issues[0].text, "Guaranteed")
        self.assertEqual(result.issues[0].rule_id, "CLAIM_001")
        self.assertIsNotNone(result.suggested_revision)
        self.assertNotIn("guaranteed", result.suggested_revision.lower())

    def test_matching_is_case_insensitive_for_all_hard_phrases(self) -> None:
        cases = {
            "100% COVERED": "CLAIM_002",
            "Zero Risk": "CLAIM_003",
            "ALWAYS COVERED": "CLAIM_004",
            "Claim Guaranteed": "CLAIM_005",
        }

        for text, rule_id in cases.items():
            with self.subTest(text=text):
                result = check_compliance(text, "jaguar", "instagram")
                self.assertEqual(result.result, "FAIL")
                self.assertEqual(result.risk, "HIGH")
                self.assertEqual(result.rules, [rule_id])

    def test_multiple_violations_have_multiple_unique_rules(self) -> None:
        result = check_compliance(
            "Guaranteed coverage is 100% covered, zero risk, always covered, and claim guaranteed.",
            "doctorshield",
            "linkedin",
        )

        self.assertEqual(
            result.rules,
            ["CLAIM_001", "CLAIM_002", "CLAIM_003", "CLAIM_004", "CLAIM_005"],
        )
        self.assertEqual(len(result.issues), 5)
        self.assertEqual(len(result.rules), len(set(result.rules)))
        self.assertNotIn("guaranteed", result.suggested_revision.lower())
        self.assertNotIn("100% covered", result.suggested_revision.lower())
        self.assertNotIn("zero risk", result.suggested_revision.lower())
        self.assertNotIn("always covered", result.suggested_revision.lower())
        self.assertNotIn("claim guaranteed", result.suggested_revision.lower())

    def test_overlapping_claim_phrase_does_not_duplicate_generic_rule(self) -> None:
        result = check_compliance("Claim guaranteed", "jade", "linkedin")

        self.assertEqual(result.rules, ["CLAIM_005"])
        self.assertEqual([issue.rule_id for issue in result.issues], ["CLAIM_005"])

    def test_repeated_same_rule_is_reported_once(self) -> None:
        result = check_compliance(
            "Guaranteed protection and guaranteed outcomes need qualification.",
            "jade",
            "linkedin",
        )

        self.assertEqual(result.rules, ["CLAIM_001"])
        self.assertEqual(len(result.issues), 1)

    def test_clean_copy_passes_low_without_issues_or_revision(self) -> None:
        result = check_compliance(
            "Protection is designed around clear policy terms and practical controls.",
            "jade",
            "linkedin",
        )

        self.assertEqual(result.result, "PASS")
        self.assertEqual(result.risk, "LOW")
        self.assertEqual(result.rules, [])
        self.assertEqual(result.issues, [])
        self.assertIsNone(result.suggested_revision)


if __name__ == "__main__":
    unittest.main()
