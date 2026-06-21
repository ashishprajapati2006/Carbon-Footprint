from datetime import datetime
from typing import List
from pydantic import BaseModel, Field
from .base import PyObjectId


class ApplianceAudit(BaseModel):
    name: str
    energy_efficiency_estimate: str  # "High", "Medium", "Low"
    detected_issues: List[str]
    eco_alternative: str


class RoomScanResponse(BaseModel):
    id: PyObjectId = Field(alias="_id")
    user_id: PyObjectId
    image_url: str
    room_type: str
    detected_appliances: List[ApplianceAudit]
    overall_room_eco_score: int
    recommendations: List[str]
    analyzed_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
