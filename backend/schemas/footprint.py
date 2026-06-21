from datetime import datetime
from typing import Optional, Dict
from pydantic import BaseModel, Field, ConfigDict


class EnergyFootprint(BaseModel):
    kwh: float = Field(0.0, description="Electricity consumed in kWh")
    co2_kg: float = Field(0.0, description="Emissions in kg CO2")


class TransportFootprint(BaseModel):
    mode: str = Field("none", description="Vehicle type: EV, petrol, diesel, public, flight, bicycle, none")
    distance_km: float = Field(0.0, description="Distance traveled in km")
    co2_kg: float = Field(0.0, description="Emissions in kg CO2")


class FoodFootprint(BaseModel):
    diet_type: str = Field("omnivore", description="Diet type: vegan, vegetarian, omnivore, high_meat")
    co2_kg: float = Field(0.0, description="Emissions in kg CO2")


class WasteFootprint(BaseModel):
    waste_weight_kg: float = Field(0.0, description="Waste generated in kg")
    recycled: bool = Field(False, description="Is waste recycled")
    co2_kg: float = Field(0.0, description="Emissions in kg CO2")


class FootprintLogCreate(BaseModel):
    energy: Optional[EnergyFootprint] = None
    transport: Optional[TransportFootprint] = None
    food: Optional[FoodFootprint] = None
    waste: Optional[WasteFootprint] = None
    date: Optional[datetime] = None


class FootprintLogResponse(BaseModel):
    id: str = Field(..., alias="_id")
    user_id: str
    date: datetime
    categories: Dict[str, dict]
    total_co2_kg: float

    model_config = ConfigDict(
        populate_by_name=True,
    )


class SimulationRequest(BaseModel):
    change_transport_mode: Optional[str] = None
    diet_change: Optional[str] = None
    solar_installation: Optional[bool] = None


class SimulationResponse(BaseModel):
    original_co2_kg: float
    projected_co2_kg: float
    potential_saving_percentage: float
    recommendations: list[str]


class PredictionPointResponse(BaseModel):
    date: str
    co2_kg: float
    confidence: str
