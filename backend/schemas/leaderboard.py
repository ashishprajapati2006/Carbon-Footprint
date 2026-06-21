from datetime import datetime
from pydantic import BaseModel, Field
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
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
