import sys
import os
import unittest
from datetime import datetime

# Clean sys.path to prevent collision
sys.path = [p for p in sys.path if "ml_project" not in p.lower()]

# Add backend directory to python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# Force testing environment
os.environ["MONGODB_URI"] = "dummy"
os.environ["GEMINI_API_KEY"] = "dummy_api_key"

from fastapi.testclient import TestClient
from main import app
from core.database import DatabaseManager


class TestEcoVisionSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Force MockDatabase mode for database isolation
        DatabaseManager.db = None
        cls.client = TestClient(app)
        
        # Test accounts data
        cls.test_email = "vision_tester@ecopilot.ai"
        cls.test_password = "securePassword123"
        cls.test_name = "Vision Tester"
        
        # Register and Login to get active session token
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

    def setUp(self):
        # Clear collections before each test to start fresh
        db = DatabaseManager.get_db()
        db["room_analyses"]._store.clear()

    def test_01_scan_room_image_success(self):
        print("\nTesting EcoVision Room Scanner Upload & Analysis...")
        
        # Post mock JPEG image bytes to the room scanning endpoint
        response = self.client.post(
            "/api/rooms/scan",
            files={"file": ("living_room.jpg", b"\xff\xd8\xff\xe0-mock-jpeg-bytes", "image/jpeg")},
            data={"room_type": "living_room"},
            headers=self.headers
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Assert schema fields exist
        self.assertIn("_id", data)
        self.assertIn("user_id", data)
        self.assertEqual(data["room_type"], "living_room")
        self.assertIn("detected_appliances", data)
        self.assertIn("total_energy_waste_kwh", data)
        self.assertIn("total_carbon_impact_kg", data)
        self.assertIn("total_yearly_cost_usd", data)
        self.assertIn("overall_room_eco_score", data)
        self.assertIn("recommendations", data)
        self.assertIn("analyzed_at", data)
        
        # Check appliance detection metrics (mock data lists AC, Lights, Fan)
        appliances = data["detected_appliances"]
        self.assertGreater(len(appliances), 0)
        
        first_app = appliances[0]
        self.assertIn("name", first_app)
        self.assertIn("type", first_app)
        self.assertIn("energy_efficiency_estimate", first_app)
        self.assertIn("detected_issues", first_app)
        self.assertIn("eco_alternative", first_app)
        self.assertIn("energy_waste_kwh", first_app)
        self.assertIn("carbon_impact_kg", first_app)
        self.assertIn("yearly_cost_usd", first_app)
        
        # Check numerical totals consistency
        self.assertGreater(data["total_energy_waste_kwh"], 0.0)
        self.assertGreater(data["total_carbon_impact_kg"], 0.0)
        self.assertGreater(data["total_yearly_cost_usd"], 0.0)

        # Check list/history scans route returns the recorded scan
        list_res = self.client.get("/api/rooms/scans", headers=self.headers)
        self.assertEqual(list_res.status_code, 200)
        list_data = list_res.json()
        self.assertEqual(len(list_data), 1)
        self.assertEqual(list_data[0]["_id"], data["_id"])
        self.assertEqual(list_data[0]["room_type"], "living_room")


if __name__ == "__main__":
    unittest.main()
