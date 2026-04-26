import unittest

from ingestion.source_validation import is_allowed_regulator_url, validate_regulator_url


class SourceValidationTests(unittest.TestCase):
    def test_accepts_official_rbi_url(self):
        url = "https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=1234&Mode=0"
        self.assertTrue(is_allowed_regulator_url(url, source="RBI"))
        self.assertEqual(validate_regulator_url(url, source="RBI"), url)

    def test_accepts_official_sebi_url(self):
        url = "https://www.sebi.gov.in/legal/circulars/feb-2026/example_99814.html"
        self.assertTrue(is_allowed_regulator_url(url, source="SEBI"))
        self.assertEqual(validate_regulator_url(url, source="SEBI"), url)

    def test_rejects_unofficial_url(self):
        with self.assertRaises(ValueError):
            validate_regulator_url("https://example.com/fake-circular", source="SEBI")


if __name__ == "__main__":
    unittest.main()
