import json
import logging
import re
from datetime import datetime
from typing import Any, Dict
from bson import ObjectId

from ai.gemini_ai import GeminiAIService
from .carbon_calc import CarbonCalculatorService
from repositories.bill import BillRepository

logger = logging.getLogger("ecopilot.analysis")

class BillAnalysisService:
    """
    Coordinates utility statement analysis: parses text contents using Gemini,
    converts usage to carbon equivalents, and queries history to calculate trends.
    """
    def __init__(self, gemini_service: GeminiAIService):
        self.gemini = gemini_service

    def _extract_json(self, raw_text: str) -> dict:
        """Helper to extract and parse JSON from Markdown wrappers if returned by the LLM."""
        cleaned = raw_text.strip()
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL | re.IGNORECASE)
        if match:
            cleaned = match.group(1)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.error(f"Failed to decode Gemini response as JSON. Raw text: {raw_text}")
            return {}

    async def analyze_bill_text(self, ocr_text: str) -> dict:
        """Sends extracted text to Gemini to parse utility metrics and extract savings recommendations."""
        if self.gemini.is_mock:
            logger.info("Gemini in mock mode. Returning mock bill analysis.")
            return self._get_mock_bill_analysis(ocr_text)

        try:
            parsed = await self._query_gemini_bill_text(ocr_text)
            return self._apply_default_bill_metrics(parsed)
        except Exception as e:
            logger.error(f"Gemini bill text analysis failed: {e}")
            if any(k in str(e).lower() for k in ("429", "quota", "resource_exhausted", "rate")):
                logger.warning("Rate-limited – returning mock bill analysis.")
                return self._get_mock_bill_analysis(ocr_text)
            raise RuntimeError(f"Failed to analyze bill text: {e}")

    def _get_mock_bill_analysis(self, ocr_text: str) -> dict:
        """Generates dummy metrics when Gemini is disabled/offline."""
        kwh = 380.0
        cost = 58.50
        unit = "kWh"
        period = datetime.now().strftime("%Y-%m")
        
        if "gas" in ocr_text.lower() or "therm" in ocr_text.lower():
            kwh, cost, unit = 45.0, 72.00, "therms"
        elif "water" in ocr_text.lower() or "gallon" in ocr_text.lower():
            kwh, cost, unit = 3500.0, 45.00, "gallons"
            
        return {
            "billing_period": period,
            "consumption_value": kwh,
            "consumption_unit": unit,
            "total_cost": cost,
            "savings_opportunities": [
                "Swap standard light bulbs for high-efficiency LEDs to reduce usage.",
                "Unplug phantom power draws (like idle TVs, gaming systems) when not in use.",
                "Shift high-draw utility work (laundry, dishwashing) to off-peak utility hours."
            ]
        }

    async def _query_gemini_bill_text(self, ocr_text: str) -> dict:
        """Sends the raw text to the Gemini Client API for JSON extraction."""
        from google import genai  # type: ignore
        from google.genai import types as gtypes  # type: ignore

        prompt = f"""
        You are the EcoPilot AI Bill Auditor. Analyze the transcribed utility bill text below:
        \"\"\"
        {ocr_text}
        \"\"\"
        Extract the billing_period (YYYY-MM), consumption_value (float), consumption_unit, total_cost (float), and 3 savings_opportunities.
        Respond with a JSON object:
        {{
            "billing_period": "YYYY-MM",
            "consumption_value": float,
            "consumption_unit": "kWh" | "therms" | "gallons" | "liters" | "ccf",
            "total_cost": float,
            "savings_opportunities": ["rec 1", "rec 2", "rec 3"]
        }}
        """
        config = gtypes.GenerateContentConfig(
            response_mime_type="application/json",
            system_instruction="You are EcoPilot bill auditor. Respond only with valid JSON.",
        )
        client = genai.Client(api_key=self.gemini.api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[gtypes.Content(role="user", parts=[gtypes.Part(text=prompt)])],
            config=config,
        )
        return self._extract_json(response.text)

    def _apply_default_bill_metrics(self, parsed: dict) -> dict:
        """Hydrates missing keys in the JSON response with reasonable averages."""
        if not parsed.get("billing_period"):
            parsed["billing_period"] = datetime.now().strftime("%Y-%m")
        if parsed.get("consumption_value") is None:
            parsed["consumption_value"] = 350.0
        if not parsed.get("consumption_unit"):
            parsed["consumption_unit"] = "kWh"
        if parsed.get("total_cost") is None:
            parsed["total_cost"] = 55.0
        if not parsed.get("savings_opportunities"):
            parsed["savings_opportunities"] = [
                "Inspect appliances for continuous base loads.",
                "Swap old lighting with LEDs.",
                "Optimize heating and cooling settings.",
            ]
        return parsed

    async def analyze_bill_multimodal(self, file_bytes: bytes, mime_type: str) -> dict:
        """Directly parses utility metrics from bill image/PDF bytes using Gemini Multimodal vision."""
        if self.gemini.is_mock:
            logger.info("Gemini in mock mode. Returning mock bill analysis.")
            return self._get_mock_bill_analysis("")

        try:
            parsed = await self._query_gemini_bill_image(file_bytes, mime_type)
            return self._apply_default_bill_metrics(parsed)
        except Exception as e:
            logger.error(f"Multimodal bill analysis failed: {e}")
            if any(k in str(e).lower() for k in ("429", "quota", "resource_exhausted", "rate")):
                logger.warning("Rate-limited – returning mock bill analysis.")
                return self._get_mock_bill_analysis("")
            raise RuntimeError(f"Failed to analyze bill image: {e}")

    async def _query_gemini_bill_image(self, file_bytes: bytes, mime_type: str) -> dict:
        """Helper to run the multimodal request on image/PDF bytes."""
        from google import genai  # type: ignore
        from google.genai import types as gtypes  # type: ignore

        prompt = """
        You are the EcoPilot AI Bill Auditor. Analyze the uploaded utility bill document.
        Extract billing_period (YYYY-MM), consumption_value (float), consumption_unit, total_cost (float), and 3 savings_opportunities.
        Respond with a JSON object matching this schema:
        {
            "billing_period": "YYYY-MM",
            "consumption_value": float,
            "consumption_unit": "kWh" | "therms" | "gallons" | "liters" | "ccf",
            "total_cost": float,
            "savings_opportunities": ["rec 1", "rec 2", "rec 3"]
        }
        """
        image_part = gtypes.Part.from_bytes(data=file_bytes, mime_type=mime_type)
        config = gtypes.GenerateContentConfig(
            response_mime_type="application/json",
            system_instruction="You are EcoPilot bill auditor. Respond only with valid JSON.",
        )
        client = genai.Client(api_key=self.gemini.api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[gtypes.Content(role="user", parts=[image_part, gtypes.Part(text=prompt)])],
            config=config,
        )
        return self._extract_json(response.text)

    def calculate_carbon_footprint(self, value: float, unit: str) -> float:
        """Calculates carbon footprint equivalents in kg CO2 based on unit factors."""
        u_lower = unit.lower()
        if u_lower == "kwh":
            return round(CarbonCalculatorService.calculate_energy(value), 2)
        elif u_lower == "therms":
            return round(value * 5.3, 2)
        elif u_lower in ["gallons", "gallon"]:
            return round(value * 0.003, 2)
        elif u_lower in ["liters", "liter"]:
            return round(value * 0.0008, 2)
        elif u_lower == "ccf":
            return round(value * 5.5, 2)
        return round(value * 0.4, 2)

    async def calculate_trend(self, user_id: str, current_period: str, current_value: float, current_cost: float, current_unit: str, db: Any) -> dict:
        """Queries BillRepository to find the previous bill and computes differences."""
        try:
            bill_repo = BillRepository(db)
            history = await bill_repo.get_bills_by_unit(user_id, current_unit)
            
            # Exclude current billing period to avoid self-comparison
            history = [h for h in history if h.get("billing_period") != current_period]
            
            if not history:
                return {
                    "percentage_change": 0.0,
                    "direction": "stable",
                    "compared_to_period": "none",
                    "previous_value": 0.0,
                    "previous_cost": 0.0
                }
                
            return self._sort_and_compare_bills(history, current_value, current_cost)
        except Exception as e:
            logger.error(f"Error calculating bill trends: {e}")
            return {
                "percentage_change": 0.0,
                "direction": "stable",
                "compared_to_period": "error",
                "previous_value": 0.0,
                "previous_cost": 0.0
            }

    def _sort_and_compare_bills(self, history: list, current_value: float, current_cost: float) -> dict:
        """Helper to sort history and compute percentage differences."""
        history.sort(key=lambda x: x.get("billing_period", ""), reverse=True)
        prev_bill = history[0]
        
        prev_val = float(prev_bill.get("consumption_value", 0.0))
        prev_cost = float(prev_bill.get("total_cost", 0.0))
        
        pct_change = ((current_value - prev_val) / prev_val) * 100 if prev_val > 0 else 0.0
        direction = "increase" if pct_change >= 0 else "decrease"
        
        return {
            "percentage_change": round(abs(pct_change), 2),
            "direction": direction,
            "compared_to_period": prev_bill.get("billing_period", "previous"),
            "previous_value": prev_val,
            "previous_cost": prev_cost
        }
