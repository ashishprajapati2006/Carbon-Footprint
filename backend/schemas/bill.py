from datetime import datetime
from typing import List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from .base import PyObjectId


class BillAnalysisResponse(BaseModel):
    id: PyObjectId = Field(alias="_id")
    user_id: PyObjectId
    file_url: str
    billing_period: str
    consumption_value: float
    consumption_unit: str
    total_cost: float
    carbon_footprint_kg: float
    savings_opportunities: List[str]
    trend: Dict[str, Any]
    extracted_raw_text: str
    analyzed_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
    )
