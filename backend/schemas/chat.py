from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from .base import PyObjectId


class ChatMessageItem(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatSessionCreate(BaseModel):
    session_title: str


class ChatSessionResponse(BaseModel):
    id: PyObjectId = Field(alias="_id")
    user_id: PyObjectId
    session_title: str
    messages: List[ChatMessageItem]
    updated_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
    )


class ChatHistoryMessageResponse(BaseModel):
    id: Optional[PyObjectId] = Field(None, alias="_id")
    conversation_id: PyObjectId
    session_id: PyObjectId
    user_id: PyObjectId
    timestamp: datetime
    role: str
    message: str
    content: str
    model: str
    token_usage: Dict[str, int]
    response_time: float
    metadata: Dict[str, Any]

    model_config = ConfigDict(
        populate_by_name=True,
    )
