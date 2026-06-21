from fastapi import APIRouter, Depends
from typing import List

from core.database import get_db
from core.security import get_current_user
from core.rate_limit import assessment_rate_limiter
from controllers.coach import CoachController
from schemas.coach import (
    SustainabilityAssessmentRequest,
    SustainabilityAssessmentResponse,
    ChatMessageRequest
)

router = APIRouter(prefix="/coach", tags=["AI Coaching Coach"])

@router.get("/sessions")
async def get_sessions(db = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Retrieves all chat session instances for the active user."""
    return await CoachController.get_sessions(db, current_user)

@router.post("/sessions")
async def create_session(db = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Initializes a new coach thread."""
    return await CoachController.create_session(db, current_user)

@router.post("/assess", response_model=SustainabilityAssessmentResponse)
async def assess_sustainability(
    payload: SustainabilityAssessmentRequest,
    db = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _rate_limit = Depends(assessment_rate_limiter)
):
    """
    Submits a sustainability assessment.
    Analyzes habits using Gemini API, caches results, and updates/initializes a coaching session.
    """
    return await CoachController.assess_habits(payload, db, current_user)

@router.post("/sessions/{session_id}/message/stream")
async def send_coach_message_stream(
    session_id: str,
    payload: ChatMessageRequest,
    db = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Streams the assistant response and persists the conversation to MongoDB."""
    return await CoachController.stream_coach_message(session_id, payload, db, current_user)

@router.get("/sessions/{session_id}")
async def get_session_detail(
    session_id: str,
    db = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Retrieves full details of a specific chat session."""
    return await CoachController.get_session(session_id, db, current_user)

@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    db = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Deletes a chat session from history."""
    return await CoachController.delete_session(session_id, db, current_user)
