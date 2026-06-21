import json
import logging
import re
from datetime import datetime
from typing import Any
from bson import ObjectId

from ai.gemini_ai import GeminiAIService
from .carbon_calc import CarbonCalculatorService

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
            # Determine mock values based on keywords in OCR text
            kwh = 380.0
            cost = 58.50
            unit = "kWh"
            period = "2026-05"
            
            if "gas" in ocr_text.lower() or "therm" in ocr_text.lower():
                kwh = 45.0
                cost = 72.00
                unit = "therms"
            elif "water" in ocr_text.lower() or "gallon" in ocr_text.lower():
                kwh = 3500.0
                cost = 45.00
                unit = "gallons"
                
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

        prompt = f"""
        You are the EcoPilot AI Bill Auditor. Analyze the transcribed utility bill text below:
        \"\"\"
        {ocr_text}
        \"\"\"

        Extract the following metrics:
        1. Billing Period: The month and year of the bill (formatted strictly as 'YYYY-MM', e.g. '2026-05').
        2. Consumption Value: The quantity of resource consumed (float).
        3. Consumption Unit: The unit of measurement (standard choices: 'kWh' for electricity, 'therms' for gas, 'gallons' or 'liters' or 'ccf' for water, or default to 'kWh' if unclear).
        4. Total Cost: The total bill cost/charges (float, e.g. 64.50).
        5. Savings Opportunities: A list of 3 specific, highly tailored energy/water-saving recommendations based on the resource consumed and usage volume.

        You MUST respond with a JSON object following this exact schema:
        {{
            "billing_period": "YYYY-MM",
            "consumption_value": float,
            "consumption_unit": "kWh" | "therms" | "gallons" | "liters" | "ccf",
            "total_cost": float,
            "savings_opportunities": ["recommindation 1", "recommindation 2", "recommendation 3"]
        }}
        """

        try:
            from google import genai  # type: ignore
            from google.genai import types as gtypes  # type: ignore

            config = gtypes.GenerateContentConfig(
                response_mime_type="application/json",
                system_instruction=(
                    "You are EcoPilot, a highly skilled AI carbon and billing auditor. "
                    "Parse unstructured text transcripts to retrieve utility metrics. "
                    "Respond only with valid JSON – no markdown fences."
                ),
            )
            client = genai.Client(api_key=self.gemini.api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[gtypes.Content(role="user", parts=[gtypes.Part(text=prompt)])],
                config=config,
            )
            parsed = self._extract_json(response.text)

            # Apply defaults if values are missing
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
        except Exception as e:
            logger.error(f"Gemini bill text analysis failed: {e}")
            err_str = str(e).lower()
            if any(k in err_str for k in ("429", "quota", "resource_exhausted", "rate")):
                logger.warning("Rate-limited – returning mock bill analysis.")
                return {
                    "billing_period": datetime.now().strftime("%Y-%m"),
                    "consumption_value": 350.0,
                    "consumption_unit": "kWh",
                    "total_cost": 55.0,
                    "savings_opportunities": [
                        "Inspect appliances for continuous base loads.",
                        "Swap old lighting with LEDs.",
                        "Optimize heating and cooling settings.",
                    ],
                }
            raise RuntimeError(f"Failed to analyze bill text: {e}")

    async def analyze_bill_multimodal(self, file_bytes: bytes, mime_type: str) -> dict:
        """Directly parses utility metrics from bill image/PDF bytes using Gemini Multimodal vision."""
        if self.gemini.is_mock:
            logger.info("Gemini in mock mode. Returning mock bill analysis.")
            return await self.analyze_bill_text("")

        prompt = """
        You are the EcoPilot AI Bill Auditor. Analyze the uploaded utility bill document.
        
        Extract the following metrics:
        1. Billing Period: The month and year of the bill (formatted strictly as 'YYYY-MM', e.g. '2025-05'). Look at the billing period dates or statement date.
        2. Consumption Value: The quantity of resource consumed (float). For electricity, this is the units consumed (kWh).
        3. Consumption Unit: The unit of measurement (standard choices: 'kWh' for electricity, 'therms' for gas, 'gallons' or 'liters' or 'ccf' for water, or default to 'kWh' if unclear).
        4. Total Cost: The total bill cost / amount due (float).
        5. Savings Opportunities: A list of 3 specific, highly tailored energy/water-saving recommendations based on the resource consumed and usage volume.

        Respond with a JSON object matching this schema – no markdown fences:
        {
            "billing_period": "YYYY-MM",
            "consumption_value": float,
            "consumption_unit": "kWh" | "therms" | "gallons" | "liters" | "ccf",
            "total_cost": float,
            "savings_opportunities": ["recommendation 1", "recommendation 2", "recommendation 3"]
        }
        """
        try:
            from google import genai  # type: ignore
            from google.genai import types as gtypes  # type: ignore

            image_part = gtypes.Part.from_bytes(data=file_bytes, mime_type=mime_type)
            config = gtypes.GenerateContentConfig(
                response_mime_type="application/json",
                system_instruction="You are EcoPilot, a highly skilled AI carbon and billing auditor. Respond only with valid JSON.",
            )
            client = genai.Client(api_key=self.gemini.api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[gtypes.Content(role="user", parts=[image_part, gtypes.Part(text=prompt)])],
                config=config,
            )
            parsed = self._extract_json(response.text)
            
            # Apply defaults if values are missing
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
        except Exception as e:
            logger.error(f"Multimodal bill analysis failed: {e}")
            err_str = str(e).lower()
            if any(k in err_str for k in ("429", "quota", "resource_exhausted", "rate")):
                logger.warning("Rate-limited – returning mock bill analysis.")
                return await self.analyze_bill_text("")
            raise RuntimeError(f"Failed to analyze bill image: {e}")

    def calculate_carbon_footprint(self, value: float, unit: str) -> float:
        """Calculates carbon footprint equivalents in kg CO2 based on unit factors."""
        u_lower = unit.lower()
        if u_lower == "kwh":
            # Use standard CarbonCalculatorService for energy
            return round(CarbonCalculatorService.calculate_energy(value), 2)
        elif u_lower == "therms":
            # Natural gas factor: ~5.3 kg CO2 per therm
            return round(value * 5.3, 2)
        elif u_lower in ["gallons", "gallon"]:
            # Water treatment/pumping footprint factor: ~0.003 kg CO2 per gallon
            return round(value * 0.003, 2)
        elif u_lower in ["liters", "liter"]:
            # Water factor in liters: ~0.0008 kg CO2 per liter
            return round(value * 0.0008, 2)
        elif u_lower == "ccf":
            # CCF water metric: ~5.5 kg CO2 per CCF
            return round(value * 5.5, 2)
        else:
            # Fallback factor
            return round(value * 0.4, 2)

    async def calculate_trend(self, user_id: str, current_period: str, current_value: float, current_cost: float, current_unit: str, db: Any) -> dict:
        """
        Queries MongoDB bill_analyses to find the previous bill of the same unit
        and computes the percentage usage difference.
        """
        try:
            # Query past bill analyses for the active user
            cursor = db["bill_analyses"].find({
                "user_id": ObjectId(user_id),
                "consumption_unit": current_unit
            })
            history = await cursor.to_list(length=20)
            
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
                
            # Sort manually descending by billing period
            history.sort(key=lambda x: x.get("billing_period", ""), reverse=True)
            prev_bill = history[0]
            
            prev_val = float(prev_bill.get("consumption_value", 0.0))
            prev_cost = float(prev_bill.get("total_cost", 0.0))
            
            if prev_val > 0:
                pct_change = ((current_value - prev_val) / prev_val) * 100
            else:
                pct_change = 0.0
                
            direction = "increase" if pct_change >= 0 else "decrease"
            
            return {
                "percentage_change": round(abs(pct_change), 2),
                "direction": direction,
                "compared_to_period": prev_bill.get("billing_period", "previous"),
                "previous_value": prev_val,
                "previous_cost": prev_cost
            }
        except Exception as e:
            logger.error(f"Error calculating bill trends: {e}")
            return {
                "percentage_change": 0.0,
                "direction": "stable",
                "compared_to_period": "error",
                "previous_value": 0.0,
                "previous_cost": 0.0
            }
