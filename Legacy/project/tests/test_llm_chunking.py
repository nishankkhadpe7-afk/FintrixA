import unittest

from ingestion.llm_extractor import _chunk_content, _post_filter_rules


class LlmChunkingTests(unittest.TestCase):
    def test_long_content_is_split_into_multiple_chunks(self):
        content = ("Paragraph one. " * 800) + "\n\n" + ("Paragraph two. " * 800)
        chunks = _chunk_content(content)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(chunk.strip() for chunk in chunks))

    def test_sebi_uses_smaller_chunks_for_same_content(self):
        content = ("Paragraph one. " * 800) + "\n\n" + ("Paragraph two. " * 800)
        rbi_chunks = _chunk_content(content, source="RBI")
        sebi_chunks = _chunk_content(content, source="SEBI")
        self.assertGreaterEqual(len(sebi_chunks), len(rbi_chunks))

    def test_post_filter_rules_removes_non_executable_sebi_items(self):
        rules = [
            {
                "title": "Definition of connected person",
                "conditions": [{"field": "domain", "operator": "equals", "value": "trading"}],
                "action": {"result": "flag", "message": "test"},
            },
            {
                "title": "Disclosure threshold for promoter transactions",
                "conditions": [{"field": "transaction_value", "operator": "greater_than", "value": 100000}],
                "action": {"result": "flag", "message": "test"},
            },
        ]
        filtered = _post_filter_rules(rules, source="SEBI")
        self.assertEqual(len(filtered), 1)
        self.assertIn("disclosure threshold", filtered[0]["title"].lower())


if __name__ == "__main__":
    unittest.main()
