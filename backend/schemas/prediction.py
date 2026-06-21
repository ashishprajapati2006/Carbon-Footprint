from datetime import datetime
from pydantic import BaseModel, Field
from .base import PyObjectId


class CarbonPredictionCreate(BaseModel):
    target_date: str = Field(..., description="Target forecast month, format YYYY-MM")
    predicted_co2_kg: float = Field(..., ge=0.0)
    confidence: str = Field("medium", description="high, medium, low")


class CarbonPredictionResponse(BaseModel):
    id: PyObjectId = Field(alias="_id")
    user_id: PyObjectId
    target_date: str
    predicted_co2_kg: float
    confidence: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
