import sys
import os
import unittest

# Clean sys.path to prevent collision with other folders containing "app.py" or "ml_project"
sys.path = [p for p in sys.path if "ml_project" not in p.lower()]

# Add backend directory to the beginning of python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# Set environment variables for testing before imports
os.environ["MONGODB_URI"] = "dummy"

from fastapi.testclient import TestClient
from main import app
from core.database import DatabaseManager
from core.security import auth_limiter


class TestAuthenticationSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Force MockDatabase mode for database isolation during testing
        DatabaseManager.db = None
        cls.client = TestClient(app)
        
        # Test accounts data
        cls.test_email = "architect@ecopilot.ai"
        cls.test_password = "securePassword123"
        cls.test_name = "Principal Architect"

    def setUp(self):
        # Clear rate limiter cache before each test to prevent 429 overlaps
        auth_limiter.history.clear()

    def test_01_registration_flow(self):
        print("\nTesting Registration...")
        # Signup
        response = self.client.post("/api/auth/register", json={
            "email": self.test_email,
            "password": self.test_password,
            "full_name": self.test_name
        })
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn("access_token", data)
        self.assertIn("refresh_token", data)
        
        # Test Duplicate registration prevention
        response_dup = self.client.post("/api/auth/register", json={
            "email": self.test_email,
            "password": "anotherPassword",
            "full_name": "Another Name"
        })
        self.assertEqual(response_dup.status_code, 400)
        self.assertIn("already registered", response_dup.json()["detail"])

    def test_02_login_flow(self):
        print("Testing Login...")
        # Valid login
        response = self.client.post("/api/auth/login", json={
            "email": self.test_email,
            "password": self.test_password
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("access_token", data)
        self.assertIn("refresh_token", data)
        self.assertEqual(data["token_type"], "bearer")

        # Invalid login
        response_invalid = self.client.post("/api/auth/login", json={
            "email": self.test_email,
            "password": "wrongPassword"
        })
        self.assertEqual(response_invalid.status_code, 401)
        self.assertIn("Invalid email or password", response_invalid.json()["detail"])

    def test_03_refresh_rotation(self):
        print("Testing Token Refresh Rotation...")
        # Get active token
        login_res = self.client.post("/api/auth/login", json={
            "email": self.test_email,
            "password": self.test_password
        })
        refresh_token = login_res.json()["refresh_token"]

        # Run Refresh
        refresh_res = self.client.post("/api/auth/refresh", json={
            "refresh_token": refresh_token
        })
        self.assertEqual(refresh_res.status_code, 200)
        data = refresh_res.json()
        self.assertIn("access_token", data)
        self.assertIn("refresh_token", data)
        
        # Try refreshing again with the invalidated old token (should fail due to rotation)
        refresh_res_old = self.client.post("/api/auth/refresh", json={
            "refresh_token": refresh_token
        })
        self.assertEqual(refresh_res_old.status_code, 401)

    def test_04_logout(self):
        print("Testing Session Logout...")
        login_res = self.client.post("/api/auth/login", json={
            "email": self.test_email,
            "password": self.test_password
        })
        refresh_token = login_res.json()["refresh_token"]

        # Logout
        logout_res = self.client.post("/api/auth/logout", json={
            "refresh_token": refresh_token
        })
        self.assertEqual(logout_res.status_code, 200)
        
        # Try refreshing with logged out token
        refresh_res = self.client.post("/api/auth/refresh", json={
            "refresh_token": refresh_token
        })
        self.assertEqual(refresh_res.status_code, 401)

    def test_05_password_reset(self):
        print("Testing Password Reset...")
        # Request reset
        request_res = self.client.post("/api/auth/password-reset/request", json={
            "email": self.test_email
        })
        self.assertEqual(request_res.status_code, 200)
        
        # Retrieve reset token from mock database
        db = DatabaseManager.get_db()
        reset_entry = db["password_resets"]._store[-1]
        reset_token = reset_entry["token"]

        # Confirm reset
        new_pwd = "newSuperSecretPassword123"
        confirm_res = self.client.post("/api/auth/password-reset/confirm", json={
            "token": reset_token,
            "new_password": new_pwd
        })
        self.assertEqual(confirm_res.status_code, 200)

        # Login with new password
        login_res = self.client.post("/api/auth/login", json={
            "email": self.test_email,
            "password": new_pwd
        })
        self.assertEqual(login_res.status_code, 200)

    def test_06_rate_limiting(self):
        print("Testing Rate Limiting...")
        # Send 10 quick login requests (rate limit is 5 per 10s)
        rate_limited_hit = False
        for _ in range(10):
            res = self.client.post("/api/auth/login", json={
                "email": self.test_email,
                "password": "somepassword"
            })
            if res.status_code == 429:
                rate_limited_hit = True
                print("SUCCESS: Rate limited correctly (HTTP 429).")
                break
        self.assertTrue(rate_limited_hit, "Rate limiter failed to trigger HTTP 429")

    @classmethod
    def tearDownClass(cls):
        auth_limiter.history.clear()


if __name__ == "__main__":
    unittest.main()
