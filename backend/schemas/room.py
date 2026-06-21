from datetime import datetime
from typing import List
from pydantic import BaseModel, Field, ConfigDict
from .base import PyObjectId


class ApplianceAudit(BaseModel):
    name: str
    type: str
    energy_efficiency_estimate: str  # "High", "Medium", "Low"
    detected_issues: List[str]
    eco_alternative: str
    energy_waste_kwh: float = 0.0
    carbon_impact_kg: float = 0.0
    yearly_cost_usd: float = 0.0


class RoomScanResponse(BaseModel):
    id: PyObjectId = Field(alias="_id")
    user_id: PyObjectId
    image_url: str
    room_type: str
    detected_appliances: List[ApplianceAudit]
    total_energy_waste_kwh: float = 0.0
    total_carbon_impact_kg: float = 0.0
    total_yearly_cost_usd: float = 0.0
    overall_room_eco_score: int
    recommendations: List[str]
    analyzed_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
    )
