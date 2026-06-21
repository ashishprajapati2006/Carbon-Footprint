from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from .base import PyObjectId


class ActivityCreate(BaseModel):
    activity_type: str = Field(..., description="e.g. transport, energy, food, waste, combined")
    date: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = Field(default_factory=dict, description="Custom properties matching category")
    co2_kg: float = Field(..., ge=0.0)


class ActivityResponse(BaseModel):
    id: PyObjectId = Field(alias="_id")
    user_id: PyObjectId
    activity_type: str
    date: datetime
    details: Dict[str, Any]
    co2_kg: float

    model_config = ConfigDict(
        populate_by_name=True,
    )
