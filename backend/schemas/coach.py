from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class MessageItem(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatMessageRequest(BaseModel):
    message: str


class ChatSessionResponse(BaseModel):
    id: str = Field(..., alias="_id")
    user_id: str
    session_title: str
    messages: List[MessageItem]
    updated_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
    )


class ChatSessionList(BaseModel):
    id: str = Field(..., alias="_id")
    session_title: str
    updated_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
    )


class SustainabilityAssessmentRequest(BaseModel):
    travel: str = Field(..., description="Travel habits")
    food: str = Field(..., description="Dietary habits")
    electricity: str = Field(..., description="Electricity consumption and energy habits")
    waste: str = Field(..., description="Waste generation and recycling habits")
    water: str = Field(..., description="Water consumption habits")
    session_id: Optional[str] = Field(None, description="Optional existing coaching session ID to append this to")


class RecommendationItem(BaseModel):
    recommendation: str = Field(..., description="Actionable recommendation text")
    expected_savings: str = Field(..., description="Estimated resource or financial savings")
    co2_reduction: str = Field(..., description="Estimated carbon reduction (e.g., '120 kg CO2 / year')")
    difficulty_level: str = Field(..., description="Difficulty rating (Easy, Medium, Hard)")


class SustainabilityAssessmentResponse(BaseModel):
    session_id: str
    top_emission_sources: List[str] = Field(..., description="Top sources of carbon emissions")
    personalized_recommendations: List[RecommendationItem] = Field(..., description="List of personalized recommendations")
    expected_savings: str = Field(..., description="Overall expected savings description")
    co2_reduction: str = Field(..., description="Overall expected carbon reduction description")
    difficulty_level: str = Field(..., description="Overall difficulty of recommendations")


class ChatSessionUpdateResponse(BaseModel):
    message: str
    session_id: str
    session_title: str


class GenericMessageResponse(BaseModel):
    message: str
