import unittest
from pathlib import Path
from unittest.mock import patch

from ingestion.manual_document_ingestion import MANUAL_DOCS_ROOT, ingest_local_document


class ManualDocumentIngestionTests(unittest.TestCase):
    @patch("ingestion.manual_document_ingestion.persist_extracted_rules")
    @patch("ingestion.manual_document_ingestion.extract_rules_from_content")
    @patch("ingestion.manual_document_ingestion.store_raw_document")
    @patch("ingestion.manual_document_ingestion._record_processing")
    @patch("ingestion.manual_document_ingestion.is_llm_processed")
    @patch("ingestion.manual_document_ingestion.init_schema")
    def test_force_bypasses_processed_skip(
        self,
        mock_init_schema,
        mock_is_processed,
        mock_record_processing,
        mock_store_raw_document,
        mock_extract_rules,
        mock_persist_rules,
    ):
        mock_is_processed.return_value = True
        mock_store_raw_document.return_value = {"id": 123, "content_hash": "abc"}
        mock_extract_rules.return_value = [
            {
                "type": "obligation",
                "action": "ALLOW",
                "conditions": [{"field": "domain", "operator": "==", "value": "sebi"}],
            }
        ]
        mock_persist_rules.return_value = {"total_stored": 1, "total_skipped": 0, "rules": []}

        MANUAL_DOCS_ROOT.mkdir(parents=True, exist_ok=True)
        temp_path = MANUAL_DOCS_ROOT / "test_force_ingest_sample.txt"
        temp_path.write_text("sample sebi text", encoding="utf-8")

        try:
            result = ingest_local_document(
                file_path=str(temp_path),
                title="Sample SEBI Document",
                source="SEBI",
                official_url="https://www.sebi.gov.in/legal/circulars/sample_123.html",
                force=True,
            )
        finally:
            temp_path.unlink(missing_ok=True)

        self.assertEqual(result["status"], "success")
        self.assertTrue(result["forced"])
        mock_extract_rules.assert_called_once()


if __name__ == "__main__":
    unittest.main()
