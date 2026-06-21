from datetime import datetime
from pydantic import BaseModel, Field
from .base import PyObjectId


class BillAnalysisResponse(BaseModel):
    id: PyObjectId = Field(alias="_id")
    user_id: PyObjectId
    file_url: str
    billing_period: str
    kwh_consumed: float
    total_cost: float
    carbon_footprint_kg: float
    extracted_raw_text: str
    analyzed_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
