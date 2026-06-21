import sys
import os
import unittest
import asyncio
from datetime import datetime, timezone, timedelta

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
from services.gamification_svc import GamificationService

class TestGamificationSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Force MockDatabase mode for testing isolation
        DatabaseManager.db = None
        cls.client = TestClient(app)
        
        cls.test_email = "gamer_tester@ecopilot.ai"
        cls.test_password = "securePassword123"
        cls.test_name = "Gamification Tester"
        
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

    def run_async(self, coro):
        """Helper to run async code synchronously in tests."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)

    def setUp(self):
        # Clear collections related to gamification before each test to guarantee isolation
        db = DatabaseManager.get_db()
        db["points_logs"]._store = []
        db["challenges"]._store = []
        # Reset tester user points/badges in the users mock store
        for user in db["users"]._store:
            if user.get("email") == self.test_email:
                user["points"] = 0
                user["badges"] = []

    def test_01_award_points_and_badges(self):
        print("\nTesting Points Award and Badges Unlocking...")
        # 1. Start stats check (should be 0)
        res = self.client.get("/api/gamification/stats", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["points"], 0)
        self.assertEqual(len(data["badges"]), 0)

        # 2. Trigger Footprint log (awards +10 points)
        payload = {
            "energy": {"kwh": 10},
            "date": datetime.now(timezone.utc).isoformat()
        }
        res_log = self.client.post("/api/footprint/log", json=payload, headers=self.headers)
        self.assertEqual(res_log.status_code, 201)

        # 3. Assert stats now has 10 points
        res = self.client.get("/api/gamification/stats", headers=self.headers)
        self.assertEqual(res.json()["points"], 10)
        self.assertEqual(res.json()["weekly_points"], 10)
        self.assertEqual(res.json()["monthly_points"], 10)

        # 4. Award more points manually to cross the 100 threshold for "Eco Warrior"
        db = DatabaseManager.get_db()
        user = next((u for u in db["users"]._store if u["email"] == self.test_email), None)
        self.assertIsNotNone(user)
        user_id = str(user["_id"])

        # Award manually (total 10 + 50 + 50 = 110 points)
        self.run_async(GamificationService.award_points(user_id, "bill_upload", db))
        self.run_async(GamificationService.award_points(user_id, "bill_upload", db))

        # 5. Check stats and assert "Eco Warrior" badge is unlocked
        res = self.client.get("/api/gamification/stats", headers=self.headers)
        stats = res.json()
        self.assertEqual(stats["points"], 110)
        self.assertIn("Eco Warrior", stats["badges"])
        self.assertNotIn("Green Hero", stats["badges"])

    def test_02_challenges_lifecycle(self):
        print("\nTesting Challenges Lifecycle (Get and Claim)...")
        # 1. Fetch challenges list (should initialize defaults)
        res = self.client.get("/api/gamification/challenges", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        challenges = res.json()
        self.assertEqual(len(challenges), 4)
        
        # Verify default challenges properties
        unplug_quest = next((ch for ch in challenges if ch["quest_title"] == "Standby Shutdown"), None)
        self.assertIsNotNone(unplug_quest)
        self.assertEqual(unplug_quest["status"], "completed") # goal met 5/5
        self.assertEqual(unplug_quest["xp_yield"], 60)

        # 2. Claim completed challenge
        quest_id = unplug_quest["id"]
        res_claim = self.client.post(f"/api/gamification/challenges/{quest_id}/claim", headers=self.headers)
        self.assertEqual(res_claim.status_code, 200)
        claim_data = res_claim.json()
        self.assertEqual(claim_data["awarded"], 100) # Awards +100 points
        
        # 3. Assert stats have increased by 100 points
        res_stats = self.client.get("/api/gamification/stats", headers=self.headers)
        self.assertEqual(res_stats.json()["points"], 100)

        # 4. Attempt to claim again (should fail)
        res_claim_again = self.client.post(f"/api/gamification/challenges/{quest_id}/claim", headers=self.headers)
        self.assertEqual(res_claim_again.status_code, 400)
        self.assertIn("already claimed", res_claim_again.json()["detail"].lower())

    def test_03_leaderboard_sorting(self):
        print("\nTesting Leaderboard Aggregations and Standings...")
        db = DatabaseManager.get_db()
        
        # Create some other users and award points using run_async
        u1_res = self.run_async(db["users"].insert_one({
            "email": "user1@ecopilot.ai",
            "full_name": "User One",
            "points": 500,
            "badges": ["Eco Warrior", "Green Hero"]
        }))
        u2_res = self.run_async(db["users"].insert_one({
            "email": "user2@ecopilot.ai",
            "full_name": "User Two",
            "points": 250,
            "badges": ["Eco Warrior"]
        }))
        
        u1_id = u1_res.inserted_id
        u2_id = u2_res.inserted_id
        
        # Fetch tester user object id
        tester_user = next((u for u in db["users"]._store if u["email"] == self.test_email), None)
        tester_id = tester_user["_id"]
        
        # Insert points logs using run_async
        self.run_async(db["points_logs"].insert_one({"user_id": u1_id, "points": 50, "timestamp": datetime.now(timezone.utc)}))
        self.run_async(db["points_logs"].insert_one({"user_id": u2_id, "points": 150, "timestamp": datetime.now(timezone.utc)}))
        self.run_async(db["points_logs"].insert_one({"user_id": tester_id, "points": 20, "timestamp": datetime.now(timezone.utc)}))

        # 1. Test Global Leaderboard (sorted by user's total points)
        res_global = self.client.get("/api/gamification/leaderboard?period=global", headers=self.headers)
        self.assertEqual(res_global.status_code, 200)
        leaderboard = res_global.json()
        
        # Rank 1: User One (500 pts)
        # Rank 2: User Two (250 pts)
        # Rank 3: Gamification Tester (20 pts from logs)
        self.assertEqual(leaderboard[0]["name"], "User One")
        self.assertEqual(leaderboard[0]["points"], 500)
        self.assertEqual(leaderboard[1]["name"], "User Two")
        self.assertEqual(leaderboard[2]["name"], "Gamification Tester")
        self.assertTrue(leaderboard[2]["isMe"])

        # 2. Test Weekly Leaderboard (sorted by points logs since start of week)
        res_weekly = self.client.get("/api/gamification/leaderboard?period=weekly", headers=self.headers)
        self.assertEqual(res_weekly.status_code, 200)
        weekly = res_weekly.json()
        
        # Rank 1: User Two (150 pts)
        # Rank 2: User One (50 pts)
        # Rank 3: Gamification Tester (20 pts)
        self.assertEqual(weekly[0]["name"], "User Two")
        self.assertEqual(weekly[0]["points"], 150)
        self.assertEqual(weekly[1]["name"], "User One")
        self.assertEqual(weekly[2]["name"], "Gamification Tester")
        
        # Clean up database mock users for other tests
        db["users"]._store = [u for u in db["users"]._store if u["email"] == self.test_email]

if __name__ == "__main__":
    unittest.main()
