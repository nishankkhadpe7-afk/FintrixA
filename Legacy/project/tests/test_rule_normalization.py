import unittest

from engine.executor import evaluate_condition
from ingestion.llm_extractor import ExtractedMetadata
from ingestion.rule_persistence import process_rule_dict


class RuleNormalizationTests(unittest.TestCase):
    def test_new_llm_rule_shape_is_normalized_for_execution(self):
        raw_rule = {
            "type": "restriction",
            "title": "Hedging requests need underlying exposure",
            "conditions": [
                {"field": "domain", "operator": "equals", "value": "forex"},
                {"field": "hedging_flag", "operator": "equals", "value": "yes"},
                {"field": "underlying_exposure_exists", "operator": "equals", "value": "no"},
            ],
            "logic": "AND",
            "action": {
                "result": "deny",
                "message": "Unsupported hedging request without underlying exposure.",
            },
            "metadata": {
                "source": "SEBI",
                "confidence": 0.91,
                "section": "Clause 4.2",
            },
        }

        canonical = process_rule_dict(raw_rule)

        self.assertEqual(canonical["type"], "restriction")
        self.assertEqual(canonical["action"], "deny")
        self.assertEqual(canonical["title"], "Hedging requests need underlying exposure")
        self.assertEqual(canonical["description"], "Unsupported hedging request without underlying exposure.")
        self.assertEqual(canonical["source_section"], "Clause 4.2")
        self.assertEqual(canonical["regulator"], "SEBI")
        self.assertEqual(len(canonical["conditions"]), 3)
        self.assertEqual(canonical["conditions"][0]["operator"], "==")

    def test_extended_operator_and_type_normalization(self):
        raw_rule = {
            "type": "requirement",
            "title": "Document must exist",
            "conditions": [
                {"field": "document_reference", "operator": "exists", "value": True},
                {"field": "compliance_note", "operator": "contains", "value": "board"},
                {"field": "threshold", "operator": "greater_than_or_equal", "value": "10"},
            ],
            "logic": "AND",
            "action": {"result": "require", "message": "Needs supporting evidence."},
            "metadata": {"source": "SEBI", "confidence": 0.88, "section": "5.1"},
        }

        canonical = process_rule_dict(raw_rule)

        self.assertEqual(canonical["type"], "obligation")
        self.assertEqual(canonical["action"], "flag")
        operators = {condition["operator"] for condition in canonical["conditions"]}
        self.assertIn("exists", operators)
        self.assertIn("contains", operators)
        self.assertIn(">=", operators)

    def test_not_in_operator_is_supported_in_executor(self):
        result = evaluate_condition(
            {"field": "regulator", "operator": "not_in", "value": ["SEBI", "RBI"]},
            {"regulator": "IRDAI"},
        )
        self.assertTrue(result)

    def test_extracted_metadata_confidence_tolerates_string_values(self):
        metadata = ExtractedMetadata.model_validate(
            {
                "source": "SEBI",
                "confidence": "Regulation 29(2)/29(3)",
                "section": "Reg 29",
            }
        )
        self.assertEqual(metadata.confidence, 29.0)


if __name__ == "__main__":
    unittest.main()
