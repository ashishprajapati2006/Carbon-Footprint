from fastapi import APIRouter, Depends, Query
from typing import List, Any, Optional

from core.database import get_db
from core.security import get_current_user
from core.rate_limit import assessment_rate_limiter
from controllers.coach import CoachController
from schemas.coach import (
    SustainabilityAssessmentRequest,
    SustainabilityAssessmentResponse,
    ChatMessageRequest,
    ChatSessionResponse,
    ChatSessionList,
    ChatSessionUpdateResponse,
    GenericMessageResponse
)
from schemas.chat import ChatHistoryMessageResponse

router = APIRouter(prefix="/coach", tags=["AI Coaching Coach"])

@router.get("/sessions", response_model=List[ChatSessionList])
async def get_sessions(
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Any = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Retrieves all chat session instances for the active user (paginated)."""
    return await CoachController.get_sessions(db, current_user, limit, offset)

@router.post("/sessions", response_model=ChatSessionResponse)
async def create_session(db: Any = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Initializes a new coach thread."""
    return await CoachController.create_session(db, current_user)

@router.post("/assess", response_model=SustainabilityAssessmentResponse)
async def assess_sustainability(
    payload: SustainabilityAssessmentRequest,
    db: Any = Depends(get_db),
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
    db: Any = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Streams the assistant response and persists the conversation to MongoDB."""
    return await CoachController.stream_coach_message(session_id, payload, db, current_user)

@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_session_detail(
    session_id: str,
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Any = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Retrieves full details of a specific chat session with paginated messages."""
    return await CoachController.get_session(session_id, db, current_user, limit, offset)

@router.put("/sessions/{session_id}", response_model=ChatSessionUpdateResponse)
async def update_session(
    session_id: str,
    title: str = Query(..., min_length=1, max_length=100),
    db: Any = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Updates the title of a specific chat session (chat update)."""
    return await CoachController.update_session(session_id, title, db, current_user)

@router.delete("/sessions/{session_id}", response_model=GenericMessageResponse)
async def delete_session(
    session_id: str,
    db: Any = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Deletes a chat session and all its message history from MongoDB."""
    return await CoachController.delete_session(session_id, db, current_user)

@router.get("/search", response_model=List[ChatHistoryMessageResponse])
async def search_chat_history(
    q: str = Query(..., min_length=1),
    limit: int = Query(50, ge=1, le=100),
    db: Any = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Searches across user's message history matching keyword query (chat search)."""
    return await CoachController.search_chat_history(q, limit, db, current_user)
