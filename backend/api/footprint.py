from fastapi import APIRouter, Depends, status
from typing import List, Any

from core.database import get_db
from core.security import get_current_user
from schemas.footprint import FootprintLogCreate, FootprintLogResponse, SimulationRequest, SimulationResponse, PredictionPointResponse
from controllers.footprint import FootprintController

router = APIRouter(prefix="/footprint", tags=["Carbon Footprint"])

@router.post("/log", response_model=FootprintLogResponse, status_code=status.HTTP_201_CREATED)
async def log_footprint(log_data: FootprintLogCreate, db: Any = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Computes carbon categories and logs footprint values to the database."""
    return await FootprintController.log_footprint(log_data, db, current_user)

@router.get("/history", response_model=List[FootprintLogResponse])
async def get_history(db: Any = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Retrieves user historical footprint entries."""
    return await FootprintController.get_history(db, current_user)

@router.get("/predict", response_model=List[PredictionPointResponse])
async def predict_trends(db: Any = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Forecasts emissions for the user over the next 6 months."""
    return await FootprintController.predict_trends(db, current_user)

@router.post("/simulate", response_model=SimulationResponse)
async def run_lifestyle_simulation(sim_data: SimulationRequest, db: Any = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Calculates potential carbon footprint savings from simulated habits."""
    return await FootprintController.run_lifestyle_simulation(sim_data, db, current_user)
