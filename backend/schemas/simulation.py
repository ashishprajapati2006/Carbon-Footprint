from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from .base import PyObjectId


class SimulationRunCreate(BaseModel):
    simulation_title: str
    inputs: Dict[str, Any]
    original_co2_kg: float = Field(..., ge=0.0)
    projected_co2_kg: float = Field(..., ge=0.0)
    savings_percentage: float = Field(0.0, ge=0.0, le=100.0)


class SimulationRunResponse(BaseModel):
    id: PyObjectId = Field(alias="_id")
    user_id: PyObjectId
    simulation_title: str
    inputs: Dict[str, Any]
    original_co2_kg: float
    projected_co2_kg: float
    savings_percentage: float
    simulated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
