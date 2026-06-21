"""
GeminiAIService – powered by the google-genai SDK (google-genai>=1.0.0).

Key changes vs. the old google.generativeai SDK:
  - Client is `google.genai.Client(api_key=...)`
  - Chat history uses `google.genai.types.Content` / `Part` objects
  - `client.models.generate_content(model=..., contents=[...])`
  - Streaming: `client.models.generate_content_stream(...)`
  - Vision: pass `google.genai.types.Part.from_bytes(data=..., mime_type=...)`
  - JSON mode: `config=GenerateContentConfig(response_mime_type='application/json')`

Rate-limit behaviour: any 429 / ResourceExhausted / quota error falls back to
the built-in mock response so the app keeps working without crashing.
"""
from __future__ import annotations

import json
import logging
import asyncio
import hashlib
from typing import AsyncGenerator

from core.config import settings
from services.cache_svc import InMemoryCache

logger = logging.getLogger("ecopilot.gemini")

# Chat response cache with TTL 5 minutes (300 seconds)
chat_response_cache = InMemoryCache(default_ttl=300)

def _get_chat_cache_key(chat_history: list, new_message: str) -> str:
    """
    Generates a deterministic SHA-256 cache key for a given chat context.

    The key is derived from the last 10 messages and the new user message,
    ensuring repeated identical prompts hit the cache instead of Gemini API.

    Args:
        chat_history: List of previous conversation turns (role + content dicts).
        new_message: The latest user message string to hash into the key.

    Returns:
        A 64-character hex SHA-256 digest string.
    """
    # Trim history context to last 10 messages before caching to ensure unique key format
    trimmed = chat_history[-10:]
    history_serialized = json.dumps([{"role": m["role"], "content": m["content"]} for m in trimmed])
    key_str = f"{history_serialized}||{new_message}"
    return hashlib.sha256(key_str.encode("utf-8")).hexdigest()

# ── Model name – use the widely-available flash model ─────────────────────────
_MODEL = "gemini-2.5-flash"
_RATE_LIMIT_KEYWORDS = ("429", "quota", "resource_exhausted", "rate limit", "too many")

# Retry configuration constants
_MAX_RETRY_ATTEMPTS: int = 3
_INITIAL_BACKOFF_SECONDS: float = 0.5


def _is_rate_limit(err: Exception) -> bool:
    msg = str(err).lower()
    return any(k in msg for k in _RATE_LIMIT_KEYWORDS)


class GeminiAIService:
    """
    Integrates with Google Gemini (google-genai SDK) to generate content,
    analyse bills/images, and power the conversational AI Coach.
    Falls back to rich local mock responses on quota / key errors.
    """

    def __init__(self) -> None:
        self.api_key = settings.gemini_api_key
        self.is_mock = (
            not self.api_key
            or self.api_key == "dummy_api_key"
            or len(self.api_key) < 15
        )
        self._client = None
        if not self.is_mock:
            try:
                from google import genai  # type: ignore
                self._client = genai.Client(api_key=self.api_key)
                logger.info("Gemini API (google-genai) configured successfully.")
            except Exception as exc:
                logger.error(f"Error initialising Gemini client: {exc}. Falling back to mock mode.")
                self.is_mock = True
        else:
            logger.warning("Gemini API key is missing/dummy – operating in MOCK mode.")

    # ── Private helpers ────────────────────────────────────────────────────────

    async def _execute_with_retry(self, func, *args, **kwargs):
        """
        Executes a synchronous API call with exponential backoff retry.
        Up to _MAX_RETRY_ATTEMPTS attempts, starting at _INITIAL_BACKOFF_SECONDS.
        """
        backoff = _INITIAL_BACKOFF_SECONDS
        for attempt in range(_MAX_RETRY_ATTEMPTS):
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                if _is_rate_limit(exc):
                    raise exc
                if attempt == _MAX_RETRY_ATTEMPTS - 1:
                    raise exc
                logger.warning(
                    f"Gemini API call failed on attempt {attempt + 1}: {exc}. "
                    f"Retrying in {backoff}s..."
                )
                await asyncio.sleep(backoff)
                backoff *= 2

    def _generate_mock_reply(self, message: str) -> str:
        """Returns a keyword-matched sustainability coaching reply."""
        msg = message.lower()
        if any(w in msg for w in ("transport", "car", "travel", "commut", "bus", "train", "vehicl", "bike", "cycle")):
            return (
                "🚗➡️⚡ To slash transportation emissions, consider switching to an EV, "
                "carpooling, or using public transit. Biking or walking for trips under 3 km "
                "makes a huge difference and improves health too!"
            )
        if any(w in msg for w in ("diet", "food", "meat", "vegetar", "vegan", "grocer", "plant-based", "eat")):
            return (
                "🥗 Switching to a plant-based diet can cut food-related emissions by up to 50%. "
                "Try starting with 'Meatless Mondays' and gradually reducing dairy. "
                "Local, seasonal produce is the next big lever to pull."
            )
        if any(w in msg for w in ("bill", "elect", "power", "energ", "kwh", "solar", "light", "heat")):
            return (
                "💡 Reducing electricity draw: unplug idle appliances (phantom loads add up!), "
                "upgrade to LED lighting, install a smart thermostat, and consider rooftop solar "
                "panels which typically pay back in 5-7 years."
            )
        if any(w in msg for w in ("water", "shower", "leak", "tap", "drip", "wash")):
            return (
                "💧 Heating water accounts for ~18% of home energy use. Take shorter showers, "
                "fix leaky taps (a drip wastes 9 litres/day), and wash clothes in cold water."
            )
        if any(w in msg for w in ("waste", "recycl", "compost", "trash", "landfill", "bin")):
            return (
                "♻️ Composting organic waste and sorting recyclables can divert 60–70% of household "
                "waste from landfill. Landfill methane is 28× more potent than CO₂ over 100 years, "
                "so every bag you compost makes a real difference."
            )
        return (
            "🌱 Hi! I'm EcoPilot, your AI Sustainability Coach. I can help you analyse your "
            "carbon footprint, give tips to reduce home energy use, audit room appliances from photos, "
            "and simulate lifestyle improvements. Ask me anything about going green!"
        )

    # ── Public API ─────────────────────────────────────────────────────────────

    async def generate_history_summary(self, chat_history: list) -> str:
        """Summarizes older conversation history to conserve tokens while preserving context."""
        if not chat_history:
            return ""
        if self.is_mock:
            return "The user previously discussed general sustainability habits and carbon reduction."
        
        # Format the history to be summarized
        formatted_history = "\n".join([f"{msg['role'].upper()}: {msg.get('content') or msg.get('message') or ''}" for msg in chat_history])
        prompt = f"Summarize the following conversation history between a User and EcoPilot (sustainability coach) in a concise, dense paragraph of max 3 sentences. Focus on discussed habits, plans, and metrics:\n\n{formatted_history}"
        
        try:
            from google.genai import types as gtypes  # type: ignore
            config = gtypes.GenerateContentConfig(
                system_instruction="You are a helper that summarizes chat transcripts highly concisely.",
                temperature=0.2,
                max_output_tokens=256
            )
            response = await self._execute_with_retry(
                self._client.models.generate_content,
                model=_MODEL,
                contents=[gtypes.Content(role="user", parts=[gtypes.Part(text=prompt)])],
                config=config,
            )
            return (response.text or "").strip()
        except Exception as exc:
            logger.error(f"Error generating history summary: {exc}")
            return "The user and EcoPilot previously discussed sustainability habits."

    async def generate_chat_response(
        self, chat_history: list, new_message: str, history_summary: Optional[str] = None
    ) -> str:
        """Generates a single conversational response with caching and context window trimming."""
        # Trim history context to last 10 messages
        chat_history = chat_history[-10:]
        
        # Check cache
        cache_key = _get_chat_cache_key(chat_history, new_message)
        cached_reply = chat_response_cache.get(cache_key)
        if cached_reply:
            logger.info("Serving cached chat response.")
            return cached_reply

        if self.is_mock:
            reply = self._generate_mock_reply(new_message)
            chat_response_cache.set(cache_key, reply)
            return reply

        try:
            from google.genai import types as gtypes  # type: ignore

            system_prompt = (
                "You are EcoPilot, a highly skilled AI sustainability coach. "
                "Guide users in reducing their carbon footprint, explain energy habits, "
                "and provide concrete, actionable green lifestyle advice. "
                "Keep responses friendly, empowering, and concise."
            )
            if history_summary:
                system_prompt += f"\n\nSummary of earlier conversation:\n{history_summary}"

            contents = []
            for msg in chat_history:
                role = "user" if msg["role"] == "user" else "model"
                contents.append(gtypes.Content(role=role, parts=[gtypes.Part(text=msg["content"])]))
            contents.append(gtypes.Content(role="user", parts=[gtypes.Part(text=new_message)]))

            config = gtypes.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.7,
                max_output_tokens=1024
            )
            response = await self._execute_with_retry(
                self._client.models.generate_content,
                model=_MODEL,
                contents=contents,
                config=config,
            )
            reply = response.text or self._generate_mock_reply(new_message)
            chat_response_cache.set(cache_key, reply)
            return reply

        except Exception as exc:
            logger.error(f"Gemini chat error: {exc}")
            if _is_rate_limit(exc):
                reply = self._generate_mock_reply(new_message)
                return f"⚠️ *[Gemini quota reached – smart offline mode]*\n\n{reply}"
            return self._generate_mock_reply(new_message)

    async def generate_chat_response_stream(
        self, chat_history: list, new_message: str, history_summary: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Streams conversational responses with caching and context window trimming."""
        # Trim history context to last 10 messages
        chat_history = chat_history[-10:]
        
        # Check cache
        cache_key = _get_chat_cache_key(chat_history, new_message)
        cached_reply = chat_response_cache.get(cache_key)
        if cached_reply:
            logger.info("Serving cached streamed response.")
            # Yield cached chunks with a brief delay
            words = cached_reply.split(" ")
            for i in range(0, len(words), 2):
                yield " ".join(words[i : i + 2]) + " "
                await asyncio.sleep(0.02)
            return

        if self.is_mock:
            reply = self._generate_mock_reply(new_message)
            chat_response_cache.set(cache_key, reply)
            words = reply.split(" ")
            for i in range(0, len(words), 2):
                yield " ".join(words[i : i + 2]) + " "
                await asyncio.sleep(0.05)
            return

        try:
            from google.genai import types as gtypes  # type: ignore

            system_prompt = (
                "You are EcoPilot, a highly skilled AI sustainability assistant. "
                "Guide users in reducing their carbon footprint. "
                "Keep responses friendly and concise. "
                "Use markdown formatting for lists and key data."
            )
            if history_summary:
                system_prompt += f"\n\nSummary of earlier conversation:\n{history_summary}"

            contents = []
            for msg in chat_history:
                role = "user" if msg["role"] == "user" else "model"
                contents.append(gtypes.Content(role=role, parts=[gtypes.Part(text=msg["content"])]))
            contents.append(gtypes.Content(role="user", parts=[gtypes.Part(text=new_message)]))

            config = gtypes.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.7,
                max_output_tokens=1024
            )
            accumulated = ""
            for chunk in self._client.models.generate_content_stream(
                model=_MODEL, contents=contents, config=config
            ):
                if chunk.text:
                    accumulated += chunk.text
                    yield chunk.text
            
            chat_response_cache.set(cache_key, accumulated)

        except Exception as exc:
            logger.error(f"Gemini stream error: {exc}")
            prefix = ""
            if _is_rate_limit(exc):
                prefix = "⚠️ *[Gemini quota reached – offline mode]*\n\n"
            yield prefix
            reply = self._generate_mock_reply(new_message)
            words = reply.split(" ")
            for i in range(0, len(words), 2):
                yield " ".join(words[i : i + 2]) + " "
                await asyncio.sleep(0.04)

    async def analyze_multimodal(self, image_bytes: bytes, mime_type: str, prompt: str) -> str:
        """Sends an image to Gemini Vision and returns analysis text."""
        if self.is_mock or not image_bytes:
            if "room" in prompt.lower() or "appliance" in prompt.lower():
                return json.dumps({
                    "room_type": "living_room",
                    "detected_appliances": [
                        {
                            "name": "Standard AC Window Unit",
                            "type": "AC",
                            "energy_efficiency_estimate": "Low",
                            "detected_issues": ["Dust buildup on vents", "Continuous operation profile"],
                            "eco_alternative": "Smart inverter split-system AC",
                            "energy_waste_kwh": 350.0,
                            "carbon_impact_kg": 134.75,
                            "yearly_cost_usd": 52.50,
                        },
                        {
                            "name": "Halogen Floor Lamp",
                            "type": "Lights",
                            "energy_efficiency_estimate": "Low",
                            "detected_issues": ["Draws 150 W", "High thermal output"],
                            "eco_alternative": "12 W LED dimmable floor lamp",
                            "energy_waste_kwh": 120.0,
                            "carbon_impact_kg": 46.20,
                            "yearly_cost_usd": 18.00,
                        },
                        {
                            "name": "Old Ceiling Fan",
                            "type": "Fan",
                            "energy_efficiency_estimate": "Medium",
                            "detected_issues": ["Slight wobble increases motor load"],
                            "eco_alternative": "BLDC brushless ceiling fan",
                            "energy_waste_kwh": 60.0,
                            "carbon_impact_kg": 23.10,
                            "yearly_cost_usd": 9.00,
                        },
                    ],
                    "total_energy_waste_kwh": 530.0,
                    "total_carbon_impact_kg": 204.05,
                    "total_yearly_cost_usd": 79.50,
                    "overall_room_eco_score": 52,
                    "recommendations": [
                        "Clean AC filters to improve efficiency by 15%.",
                        "Swap halogen bulbs for LED equivalents.",
                        "Upgrade to a high-efficiency BLDC ceiling fan.",
                    ],
                })
            return json.dumps({"billing_period": "2026-05", "kwh_consumed": 420.0, "total_cost": 64.50})

        try:
            from google.genai import types as gtypes  # type: ignore

            image_part = gtypes.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            text_part = gtypes.Part(text=prompt)
            contents = [gtypes.Content(role="user", parts=[image_part, text_part])]
            response = await self._execute_with_retry(
                self._client.models.generate_content,
                model=_MODEL,
                contents=contents,
            )
            return response.text or "{}"

        except Exception as exc:
            logger.error(f"Gemini Vision error: {exc}")
            if _is_rate_limit(exc):
                logger.warning("Gemini Vision rate-limited – returning mock analysis.")
                # Recurse into mock branch
                return await self.analyze_multimodal(b"", mime_type, prompt)
            raise RuntimeError(f"Gemini Vision API failure: {exc}")

    async def analyze_sustainability(
        self, travel: str, food: str, electricity: str, waste: str, water: str
    ) -> dict:
        """Analyses user habits and returns structured sustainability recommendations."""
        if self.is_mock:
            return self._mock_sustainability(travel, electricity)

        prompt = f"""
You are an expert AI Sustainability Coach. Analyse the user's habits across five categories:
1. Travel: {travel}
2. Food: {food}
3. Electricity: {electricity}
4. Waste: {waste}
5. Water: {water}

Respond ONLY with a JSON object matching this exact schema – no markdown, no extra text:
{{
  "top_emission_sources": ["source 1", "source 2", ...],
  "personalized_recommendations": [
    {{
      "recommendation": "...",
      "expected_savings": "...",
      "co2_reduction": "X kg CO2 / month",
      "difficulty_level": "Easy" | "Medium" | "Hard"
    }}
  ],
  "expected_savings": "overall savings summary",
  "co2_reduction": "overall carbon reduction summary",
  "difficulty_level": "Easy" | "Medium" | "Hard"
}}
"""
        try:
            from google.genai import types as gtypes  # type: ignore

            config = gtypes.GenerateContentConfig(
                response_mime_type="application/json",
                system_instruction=(
                    "You are EcoPilot, a highly skilled AI sustainability coach. "
                    "Respond only with valid JSON – no markdown fences."
                ),
                temperature=0.2,
                max_output_tokens=1024
            )
            response = await self._execute_with_retry(
                self._client.models.generate_content,
                model=_MODEL,
                contents=[gtypes.Content(role="user", parts=[gtypes.Part(text=prompt)])],
                config=config,
            )
            return json.loads(response.text)

        except Exception as exc:
            logger.error(f"Gemini sustainability error: {exc}")
            if _is_rate_limit(exc):
                return self._mock_sustainability(travel, electricity)
            raise RuntimeError(f"Sustainability assessment failed: {exc}")

    def _mock_sustainability(self, travel: str, electricity: str) -> dict:
        return {
            "top_emission_sources": [
                f"Transportation (Travel: {travel[:50]})" if len(travel) > 5 else "High-commute private transportation",
                f"Home energy (Electricity: {electricity[:50]})" if len(electricity) > 5 else "Residential grid electricity",
                "Food-related supply-chain emissions",
            ],
            "personalized_recommendations": [
                {
                    "recommendation": "Switch daily travel to EV, carpooling, or public transit.",
                    "expected_savings": "$50–$120 / month on fuel",
                    "co2_reduction": "150 kg CO2 / month",
                    "difficulty_level": "Medium",
                },
                {
                    "recommendation": "Replace incandescent / halogen bulbs with LED and unplug standby devices.",
                    "expected_savings": "$8–$15 / month on electricity",
                    "co2_reduction": "25 kg CO2 / month",
                    "difficulty_level": "Easy",
                },
                {
                    "recommendation": "Adopt a low-impact vegetarian or pescatarian diet 4 days a week.",
                    "expected_savings": "$20–$45 / month on groceries",
                    "co2_reduction": "60 kg CO2 / month",
                    "difficulty_level": "Easy",
                },
                {
                    "recommendation": "Set up organic waste composting and actively sort recyclables.",
                    "expected_savings": "Reduced waste disposal fees",
                    "co2_reduction": "30 kg CO2 / month",
                    "difficulty_level": "Medium",
                },
            ],
            "expected_savings": "$78–$180 / month combined",
            "co2_reduction": "265 kg CO2 / month total potential offset",
            "difficulty_level": "Easy",
        }

    async def analyze_twin_simulation(
        self,
        original_co2: float,
        projected_co2: float,
        buy_ev: bool,
        install_solar: bool,
        stop_flying: bool,
        reduce_ac: bool,
    ) -> dict:
        """Calculates financial savings + lifestyle narrative for a carbon twin simulation."""
        if self.is_mock:
            return self._mock_twin(buy_ev, install_solar, stop_flying, reduce_ac)

        prompt = f"""
You are the EcoPilot AI Carbon Twin Simulator.
Simulation adjustments:
- EV swap: {buy_ev}
- Solar panels: {install_solar}
- Stop flying: {stop_flying}
- Reduce AC: {reduce_ac}

Carbon footprint:
- Baseline: {original_co2:.1f} kg CO2/month
- Projected: {projected_co2:.1f} kg CO2/month
- Net reduction: {original_co2 - projected_co2:.1f} kg CO2/month

Respond ONLY with valid JSON matching this schema – no markdown:
{{
  "savings_usd_desc": "monthly savings description",
  "lifestyle_impact": "brief encouraging narrative (max 3 sentences)",
  "top_savings_sources": ["source 1", "source 2", ...]
}}
"""
        try:
            from google.genai import types as gtypes  # type: ignore

            config = gtypes.GenerateContentConfig(
                response_mime_type="application/json",
                system_instruction="You are EcoPilot. Respond only with valid JSON.",
                temperature=0.2,
                max_output_tokens=1024
            )
            response = await self._execute_with_retry(
                self._client.models.generate_content,
                model=_MODEL,
                contents=[gtypes.Content(role="user", parts=[gtypes.Part(text=prompt)])],
                config=config,
            )
            return json.loads(response.text)

        except Exception as exc:
            logger.error(f"Gemini twin simulation error: {exc}")
            if _is_rate_limit(exc):
                return self._mock_twin(buy_ev, install_solar, stop_flying, reduce_ac)
            raise RuntimeError(f"Twin simulation failed: {exc}")

    def _mock_twin(
        self, buy_ev: bool, install_solar: bool, stop_flying: bool, reduce_ac: bool
    ) -> dict:
        parts, sources = [], []
        if buy_ev:
            parts.append("$75–$110/mo on gasoline")
            sources.append("EV commute swap")
        if install_solar:
            parts.append("$35–$60/mo on electricity")
            sources.append("Home solar panels")
        if stop_flying:
            parts.append("$80–$140/mo on air travel (amortised)")
            sources.append("Reduced flight frequency")
        if reduce_ac:
            parts.append("$15–$30/mo on cooling")
            sources.append("Smart climate controls")
        savings = " + ".join(parts) if parts else "Enable at least one option"
        if not sources:
            sources.append("No adjustments active yet")
        return {
            "savings_usd_desc": f"Estimated monthly savings: {savings}",
            "lifestyle_impact": (
                "These adjustments move your carbon profile significantly towards sustainability. "
                "EV and solar provide compounding long-term returns, while reducing flights "
                "cuts high-altitude warming effects that count for 2–3× ground-level CO₂."
            ),
            "top_savings_sources": sources,
        }

    async def generate_report_summary(
        self, report_type: str, trend: dict, predictions: list, achievements: dict
    ) -> str:
        """Generates an AI narrative summary of the user's weekly/monthly carbon report."""
        if self.is_mock:
            return self._mock_report_summary(report_type, trend, achievements)

        total_co2 = trend.get("total_co2_kg", 0.0)
        prev_co2 = trend.get("previous_co2_kg", 0.0)
        pct = trend.get("percentage_change", 0.0)
        direction = trend.get("direction", "stable")
        xp = achievements.get("xp_earned", 0)
        badges = achievements.get("badges_unlocked", [])

        prompt = f"""
You are EcoPilot, a personal AI sustainability coach.

User's {report_type} report stats:
- Total CO₂: {total_co2:.2f} kg
- Previous period: {prev_co2:.2f} kg
- Change: {pct:.1f}% ({direction})
- XP earned: +{xp}
- New badges: {', '.join(badges) if badges else 'None'}

Write a concise, encouraging executive summary (max 5 sentences, under 120 words).
"""
        try:
            from google.genai import types as gtypes  # type: ignore

            config = gtypes.GenerateContentConfig(
                system_instruction="You are EcoPilot. Write clear, encouraging progress summaries.",
                temperature=0.7,
                max_output_tokens=512
            )
            response = await self._execute_with_retry(
                self._client.models.generate_content,
                model=_MODEL,
                contents=[gtypes.Content(role="user", parts=[gtypes.Part(text=prompt)])],
                config=config,
            )
            return (response.text or "").strip() or self._mock_report_summary(report_type, trend, achievements)

        except Exception as exc:
            logger.error(f"Gemini report summary error: {exc}")
            return self._mock_report_summary(report_type, trend, achievements)

    def _mock_report_summary(self, report_type: str, trend: dict, achievements: dict) -> str:
        total_co2 = trend.get("total_co2_kg", 0.0)
        pct = trend.get("percentage_change", 0.0)
        direction = trend.get("direction", "stable")
        xp = achievements.get("xp_earned", 0)
        badges = achievements.get("badges_unlocked", [])
        badges_phrase = f" and unlocked: **{', '.join(badges)}**" if badges else ""
        change_phrase = (
            f"a {pct:.1f}% decrease 🎉" if direction == "down"
            else f"a {pct:.1f}% increase" if direction == "up"
            else "stable emissions"
        )
        return (
            f"Great work on your **{report_type.capitalize()} Sustainability Report**! "
            f"Your carbon footprint was **{total_co2:.2f} kg CO₂**, showing {change_phrase} "
            f"vs. the previous period. You earned **+{xp} XP**{badges_phrase}. "
            "Keep optimising your home cooling and choosing public transport to push your score higher!"
        )
