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

from fastapi.testclient import TestClient
from main import app
from core.database import DatabaseManager
from core.rate_limit import assessment_rate_limiter
from services.cache_svc import assessment_cache


class TestCoachAssessmentSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Force MockDatabase mode for testing isolation
        DatabaseManager.db = None
        cls.client = TestClient(app)
        
        # Clear rate limiter cache
        from core.security import auth_limiter
        auth_limiter.history.clear()
        
        # Test accounts data
        cls.test_email = "coach_tester@ecopilot.ai"
        cls.test_password = "securePassword123"
        cls.test_name = "Coach Tester"
        
        # Register and Login to get active session tokens
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
        # Clear rate limiters and cache before each test
        assessment_rate_limiter.user_requests.clear()
        assessment_cache.clear()

    def test_01_assess_success(self):
        print("\nTesting Coach Assessment Success...")
        payload = {
            "travel": "Commute 25km daily by petrol car",
            "food": "Vegan diet, zero meat, occasional dairy",
            "electricity": "300 kWh per month, no solar panels",
            "waste": "Throw away plastics, recycle paper and cardboard",
            "water": "15 minute daily showers, water lawn weekly"
        }
        
        response = self.client.post(
            "/api/coach/assess",
            json=payload,
            headers=self.headers
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Validate schema compliance
        self.assertIn("session_id", data)
        self.assertIn("top_emission_sources", data)
        self.assertIn("personalized_recommendations", data)
        self.assertIn("expected_savings", data)
        self.assertIn("co2_reduction", data)
        self.assertIn("difficulty_level", data)
        
        # Assert structure of recommendations
        self.assertGreater(len(data["personalized_recommendations"]), 0)
        first_rec = data["personalized_recommendations"][0]
        self.assertIn("recommendation", first_rec)
        self.assertIn("expected_savings", first_rec)
        self.assertIn("co2_reduction", first_rec)
        self.assertIn("difficulty_level", first_rec)
        
        # Verify MongoDB mock saved the session with messages
        db = DatabaseManager.get_db()
        session_id = data["session_id"]
        session = next((s for s in db["coaching_sessions"]._store if str(s["_id"]) == session_id), None)
        self.assertIsNotNone(session)
        self.assertEqual(len(session["messages"]), 2)  # User profile message + AI recommendation report message
        self.assertEqual(session["messages"][0]["role"], "user")
        self.assertEqual(session["messages"][1]["role"], "assistant")

    def test_02_assess_caching(self):
        print("Testing Assessment Caching...")
        payload = {
            "travel": "Walk everywhere, zero car travel",
            "food": "Vegetarian",
            "electricity": "100 kWh/month",
            "waste": "Zero waste, compost everything",
            "water": "Quick showers"
        }
        
        # First assessment (Cache Miss)
        res1 = self.client.post("/api/coach/assess", json=payload, headers=self.headers)
        self.assertEqual(res1.status_code, 200)
        
        # Cache should now contain the key
        import hashlib
        cache_str = f"{payload['travel']}||{payload['food']}||{payload['electricity']}||{payload['waste']}||{payload['water']}"
        cache_key = hashlib.sha256(cache_str.encode("utf-8")).hexdigest()
        self.assertIsNotNone(assessment_cache.get(cache_key))
        
        # Clear rate limiter to avoid 429
        assessment_rate_limiter.user_requests.clear()
        
        # Second assessment (Cache Hit)
        res2 = self.client.post("/api/coach/assess", json=payload, headers=self.headers)
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res1.json()["top_emission_sources"], res2.json()["top_emission_sources"])

    def test_03_assess_existing_session(self):
        print("Testing Assessment Appending to Existing Session...")
        payload1 = {
            "travel": "Commute by bus",
            "food": "Omnivore",
            "electricity": "200 kWh/month",
            "waste": "Recycle sometimes",
            "water": "Average water use"
        }
        
        # Create initial session
        res1 = self.client.post("/api/coach/assess", json=payload1, headers=self.headers)
        self.assertEqual(res1.status_code, 200)
        session_id = res1.json()["session_id"]
        
        # Clear rate limiter
        assessment_rate_limiter.user_requests.clear()
        
        # Append second assessment to the same session
        payload2 = {
            "travel": "Updated commute to cycling",
            "food": "Omnivore",
            "electricity": "200 kWh/month",
            "waste": "Recycle sometimes",
            "water": "Average water use",
            "session_id": session_id
        }
        
        res2 = self.client.post("/api/coach/assess", json=payload2, headers=self.headers)
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.json()["session_id"], session_id)
        
        # Verify messages list size in DB increased
        db = DatabaseManager.get_db()
        session = next((s for s in db["coaching_sessions"]._store if str(s["_id"]) == session_id), None)
        self.assertEqual(len(session["messages"]), 4)  # 2 messages from first assessment + 2 from second assessment

    def test_04_assess_rate_limiting(self):
        print("Testing Assessment Rate Limiting...")
        payload = {
            "travel": "Flight every week",
            "food": "Meat lover",
            "electricity": "500 kWh/month",
            "waste": "No recycling",
            "water": "Wasting water"
        }
        
        # Send 10 quick requests (limit is 5 requests per 60 seconds)
        rate_limited = False
        for i in range(10):
            res = self.client.post("/api/coach/assess", json=payload, headers=self.headers)
            if res.status_code == 429:
                rate_limited = True
                print(f"SUCCESS: Rate limit triggered on request #{i+1} (HTTP 429).")
                break
                
        self.assertTrue(rate_limited, "Rate limiter did not block assessments.")


if __name__ == "__main__":
    unittest.main()
