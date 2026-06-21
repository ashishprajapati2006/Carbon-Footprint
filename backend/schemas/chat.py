from datetime import datetime
from typing import List
from pydantic import BaseModel, Field
from .base import PyObjectId


class ChatMessageItem(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatSessionCreate(BaseModel):
    session_title: str


class ChatSessionResponse(BaseModel):
    id: PyObjectId = Field(alias="_id")
    user_id: PyObjectId
    session_title: str
    messages: List[ChatMessageItem]
    updated_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
