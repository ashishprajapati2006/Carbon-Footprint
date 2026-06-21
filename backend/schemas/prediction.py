from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict
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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(
        populate_by_name=True,
    )
