from datetime import datetime, timezone
from typing import List
from pydantic import BaseModel, Field, ConfigDict
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
    id: str
    user_id: str
    quest_title: str
    description: str
    xp_yield: int
    goal_amount: int
    current_amount: int
    category: str
    status: str
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(
        populate_by_name=True,
    )


class ChallengeClaimResponse(BaseModel):
    message: str
    awarded: int
    total_points: int
    badges_unlocked: List[str] = Field(default_factory=list)
