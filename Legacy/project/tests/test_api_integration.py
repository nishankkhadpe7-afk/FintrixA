import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.main import app


class ApiIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch("api.main.simulation_service.simulate")
    def test_direct_simulate_route_returns_service_result(self, mock_simulate):
        mock_simulate.return_value = {
            "request_id": "req-1",
            "total_inputs": 1,
            "total_matches": 1,
            "results": [
                {
                    "input": {"domain": "lending"},
                    "matched_rules": [
                        {
                            "rule_id": "rule-1",
                            "version": 1,
                            "type": "allowance",
                            "action": "ALLOW",
                            "title": "Retail Home Loan Allow Rule",
                            "description": "Matches a normal retail home-loan profile.",
                        }
                    ],
                    "match_count": 1,
                    "trace": None,
                }
            ],
        }

        response = self.client.post("/simulate", json={"inputs": [{"domain": "lending"}]})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["request_id"], "req-1")
        self.assertEqual(payload["results"][0]["matched_rules"][0]["title"], "Retail Home Loan Allow Rule")

    @patch("api.routers.sebi_ingestion.run_sebi_discovery")
    def test_sebi_discovery_route(self, mock_discovery):
        mock_discovery.return_value = {
            "status": "success",
            "total_seen": 5,
            "new_items": 2,
            "items": [
                {"id": "sebi-rss-001", "title": "Sample SEBI Circular"},
                {"id": "sebi-rss-002", "title": "Sample SEBI Regulation"},
            ],
        }

        response = self.client.post("/sebi/discover?max_entries=5")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["new_items"], 2)
        self.assertEqual(payload["items"][0]["id"], "sebi-rss-001")


if __name__ == "__main__":
    unittest.main()
