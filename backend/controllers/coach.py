import hashlib
import json
import logging
from datetime import datetime
from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from bson import ObjectId

from ai.gemini_ai import GeminiAIService
from services.cache_svc import assessment_cache
from repositories.coach import CoachRepository
from schemas.coach import SustainabilityAssessmentRequest, SustainabilityAssessmentResponse, ChatMessageRequest

logger = logging.getLogger("ecopilot.coach")

class CoachController:
    @staticmethod
    async def assess_habits(log_data: SustainabilityAssessmentRequest, db, current_user: dict) -> dict:
        repo = CoachRepository(db)
        # Compute sha256 cache key from habits contents to optimize latency
        cache_str = f"{log_data.travel}||{log_data.food}||{log_data.electricity}||{log_data.waste}||{log_data.water}"
        cache_key = hashlib.sha256(cache_str.encode("utf-8")).hexdigest()
        
        cached_result = assessment_cache.get(cache_key)
        if cached_result:
            logger.info("Serving cached habits assessment.")
            assessment_json = cached_result
        else:
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
                # Cache results
                assessment_cache.set(cache_key, assessment_json)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Gemini analysis failed: {e}"
                )

        # Retrieve or create coaching session
        session_id = log_data.session_id
        if not session_id:
            # Spawn new thread
            new_session = {
                "user_id": ObjectId(current_user["id"]),
                "session_title": f"Eco Profile - {datetime.utcnow().strftime('%b %d, %H:%M')}",
                "messages": [],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            session_id = await repo.create_session(new_session)

        # Construct summary of prompt input
        user_message_content = (
            f"Here is my sustainability profile:\n"
            f"- 🚗 Travel: {log_data.travel}\n"
            f"- 🥗 Food: {log_data.food}\n"
            f"- ⚡ Electricity: {log_data.electricity}\n"
            f"- 🗑️ Waste: {log_data.waste}\n"
            f"- 💧 Water: {log_data.water}"
        )
        
        # Append user habits statement message
        user_msg = {
            "role": "user",
            "content": user_message_content,
            "timestamp": datetime.utcnow()
        }
        await repo.add_message(session_id, user_msg)

        # Format assistant audit report message
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
        assistant_report = md

        assistant_msg = {
            "role": "assistant",
            "content": assistant_report,
            "timestamp": datetime.utcnow()
        }
        await repo.add_message(session_id, assistant_msg)

        # Format output
        return {
            "session_id": session_id,
            "top_emission_sources": assessment_json.get("top_emission_sources", []),
            "personalized_recommendations": assessment_json.get("personalized_recommendations", []),
            "expected_savings": assessment_json.get("expected_savings", ""),
            "co2_reduction": assessment_json.get("co2_reduction", ""),
            "difficulty_level": assessment_json.get("difficulty_level", "Easy")
        }

    @staticmethod
    async def get_sessions(db, current_user: dict) -> list:
        repo = CoachRepository(db)
        sessions = await repo.get_sessions(current_user["id"])
        for s in sessions:
            if isinstance(s.get("created_at"), datetime):
                s["created_at"] = s["created_at"].isoformat()
            if isinstance(s.get("updated_at"), datetime):
                s["updated_at"] = s["updated_at"].isoformat()
        return sessions

    @staticmethod
    async def create_session(db, current_user: dict) -> dict:
        repo = CoachRepository(db)
        welcome_text = (
            "Hello! I am EcoPilot, your AI Sustainability Coach. "
            "How can I help you reduce your carbon footprint, audit utility drawers, or simulate offsets today?"
        )
        new_session = {
            "user_id": ObjectId(current_user["id"]),
            "session_title": f"Conversation thread - {datetime.utcnow().strftime('%b %d')}",
            "messages": [
                {
                    "role": "assistant",
                    "content": welcome_text,
                    "timestamp": datetime.utcnow()
                }
            ],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        sess_id = await repo.create_session(new_session)
        new_session["_id"] = sess_id
        new_session["user_id"] = str(new_session["user_id"])
        
        new_session["messages"][0]["timestamp"] = new_session["messages"][0]["timestamp"].isoformat()
        new_session["created_at"] = new_session["created_at"].isoformat()
        new_session["updated_at"] = new_session["updated_at"].isoformat()
        return new_session

    @staticmethod
    async def get_session(session_id: str, db, current_user: dict) -> dict:
        repo = CoachRepository(db)
        session = await repo.get_session_by_id(session_id)
        if not session or session["user_id"] != current_user["id"]:
            raise HTTPException(status_code=404, detail="Coaching session not found")
        
        # Serialize datetimes
        for msg in session.get("messages", []):
            if isinstance(msg.get("timestamp"), datetime):
                msg["timestamp"] = msg["timestamp"].isoformat()
        if isinstance(session.get("created_at"), datetime):
            session["created_at"] = session["created_at"].isoformat()
        if isinstance(session.get("updated_at"), datetime):
            session["updated_at"] = session["updated_at"].isoformat()
            
        return session

    @staticmethod
    async def delete_session(session_id: str, db, current_user: dict) -> dict:
        repo = CoachRepository(db)
        session = await repo.get_session_by_id(session_id)
        if not session or session["user_id"] != current_user["id"]:
            raise HTTPException(status_code=404, detail="Coaching session not found")
            
        await repo.delete_session(session_id)
        return {"message": "Coaching thread deleted successfully."}

    @staticmethod
    async def stream_coach_message(session_id: str, payload: ChatMessageRequest, db, current_user: dict) -> StreamingResponse:
        repo = CoachRepository(db)
        session = await repo.get_session_by_id(session_id)
        if not session or session["user_id"] != current_user["id"]:
            raise HTTPException(status_code=404, detail="Coaching session not found")

        # Append user message
        user_msg = {
            "role": "user",
            "content": payload.message,
            "timestamp": datetime.utcnow()
        }
        await repo.add_message(session_id, user_msg)

        # Prepare messages history format for LLM context
        history = [{"role": msg["role"], "content": msg["content"]} for msg in session.get("messages", [])]
        
        async def event_generator():
            gemini = GeminiAIService()
            accumulated_response = ""
            try:
                async for chunk in gemini.generate_chat_response_stream(history, payload.message):
                    if chunk:
                        accumulated_response += chunk
                        yield chunk
            except Exception as e:
                logger.error(f"Streaming generator encountered error: {e}")
                err_msg = "\n\n[Coach Connection Error. Swapping commute modes or swap bulbs parameters to reduce draws.]"
                accumulated_response += err_msg
                yield err_msg

            # Save assistant response
            assistant_msg = {
                "role": "assistant",
                "content": accumulated_response,
                "timestamp": datetime.utcnow()
            }
            await repo.add_message(session_id, assistant_msg)

        return StreamingResponse(event_generator(), media_type="text/event-stream")
