from datetime import datetime
from pydantic import BaseModel, Field
from .base import PyObjectId


class ChallengeCreate(BaseModel):
    quest_title: str
    description: str
    xp_yield: int = Field(50, ge=0)
    goal_amount: int = Field(1, ge=1)
    current_amount: int = Field(0, ge=0)
    category: str = Field("food", description="food, transport, energy, waste")
    status: str = Field("in_progress", description="in_progress, completed, claimed")


class ChallengeResponse(BaseModel):
    id: PyObjectId = Field(alias="_id")
    user_id: PyObjectId
    quest_title: str
    description: str
    xp_yield: int
    goal_amount: int
    current_amount: int
    category: str
    status: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
