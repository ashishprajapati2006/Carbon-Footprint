from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from .base import PyObjectId


class ActivityCreate(BaseModel):
    activity_type: str = Field(..., description="e.g. transport, energy, food, waste, combined")
    date: Optional[datetime] = Field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = Field(default_factory=dict, description="Custom properties matching category")
    co2_kg: float = Field(..., ge=0.0)


class ActivityResponse(BaseModel):
    id: PyObjectId = Field(alias="_id")
    user_id: PyObjectId
    activity_type: str
    date: datetime
    details: Dict[str, Any]
    co2_kg: float

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
