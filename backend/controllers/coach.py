"""
AI Coach Controller — Gemini-Powered Carbon Reduction Coaching.

Orchestrates the conversational AI coaching experience for EcoPilot:
  - Creates and manages user coaching sessions stored in MongoDB
  - Streams AI responses from Google Gemini 2.5 Flash with SSE
  - Maintains conversation context with automatic summarization after 10 turns
  - Caches sustainability assessment responses to minimize token usage
  - Provides keyword-based chat history search across all sessions

The coach guides users toward actionable carbon reduction strategies aligned
with their personal footprint data (energy, transport, diet, waste habits).
Directly supports UN SDG 13 — Climate Action through personalized AI guidance.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, List
from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse
from bson import ObjectId

from ai.gemini_ai import GeminiAIService
from services.cache_svc import assessment_cache
from repositories.coach import CoachRepository
from schemas.coach import SustainabilityAssessmentRequest, SustainabilityAssessmentResponse, ChatMessageRequest

logger = logging.getLogger("ecopilot.coach")


class CoachController:
    @staticmethod
    async def _get_habits_assessment(log_data: SustainabilityAssessmentRequest) -> tuple[dict, int, int, float]:
        """Looks up habits assessment in cache, or queries Gemini, returning assessment payload and token metrics."""
        cache_str = f"{log_data.travel}||{log_data.food}||{log_data.electricity}||{log_data.waste}||{log_data.water}"
        cache_key = hashlib.sha256(cache_str.encode("utf-8")).hexdigest()
        
        start_time = time.perf_counter()
        cached_result = assessment_cache.get(cache_key)
        if cached_result:
            logger.info("Serving cached habits assessment.")
            return cached_result, 0, 0, time.perf_counter() - start_time
            
        from repositories.cache import CacheRepository
        cache_repo = CacheRepository()
        try:
            cached_db = await cache_repo.get_cache(cache_key)
            if cached_db:
                logger.info("Serving MongoDB cached habits assessment.")
                if isinstance(cached_db, str):
                    cached_db = json.loads(cached_db)
                assessment_cache.set(cache_key, cached_db)
                return cached_db, 0, 0, time.perf_counter() - start_time
        except Exception as e:
            logger.warning(f"Failed to check MongoDB assessment cache: {e}")

        logger.info("Requesting new habits analysis from Gemini.")
        gemini = GeminiAIService()
        try:
            assessment_json = await gemini.analyze_sustainability(
                travel=log_data.travel,
                food=log_data.food,
                electricity=log_data.electricity,
                waste=log_data.waste,
                water=log_data.water
            )
            response_time = time.perf_counter() - start_time
            prompt_tokens = (len(log_data.travel) + len(log_data.food) + len(log_data.electricity) + len(log_data.waste) + len(log_data.water)) // 4
            completion_tokens = len(json.dumps(assessment_json)) // 4
            assessment_cache.set(cache_key, assessment_json)
            try:
                await cache_repo.set_cache(cache_key, json.dumps(assessment_json), ttl_seconds=600)
            except Exception as e:
                logger.warning(f"Failed to save assessment to MongoDB cache: {e}")
            return assessment_json, prompt_tokens, completion_tokens, response_time
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Gemini habits analysis failed: {e}"
            )

    @staticmethod
    async def _get_or_create_coaching_session(session_id: str | None, current_user_id: str, repo: CoachRepository) -> str:
        """Fetches an existing session or creates a new one for user."""
        if session_id:
            session = await repo.get_session_by_id(session_id)
            if not session or str(session["user_id"]) != current_user_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Coaching session not found."
                )
            return session_id

        new_session = {
            "user_id": ObjectId(current_user_id),
            "session_title": f"Eco Profile - {datetime.now(timezone.utc).strftime('%b %d, %H:%M')}",
            "messages": [],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        return await repo.create_session(new_session)

    @staticmethod
    def _format_assessment_md(assessment_json: dict) -> str:
        """Helper to format visual sustainability report markdown block."""
        md = "### 🌱 Sustainability Assessment Report\n\n"
        md += "#### 🚨 Top Emission Sources\n"
        for src in assessment_json.get("top_emission_sources", []):
            md += f"- {src}\n"
        md += "\n"
        
        md += "#### 💡 Personalized Recommendations\n"
        for idx, rec in enumerate(assessment_json.get("personalized_recommendations", []), 1):
            md += f"{idx}. **{rec.get('recommendation')}**\n"
            md += f"   - 💰 Savings: {rec.get('expected_savings')}\n"
            md += f"   - 🌱 CO2 Reduction: {rec.get('co2_reduction')}\n"
            md += f"   - ⚡ Difficulty: {rec.get('difficulty_level')}\n"
        md += "\n"
        
        md += "#### 📊 Summary\n"
        md += f"- **Expected Savings (Overall)**: {assessment_json.get('expected_savings')}\n"
        md += f"- **CO2 Reduction (Overall)**: {assessment_json.get('co2_reduction')}\n"
        md += f"- **Difficulty Level**: {assessment_json.get('difficulty_level')}\n"
        return md

    @staticmethod
    async def assess_habits(log_data: SustainabilityAssessmentRequest, db: Any, current_user: dict) -> dict:
        repo = CoachRepository(db)
        
        assessment_json, prompt_tokens, completion_tokens, response_time = await CoachController._get_habits_assessment(log_data)
        session_id = await CoachController._get_or_create_coaching_session(log_data.session_id, current_user["id"], repo)

        user_message_content = (
            f"Here is my sustainability profile:\n"
            f"- 🚗 Travel: {log_data.travel}\n"
            f"- 🥗 Food: {log_data.food}\n"
            f"- ⚡ Electricity: {log_data.electricity}\n"
            f"- 🗑️ Waste: {log_data.waste}\n"
            f"- 💧 Water: {log_data.water}"
        )
        
        await repo.add_message(
            session_id,
            {"role": "user", "content": user_message_content, "timestamp": datetime.now(timezone.utc)},
            token_usage={"prompt_tokens": len(user_message_content) // 4, "completion_tokens": 0, "total_tokens": len(user_message_content) // 4},
            response_time=0.0
        )

        assistant_report = CoachController._format_assessment_md(assessment_json)
        await repo.add_message(
            session_id,
            {"role": "assistant", "content": assistant_report, "timestamp": datetime.now(timezone.utc)},
            model="gemini-2.5-flash",
            token_usage={"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens, "total_tokens": prompt_tokens + completion_tokens},
            response_time=response_time
        )

        return {
            "session_id": session_id,
            "top_emission_sources": assessment_json.get("top_emission_sources", []),
            "personalized_recommendations": assessment_json.get("personalized_recommendations", []),
            "expected_savings": assessment_json.get("expected_savings", ""),
            "co2_reduction": assessment_json.get("co2_reduction", ""),
            "difficulty_level": assessment_json.get("difficulty_level", "Easy")
        }

    @staticmethod
    async def get_sessions(db: Any, current_user: dict, limit: int = 100, offset: int = 0) -> list:
        repo = CoachRepository(db)
        sessions = await repo.get_sessions(current_user["id"], limit, offset)
        for s in sessions:
            if isinstance(s.get("created_at"), datetime):
                s["created_at"] = s["created_at"].isoformat()
            if isinstance(s.get("updated_at"), datetime):
                s["updated_at"] = s["updated_at"].isoformat()
        return sessions

    @staticmethod
    async def create_session(db: Any, current_user: dict) -> dict:
        repo = CoachRepository(db)
        welcome_text = (
            "Hello! I am EcoPilot, your AI Sustainability Coach. "
            "How can I help you reduce your carbon footprint, audit utility drawers, or simulate offsets today?"
        )
        new_session = {
            "user_id": ObjectId(current_user["id"]),
            "session_title": f"Conversation thread - {datetime.now(timezone.utc).strftime('%b %d')}",
            "messages": [
                {
                    "role": "assistant",
                    "content": welcome_text,
                    "timestamp": datetime.now(timezone.utc)
                }
            ],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        sess_id = await repo.create_session(new_session)
        new_session["_id"] = sess_id
        new_session["user_id"] = str(new_session["user_id"])
        
        await repo.log_initial_chat_message(
            session_id=sess_id,
            user_id=current_user["id"],
            message=new_session["messages"][0],
            model="gemini-2.5-flash",
            token_usage={"prompt_tokens": 0, "completion_tokens": len(welcome_text) // 4, "total_tokens": len(welcome_text) // 4}
        )

        
        new_session["messages"][0]["timestamp"] = new_session["messages"][0]["timestamp"].isoformat()
        new_session["created_at"] = new_session["created_at"].isoformat()
        new_session["updated_at"] = new_session["updated_at"].isoformat()
        return new_session

    @staticmethod
    async def get_session(session_id: str, db: Any, current_user: dict, limit: int = 100, offset: int = 0) -> dict:
        repo = CoachRepository(db)
        session = await repo.get_session_by_id(session_id)
        if not session or session["user_id"] != current_user["id"]:
            raise HTTPException(status_code=404, detail="Coaching session not found")
        
        # Retrieve flat messages from chat_history collection
        flat_messages = await repo.get_messages(session_id, limit, offset)
        if flat_messages:
            session["messages"] = flat_messages
        else:
            # Fallback to legacy field serialization
            for msg in session.get("messages", []):
                if isinstance(msg.get("timestamp"), datetime):
                    msg["timestamp"] = msg["timestamp"].isoformat()
        
        if isinstance(session.get("created_at"), datetime):
            session["created_at"] = session["created_at"].isoformat()
        if isinstance(session.get("updated_at"), datetime):
            session["updated_at"] = session["updated_at"].isoformat()
            
        return session

    @staticmethod
    async def update_session(session_id: str, title: str, db: Any, current_user: dict) -> dict:
        repo = CoachRepository(db)
        session = await repo.get_session_by_id(session_id)
        if not session or session["user_id"] != current_user["id"]:
            raise HTTPException(status_code=404, detail="Coaching session not found")
            
        success = await repo.update_session_title(session_id, title)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update session title")
        return {"message": "Coaching session title updated successfully.", "session_id": session_id, "session_title": title}

    @staticmethod
    async def delete_session(session_id: str, db: Any, current_user: dict) -> dict:
        repo = CoachRepository(db)
        session = await repo.get_session_by_id(session_id)
        if not session or session["user_id"] != current_user["id"]:
            raise HTTPException(status_code=404, detail="Coaching session not found")
            
        await repo.delete_session(session_id)
        return {"message": "Coaching thread deleted successfully."}

    @staticmethod
    async def _prepare_history_summary(session_id: str, messages_list: list, session: dict, repo: CoachRepository) -> str:
        """Fetches or calculates the summary of older coaching chat messages."""
        older_history = messages_list[:-10]
        history_summary = session.get("history_summary", "")
        summarized_count = session.get("summarized_count", 0)
        new_count = len(older_history)

        if new_count > 0 and (not history_summary or new_count >= summarized_count + 4):
            gemini = GeminiAIService()
            try:
                history_summary = await gemini.generate_history_summary(older_history)
                await repo.update_session_summary(session_id, history_summary, new_count)
                logger.info(f"Updated coaching history summary for session {session_id} ({new_count} messages summarized).")
            except Exception as e:
                logger.error(f"Error computing history summary: {e}")
        return history_summary

    @staticmethod
    async def _post_user_message(session_id: str, message_text: str, history: list, repo: CoachRepository) -> int:
        """Appends new user message to the database and estimates input tokens."""
        user_msg = {
            "role": "user",
            "content": message_text,
            "timestamp": datetime.now(timezone.utc)
        }
        input_token_est = (len(message_text) + sum(len(h["content"]) for h in history)) // 4
        await repo.add_message(
            session_id=session_id,
            message=user_msg,
            model="gemini-2.5-flash",
            token_usage={"prompt_tokens": input_token_est, "completion_tokens": 0, "total_tokens": input_token_est},
            response_time=0.0
        )
        return input_token_est

    @staticmethod
    def _create_event_generator(session_id: str, history: list, user_message: str, history_summary: str, input_token_est: int, repo: CoachRepository):
        """Creates the streaming text generator for Gemini chatbot responses."""
        async def event_generator():
            gemini = GeminiAIService()
            accumulated_response = ""
            start_time = time.perf_counter()
            try:
                async for chunk in gemini.generate_chat_response_stream(history, user_message, history_summary=history_summary):
                    if chunk:
                        accumulated_response += chunk
                        yield chunk
            except Exception as e:
                logger.error(f"Streaming generator encountered error: {e}")
                err_msg = "\n\n[Coach Connection Error. Swapping commute modes or swap bulbs parameters to reduce draws.]"
                accumulated_response += err_msg
                yield err_msg

            end_time = time.perf_counter()
            response_time_sec = end_time - start_time
            completion_token_est = len(accumulated_response) // 4

            assistant_msg = {
                "role": "assistant",
                "content": accumulated_response,
                "timestamp": datetime.now(timezone.utc)
            }
            await repo.add_message(
                session_id=session_id,
                message=assistant_msg,
                model="gemini-2.5-flash",
                token_usage={
                    "prompt_tokens": input_token_est,
                    "completion_tokens": completion_token_est,
                    "total_tokens": input_token_est + completion_token_est
                },
                response_time=response_time_sec
            )
        return event_generator()

    @staticmethod
    async def stream_coach_message(session_id: str, payload: ChatMessageRequest, db: Any, current_user: dict) -> StreamingResponse:
        repo = CoachRepository(db)
        session = await repo.get_session_by_id(session_id)
        if not session or session["user_id"] != current_user["id"]:
            raise HTTPException(status_code=404, detail="Coaching session not found")

        messages_list = await repo.get_messages(session_id, limit=1000, offset=0)
        if not messages_list:
            messages_list = session.get("messages", [])

        trimmed_history = messages_list[-10:]
        history = [{"role": msg["role"], "content": msg.get("content") or msg.get("message") or ""} for msg in trimmed_history]

        history_summary = await CoachController._prepare_history_summary(session_id, messages_list, session, repo)
        input_token_est = await CoachController._post_user_message(session_id, payload.message, history, repo)
        
        gen = CoachController._create_event_generator(session_id, history, payload.message, history_summary, input_token_est, repo)
        return StreamingResponse(gen, media_type="text/event-stream")

    @staticmethod
    async def search_chat_history(q: str, limit: int, db: Any, current_user: dict) -> list:
        repo = CoachRepository(db)
        return await repo.search_messages(current_user["id"], q, limit)
