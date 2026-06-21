import sys
import os
import unittest
from datetime import datetime, timezone
from bson import ObjectId

# Add backend directory to python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# Force testing environment
os.environ["MONGODB_URI"] = "dummy"

from fastapi.testclient import TestClient
from main import app
from core.database import DatabaseManager

class TestAuditNewFeatures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Force MockDatabase mode
        DatabaseManager.db = None
        cls.client = TestClient(app)
        
        # Accounts
        cls.test_email = "audit_tester@ecopilot.ai"
        cls.test_password = "securePassword123"
        cls.test_name = "Audit Tester"
        
        # Register and Login
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
        # Reset Mock Database
        db = DatabaseManager.get_db()
        db["coaching_sessions"]._store.clear()
        db["chat_history"]._store.clear()
        db["reports"]._store.clear()
        db["carbon_predictions"]._store.clear()
        db["leaderboard"]._store.clear()
        
        from core.security import auth_limiter
        auth_limiter.history.clear()

    def test_01_chat_update_and_pagination(self):
        print("\nTesting Chat title updates and message pagination...")
        # Create a session
        create_res = self.client.post("/api/coach/sessions", headers=self.headers)
        self.assertEqual(create_res.status_code, 200)
        session_id = create_res.json()["_id"]
        
        # 1. Update session title
        update_res = self.client.put(
            f"/api/coach/sessions/{session_id}?title=New%20Eco%20Title",
            headers=self.headers
        )
        self.assertEqual(update_res.status_code, 200)
        self.assertEqual(update_res.json()["session_title"], "New Eco Title")
        
        # Verify in DB
        db = DatabaseManager.get_db()
        session = next((s for s in db["coaching_sessions"]._store if str(s["_id"]) == session_id), None)
        self.assertEqual(session["session_title"], "New Eco Title")

        # 2. Add multiple messages to test pagination
        db["chat_history"]._store.clear()
        for i in range(5):
            db["chat_history"]._store.append({
                "_id": ObjectId(),
                "session_id": DatabaseManager.get_db()["coaching_sessions"]._store[0]["_id"],
                "conversation_id": DatabaseManager.get_db()["coaching_sessions"]._store[0]["_id"],
                "user_id": DatabaseManager.get_db()["coaching_sessions"]._store[0]["user_id"],
                "timestamp": datetime.now(timezone.utc),
                "role": "user" if i % 2 == 0 else "assistant",
                "message": f"Message number {i}",
                "content": f"Message number {i}",
                "model": "gemini-2.5-flash",
                "token_usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
                "response_time": 0.25,
                "metadata": {}
            })
            
        # Get session detail with pagination limit=2, offset=1
        detail_res = self.client.get(
            f"/api/coach/sessions/{session_id}?limit=2&offset=1",
            headers=self.headers
        )
        self.assertEqual(detail_res.status_code, 200)
        messages = detail_res.json()["messages"]
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["message"], "Message number 1")
        self.assertEqual(messages[1]["message"], "Message number 2")

    def test_02_chat_search(self):
        print("\nTesting keyword search over chat history...")
        # Create coaching session
        create_res = self.client.post("/api/coach/sessions", headers=self.headers)
        session_id = create_res.json()["_id"]
        
        db = DatabaseManager.get_db()
        db["chat_history"]._store.clear()
        
        # Seed chat history messages
        messages_to_seed = [
            "I want to know about solar panels.",
            "Tell me about EVs and travel.",
            "Water bills are very expensive.",
            "Unplug standard incandescent light bulbs."
        ]
        for msg in messages_to_seed:
            db["chat_history"]._store.append({
                "_id": ObjectId(),
                "session_id": DatabaseManager.get_db()["coaching_sessions"]._store[0]["_id"],
                "conversation_id": DatabaseManager.get_db()["coaching_sessions"]._store[0]["_id"],
                "user_id": DatabaseManager.get_db()["coaching_sessions"]._store[0]["user_id"],
                "timestamp": datetime.now(timezone.utc),
                "role": "user",
                "message": msg,
                "content": msg,
                "model": "gemini-2.5-flash",
                "token_usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10},
                "response_time": 0.1,
                "metadata": {}
            })
            
        # Call search route
        search_res = self.client.get(
            "/api/coach/search?q=solar",
            headers=self.headers
        )
        self.assertEqual(search_res.status_code, 200)
        results = search_res.json()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["message"], "I want to know about solar panels.")

    def test_03_reports_flow(self):
        print("\nTesting full PDF and email sustainability report generation flow...")
        # 1. Generate Report
        gen_payload = {
            "report_type": "monthly",
            "send_email": False
        }
        gen_res = self.client.post(
            "/api/reports/generate",
            json=gen_payload,
            headers=self.headers
        )
        self.assertEqual(gen_res.status_code, 201)
        report = gen_res.json()
        self.assertEqual(report["report_type"], "monthly")
        self.assertIn("carbon_trend", report)
        self.assertIn("predictions", report)
        self.assertIn("ai_summary", report)
        report_id = report["_id"]

        # 2. List Reports
        list_res = self.client.get("/api/reports", headers=self.headers)
        self.assertEqual(list_res.status_code, 200)
        self.assertEqual(len(list_res.json()), 1)

        # 3. Read Report Details
        read_res = self.client.get(f"/api/reports/{report_id}", headers=self.headers)
        self.assertEqual(read_res.status_code, 200)
        self.assertEqual(read_res.json()["_id"], report_id)

        # 4. Download Report PDF
        pdf_res = self.client.get(f"/api/reports/{report_id}/pdf", headers=self.headers)
        self.assertEqual(pdf_res.status_code, 200)
        self.assertEqual(pdf_res.headers.get("content-type"), "application/pdf")
        self.assertGreater(len(pdf_res.content), 0)

        # 5. Delete Report
        del_res = self.client.delete(f"/api/reports/{report_id}", headers=self.headers)
        self.assertEqual(del_res.status_code, 200)
        
        # Verify deleted
        list_res_after = self.client.get("/api/reports", headers=self.headers)
        self.assertEqual(len(list_res_after.json()), 0)

    def test_04_health_check(self):
        print("\nTesting GET /health check endpoint...")
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("status", data)
        self.assertIn("database", data)
        self.assertIn("ai_service", data)
        self.assertEqual(data["status"], "healthy")

    def test_05_file_validator_security(self):
        print("\nTesting file upload validator security constraints...")
        from fastapi import UploadFile
        from io import BytesIO
        import pytest
        from utils.file_validator import validate_uploaded_file

        # Helper to create mock UploadFile
        def make_upload_file(filename: str, content_type: str, data: bytes):
            return UploadFile(
                file=BytesIO(data),
                filename=filename,
                headers={"content-type": content_type}
            )

        # 1. Test double extension
        async def run_double_ext():
            file = make_upload_file("malicious.png.exe", "image/png", b"some bytes")
            await validate_uploaded_file(file, {"png"}, {"image/png"}, 1024)
        
        with self.assertRaises(Exception) as context:
            import asyncio
            asyncio.run(run_double_ext())
        self.assertIn("Double extension", str(context.exception))

        # 2. Test executable header (MZ)
        async def run_mz():
            file = make_upload_file("safe.png", "image/png", b"MZ some malware here")
            await validate_uploaded_file(file, {"png"}, {"image/png"}, 1024)

        with self.assertRaises(Exception) as context:
            import asyncio
            asyncio.run(run_mz())
        self.assertIn("executable (PE)", str(context.exception))

        # 3. Test PDF spoofing check
        async def run_pdf_spoof():
            file = make_upload_file("statement.pdf", "application/pdf", b"Not a PDF file content")
            await validate_uploaded_file(file, {"pdf"}, {"application/pdf"}, 1024)

        with self.assertRaises(Exception) as context:
            import asyncio
            asyncio.run(run_pdf_spoof())
        self.assertIn("PDF header signature", str(context.exception))

    def test_06_chat_summarization_logic(self):
        print("\nTesting AI coaching older conversation summarization logic...")
        db = DatabaseManager.get_db()
        db["coaching_sessions"]._store.clear()
        db["chat_history"]._store.clear()

        # Create session
        create_res = self.client.post("/api/coach/sessions", headers=self.headers)
        session_id = create_res.json()["_id"]

        # Seed 14 messages (more than 10) in history (making 15 total with welcome message)
        for i in range(14):
            db["chat_history"]._store.append({
                "_id": ObjectId(),
                "session_id": ObjectId(session_id),
                "conversation_id": ObjectId(session_id),
                "user_id": ObjectId(db["coaching_sessions"]._store[0]["user_id"]),
                "timestamp": datetime.now(timezone.utc),
                "role": "user" if i % 2 == 0 else "assistant",
                "message": f"Historic message turn {i}",
                "content": f"Historic message turn {i}",
                "model": "gemini-2.5-flash",
                "token_usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10},
                "response_time": 0.1,
                "metadata": {}
            })

        # Send a message via stream to trigger summarization
        stream_res = self.client.post(
            f"/api/coach/sessions/{session_id}/message/stream",
            json={"message": "Can you summarize my energy tips?"},
            headers=self.headers
        )
        self.assertEqual(stream_res.status_code, 200)

        # Check that history_summary was generated and stored in coaching_sessions
        session_doc = db["coaching_sessions"]._store[0]
        self.assertIn("history_summary", session_doc)
        self.assertGreater(len(session_doc["history_summary"]), 0)
        self.assertEqual(session_doc["summarized_count"], 5)  # 15 total - 10 trimmed = 5 older messages summarized

if __name__ == "__main__":
    unittest.main()
