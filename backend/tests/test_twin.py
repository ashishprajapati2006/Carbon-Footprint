import sys
import os
import unittest

# Clean sys.path to prevent collision
sys.path = [p for p in sys.path if "ml_project" not in p.lower()]

# Add backend directory to python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# Force testing environment
os.environ["MONGODB_URI"] = "dummy"

from fastapi.testclient import TestClient
from main import app
from core.database import DatabaseManager


class TestCarbonTwinSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Force MockDatabase mode for testing isolation
        DatabaseManager.db = None
        cls.client = TestClient(app)
        
        # Clear rate limiter cache
        from core.security import auth_limiter
        auth_limiter.history.clear()
        
        # Test accounts data
        cls.test_email = "twin_tester@ecopilot.ai"
        cls.test_password = "securePassword123"
        cls.test_name = "Twin Tester"
        
        # Register and Login to get active token
        cls.client.post("/api/auth/register", json={
            "email": cls.test_email,
            "password": cls.test_password,
            "full_name": cls.test_name
        })
        
        login_res = cls.client.post("/api/auth/login", json={
            "email": cls.test_email,
            "password": cls.test_password
        })
        cls.token = login_res.json()["access_token"]
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

    def test_01_simulate_baseline(self):
        print("\nTesting Carbon Twin Simulation (Baseline Toggles)...")
        payload = {
            "buy_ev": False,
            "install_solar": False,
            "stop_flying": False,
            "reduce_ac": False
        }
        
        response = self.client.post(
            "/api/twin/simulate",
            json=payload,
            headers=self.headers
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Validate schema fields
        self.assertIn("id", data)
        self.assertIn("original_co2_kg", data)
        self.assertIn("projected_co2_kg", data)
        self.assertIn("reduction_kg", data)
        self.assertIn("reduction_pct", data)
        self.assertIn("savings_usd_desc", data)
        self.assertIn("lifestyle_impact", data)
        self.assertIn("top_savings_sources", data)
        self.assertIn("chart_data", data)
        
        # Assert chart data has 6 months of projections
        self.assertEqual(len(data["chart_data"]), 6)
        self.assertEqual(data["reduction_kg"], 0.0)
        self.assertEqual(data["reduction_pct"], 0.0)

    def test_02_simulate_with_adjustments(self):
        print("Testing Carbon Twin Simulation (With Active Adjustments)...")
        payload = {
            "buy_ev": True,
            "install_solar": True,
            "stop_flying": True,
            "reduce_ac": True
        }
        
        response = self.client.post(
            "/api/twin/simulate",
            json=payload,
            headers=self.headers
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Ensure emission drops and savings are computed
        self.assertGreater(data["original_co2_kg"], data["projected_co2_kg"])
        self.assertGreater(data["reduction_kg"], 0.0)
        self.assertGreater(data["reduction_pct"], 0.0)
        
        # Verify chart simulated values are lower than current values
        first_point = data["chart_data"][0]
        self.assertGreater(first_point["current"], first_point["simulated"])
        
        # Verify stored simulation record in Mock DB
        db = DatabaseManager.get_db()
        sim_id = data["id"]
        stored_sim = next((s for s in db["carbon_twin_simulations"]._store if str(s["_id"]) == sim_id), None)
        self.assertIsNotNone(stored_sim)
        self.assertTrue(stored_sim["toggles"]["buy_ev"])
        self.assertTrue(stored_sim["toggles"]["install_solar"])
        self.assertEqual(stored_sim["results"]["savings_usd_desc"], data["savings_usd_desc"])


if __name__ == "__main__":
    unittest.main()
