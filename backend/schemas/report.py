from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from .base import PyObjectId

class ReportGenerateRequest(BaseModel):
    report_type: str = Field("monthly", description="weekly or monthly")
    send_email: bool = Field(False, description="Send the report via email")

class ReportResponse(BaseModel):
    id: PyObjectId = Field(alias="_id")
    user_id: PyObjectId
    report_type: str
    start_date: datetime
    end_date: datetime
    carbon_trend: Dict[str, Any]
    predictions: List[Dict[str, Any]]
    achievements: Dict[str, Any]
    suggestions: List[Dict[str, Any]]
    ai_summary: str
    created_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
    )
