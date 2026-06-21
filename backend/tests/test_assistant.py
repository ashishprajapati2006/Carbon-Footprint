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


class TestAssistantSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Force MockDatabase mode for database isolation
        DatabaseManager.db = None
        cls.client = TestClient(app)
        
        # Test accounts data
        cls.test_email = "assistant_tester@ecopilot.ai"
        cls.test_password = "securePassword123"
        cls.test_name = "Assistant Tester"
        
        # Register and Login to get active session token
        cls.client.post("/api/auth/register", json={
            "email": cls.test_email,
            "password": cls.test_password,
            "full_name": cls.test_name
        })
        
        # Clear rate limits before logging in
        from core.security import auth_limiter
        auth_limiter.history.clear()
        
        login_res = cls.client.post("/api/auth/login", json={
            "email": cls.test_email,
            "password": cls.test_password
        })
        cls.token = login_res.json()["access_token"]
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

    def setUp(self):
        # Clear collections before each test to start fresh
        db = DatabaseManager.get_db()
        db["coaching_sessions"]._store.clear()
        
        # Reset auth rate limiter cache to avoid 429
        from core.security import auth_limiter
        auth_limiter.history.clear()

    def test_01_assistant_streaming_and_persistence(self):
        print("\nTesting Assistant Session Streaming and Persistence...")
        
        # 1. Create a session
        create_res = self.client.post("/api/coach/sessions", headers=self.headers)
        self.assertEqual(create_res.status_code, 200)
        session_data = create_res.json()
        session_id = session_data["_id"]
        
        self.assertIn("session_title", session_data)
        self.assertEqual(len(session_data["messages"]), 1) # Default welcome message
        
        # 2. Call streaming message endpoint
        payload = {"message": "How do I cut down electricity emissions?"}
        
        # Send streaming request in a with block
        with self.client.stream(
            "POST",
            f"/api/coach/sessions/{session_id}/message/stream",
            json=payload,
            headers=self.headers
        ) as stream_res:
            self.assertEqual(stream_res.status_code, 200)
            
            # Consume the stream
            chunks = []
            for chunk in stream_res.iter_text():
                if chunk:
                    chunks.append(chunk)
                    
            self.assertGreater(len(chunks), 0)
            
            # Verify stream has concatenated response
            full_response = "".join(chunks)
            self.assertGreater(len(full_response), 0)
            
        # 3. Verify that the assistant message is persisted in MongoDB when streaming finishes
        db = DatabaseManager.get_db()
        session = next((s for s in db["coaching_sessions"]._store if str(s["_id"]) == session_id), None)
        self.assertIsNotNone(session)
        
        # Should contain: [welcome_msg, user_msg, assistant_msg]
        self.assertEqual(len(session["messages"]), 3)
        self.assertEqual(session["messages"][1]["content"], "How do I cut down electricity emissions?")
        self.assertEqual(session["messages"][2]["content"], full_response)
        
        # 4. Get session details by ID
        detail_res = self.client.get(f"/api/coach/sessions/{session_id}", headers=self.headers)
        self.assertEqual(detail_res.status_code, 200)
        detail_data = detail_res.json()
        self.assertEqual(detail_data["_id"], session_id)
        self.assertEqual(len(detail_data["messages"]), 3)

        # 5. Delete session
        delete_res = self.client.delete(f"/api/coach/sessions/{session_id}", headers=self.headers)
        self.assertEqual(delete_res.status_code, 200)
        
        # Verify it has been deleted
        db = DatabaseManager.get_db()
        session_exists = next((s for s in db["coaching_sessions"]._store if str(s["_id"]) == session_id), None)
        self.assertIsNone(session_exists)


if __name__ == "__main__":
    unittest.main()
