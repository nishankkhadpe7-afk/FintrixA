import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.database import Base, engine
from backend.rules.engine import evaluate_all_rules, evaluate_for_scenario, get_trace_history
from backend.rules.routes import router as rules_router
from backend.rules.seed import seed_rules
from sqlalchemy.orm import Session
from backend.database import SessionLocal


class RulesIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        seed_rules()
        cls.app = FastAPI()
        cls.app.include_router(rules_router, prefix="/api/rules")
        cls.client = TestClient(cls.app)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()

    def setUp(self):
        self.db: Session = SessionLocal()

    def tearDown(self):
        self.db.close()

    def test_evaluate_all_rules_returns_summary_and_matches(self):
        result = evaluate_all_rules(
            db=self.db,
            input_data={
                "domain": "forex",
                "amount": 30000000,
                "declared": False,
            },
            debug=True,
            source="test",
        )

        self.assertGreater(result["total_rules"], 0)
        self.assertGreaterEqual(result["match_count"], 1)
        self.assertIn("rule_summary", result)
        self.assertEqual(result["rule_summary"]["status"], "Non-Compliant")
        self.assertTrue(result["traces"])

    def test_evaluate_for_scenario_detects_lending_rule(self):
        result = evaluate_for_scenario(
            db=self.db,
            question="A borrower defaulted on a 2 crore loan and EMI is overdue.",
            event_types=["loan_default"],
            amount=20000000,
            debug=False,
        )

        matched_ids = {item["rule_id"] for item in result["matched_rules"]}
        self.assertIn("LEND-001", matched_ids)
        self.assertIn("LEND-002", matched_ids)
        self.assertEqual(result["rule_summary"]["status"], "Non-Compliant")

    def test_trace_endpoint_returns_recent_items(self):
        self.client.post(
            "/api/rules/evaluate",
            json={
                "input_data": {
                    "domain": "general",
                    "amount": 1500000,
                    "declared": False,
                },
                "debug": True,
            },
        )

        response = self.client.get("/api/rules/trace?limit=5")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("items", payload)
        self.assertLessEqual(payload["count"], 5)

    def test_simulate_endpoint_returns_multi_input_results(self):
        response = self.client.post(
            "/api/rules/simulate",
            json={
                "inputs": [
                    {
                        "domain": "forex",
                        "amount": 30000000,
                        "declared": False,
                    },
                    {
                        "domain": "lending",
                        "amount": 500000,
                        "declared": True,
                    },
                ],
                "debug": True,
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total_inputs"], 2)
        self.assertEqual(len(payload["results"]), 2)
        self.assertIn("request_id", payload)
        self.assertIn("trace", payload["results"][0])

    def test_get_trace_history_can_filter_by_rule_id(self):
        history = get_trace_history(self.db, rule_id="FOREX-001", limit=5)
        self.assertIsInstance(history, list)


if __name__ == "__main__":
    unittest.main()
