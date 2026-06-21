from datetime import datetime, timezone
from typing import List
from pydantic import BaseModel, Field, ConfigDict
from .base import PyObjectId


class LeaderboardEntryCreate(BaseModel):
    username: str
    level_name: str
    monthly_co2_kg: float = Field(..., ge=0.0)
    rank_position: int = Field(..., ge=1)


class LeaderboardEntryResponse(BaseModel):
    id: PyObjectId = Field(alias="_id")
    user_id: PyObjectId
    username: str
    level_name: str
    monthly_co2_kg: float
    rank_position: int
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(
        populate_by_name=True,
    )


class UserStatsResponse(BaseModel):
    points: int
    weekly_points: int
    monthly_points: int
    level: int
    xp_in_level: int
    badges: List[str]


class LeaderboardResponse(BaseModel):
    rank: int
    user_id: str
    name: str
    level: str
    points: int
    monthly_co2_kg: float
    isMe: bool
