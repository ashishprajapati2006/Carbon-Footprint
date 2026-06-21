import sys
import os
import unittest
from unittest.mock import patch
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
from ocr.ocr_svc import OCRService
from services.analysis_svc import BillAnalysisService
from ai.gemini_ai import GeminiAIService


class TestBillAnalyzerSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Force MockDatabase mode for database isolation
        DatabaseManager.db = None
        cls.client = TestClient(app)
        
        # Clear rate limiter cache
        from core.security import auth_limiter
        auth_limiter.history.clear()
        
        # Test accounts data
        cls.test_email = "bill_tester@ecopilot.ai"
        cls.test_password = "securePassword123"
        cls.test_name = "Bill Tester"
        
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
        db["bill_analyses"]._store.clear()
        db["footprint_logs"]._store.clear()

    @patch.object(OCRService, 'perform_ocr')
    @patch.object(BillAnalysisService, 'analyze_bill_text')
    def test_01_upload_bill_success_and_trend(self, mock_analyze, mock_ocr):
        print("\nTesting AI Bill Upload OCR and Analysis Success...")
        
        # Configure Mocks
        mock_ocr.return_value = "ELECTRICITY BILL TRANSCRIPT: Period May 2026. Consumed 400 kWh. Cost $60.00."
        mock_analyze.return_value = {
            "billing_period": "2026-05",
            "consumption_value": 400.0,
            "consumption_unit": "kWh",
            "total_cost": 60.00,
            "savings_opportunities": ["Opportunity 1", "Opportunity 2", "Opportunity 3"]
        }
        
        # 1. First upload (creates baseline, trend should be stable/none)
        response1 = self.client.post(
            "/api/bills/upload",
            files={"file": ("bill1.pdf", b"%PDF-dummy-bytes", "application/pdf")},
            headers=self.headers
        )
        self.assertEqual(response1.status_code, 200)
        data1 = response1.json()
        
        self.assertEqual(data1["billing_period"], "2026-05")
        self.assertEqual(data1["consumption_value"], 400.0)
        self.assertEqual(data1["consumption_unit"], "kWh")
        self.assertEqual(data1["total_cost"], 60.0)
        self.assertGreater(data1["carbon_footprint_kg"], 0.0)
        self.assertEqual(data1["trend"]["compared_to_period"], "none") # Baseline
        
        # Verify MongoDB storage
        db = DatabaseManager.get_db()
        self.assertEqual(len(db["bill_analyses"]._store), 1)
        self.assertEqual(len(db["footprint_logs"]._store), 1)
        self.assertEqual(db["footprint_logs"]._store[0]["categories"]["energy"]["usage"], 400.0)

        # 2. Second upload (increases usage, trend should calculate increase percentage)
        mock_ocr.return_value = "ELECTRICITY BILL TRANSCRIPT: Period June 2026. Consumed 440 kWh. Cost $66.00."
        mock_analyze.return_value = {
            "billing_period": "2026-06",
            "consumption_value": 440.0,
            "consumption_unit": "kWh",
            "total_cost": 66.00,
            "savings_opportunities": ["Opportunity A", "Opportunity B"]
        }
        
        response2 = self.client.post(
            "/api/bills/upload",
            files={"file": ("bill2.pdf", b"%PDF-dummy-bytes", "application/pdf")},
            headers=self.headers
        )
        self.assertEqual(response2.status_code, 200)
        data2 = response2.json()
        
        # Verify trend outputs (400 -> 440 = +10.0% increase compared to 2026-05)
        self.assertEqual(data2["trend"]["percentage_change"], 10.0)
        self.assertEqual(data2["trend"]["direction"], "increase")
        self.assertEqual(data2["trend"]["compared_to_period"], "2026-05")
        
        # Verify lists route returns both records sorted descending
        list_res = self.client.get("/api/bills", headers=self.headers)
        self.assertEqual(list_res.status_code, 200)
        list_data = list_res.json()
        self.assertEqual(len(list_data), 2)
        self.assertEqual(list_data[0]["billing_period"], "2026-06")
        self.assertEqual(list_data[1]["billing_period"], "2026-05")

    def test_02_invalid_file_extension(self):
        print("Testing Invalid Extension Validation...")
        response = self.client.post(
            "/api/bills/upload",
            files={"file": ("bill.txt", b"random txt bytes", "text/plain")},
            headers=self.headers
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unsupported file format", response.json()["detail"])

    @patch.object(GeminiAIService, '__init__', lambda self: setattr(self, 'is_mock', False) or setattr(self, 'api_key', 'some_dummy_api_key_long_enough'))
    @patch.object(BillAnalysisService, 'analyze_bill_multimodal')
    @patch.object(OCRService, 'perform_ocr')
    @patch.object(BillAnalysisService, 'analyze_bill_text')
    def test_03_upload_bill_multimodal_success(self, mock_analyze_text, mock_ocr, mock_multimodal):
        print("\nTesting AI Bill Upload Multimodal Success (No OCR fallback)...")
        
        # Configure multimodal mock to return valid parsed data
        mock_multimodal.return_value = {
            "billing_period": "2026-07",
            "consumption_value": 500.0,
            "consumption_unit": "kWh",
            "total_cost": 75.00,
            "savings_opportunities": ["Save A", "Save B", "Save C"]
        }
        
        response = self.client.post(
            "/api/bills/upload",
            files={"file": ("bill3.pdf", b"%PDF-dummy-bytes", "application/pdf")},
            headers=self.headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["billing_period"], "2026-07")
        self.assertEqual(data["consumption_value"], 500.0)
        self.assertEqual(data["consumption_unit"], "kWh")
        self.assertEqual(data["total_cost"], 75.0)
        
        # Verify direct multimodal analysis was called once
        mock_multimodal.assert_called_once()
        # Verify OCR and analyze_bill_text were NEVER called since multimodal succeeded
        mock_ocr.assert_not_called()
        mock_analyze_text.assert_not_called()

    @patch.object(GeminiAIService, '__init__', lambda self: setattr(self, 'is_mock', False) or setattr(self, 'api_key', 'some_dummy_api_key_long_enough'))
    @patch.object(BillAnalysisService, 'analyze_bill_multimodal')
    @patch.object(OCRService, 'perform_ocr')
    @patch.object(BillAnalysisService, 'analyze_bill_text')
    def test_04_upload_bill_multimodal_fallback(self, mock_analyze_text, mock_ocr, mock_multimodal):
        print("\nTesting AI Bill Upload Multimodal Failure Fallback to OCR...")
        
        # Multimodal analysis raises an exception
        mock_multimodal.side_effect = Exception("Vision API rate limit or error")
        
        # Configure fallback OCR and text analysis mocks
        mock_ocr.return_value = "ELECTRICITY BILL TRANSCRIPT: Period July 2026. Consumed 500 kWh. Cost $75.00."
        mock_analyze_text.return_value = {
            "billing_period": "2026-07",
            "consumption_value": 500.0,
            "consumption_unit": "kWh",
            "total_cost": 75.00,
            "savings_opportunities": ["Save A", "Save B", "Save C"]
        }
        
        response = self.client.post(
            "/api/bills/upload",
            files={"file": ("bill4.pdf", b"%PDF-dummy-bytes", "application/pdf")},
            headers=self.headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["billing_period"], "2026-07")
        self.assertEqual(data["consumption_value"], 500.0)
        self.assertEqual(data["consumption_unit"], "kWh")
        
        # Verify multimodal analysis was attempted
        mock_multimodal.assert_called_once()
        # Verify fallback OCR and text analysis were both called
        mock_ocr.assert_called_once()
        mock_analyze_text.assert_called_once()


if __name__ == "__main__":
    unittest.main()

