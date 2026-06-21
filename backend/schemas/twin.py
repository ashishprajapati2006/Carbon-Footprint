from pydantic import BaseModel, Field
from typing import List


class TwinSimulationRequest(BaseModel):
    buy_ev: bool = Field(default=False, description="Simulate swapping commute to an electric vehicle")
    install_solar: bool = Field(default=False, description="Simulate installing solar panels at home")
    stop_flying: bool = Field(default=False, description="Simulate stopping all airline travel")
    reduce_ac: bool = Field(default=False, description="Simulate reducing daily AC usage")


class ChartDataPoint(BaseModel):
    month: str = Field(..., description="Abbreviated month name (e.g. Jan)")
    current: float = Field(..., description="CO2 emission value for current profile in kg")
    simulated: float = Field(..., description="CO2 emission value for simulated profile in kg")


class TwinSimulationResponse(BaseModel):
    id: str = Field(..., description="Unique simulation run database ID")
    original_co2_kg: float = Field(..., description="Baseline monthly carbon emissions in kg")
    projected_co2_kg: float = Field(..., description="Projected monthly carbon emissions after adjustments in kg")
    reduction_kg: float = Field(..., description="Absolute CO2 savings in kg")
    reduction_pct: float = Field(..., description="Percentage reduction of carbon emissions")
    savings_usd_desc: str = Field(..., description="Gemini-calculated description of financial savings")
    lifestyle_impact: str = Field(..., description="Gemini-calculated lifestyle description")
    top_savings_sources: List[str] = Field(..., description="List of the primary drivers of carbon savings")
    chart_data: List[ChartDataPoint] = Field(..., description="Data points for frontend charting")
