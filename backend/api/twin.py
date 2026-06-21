from fastapi import APIRouter, Depends

from core.database import get_db
from core.security import get_current_user
from controllers.twin import TwinController
from schemas.twin import TwinSimulationRequest, TwinSimulationResponse

router = APIRouter(prefix="/twin", tags=["Carbon Twin Simulation"])

@router.post("/simulate", response_model=TwinSimulationResponse)
async def simulate_carbon_twin(
    payload: TwinSimulationRequest,
    db = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Simulates lifestyle adjustments (EV, Solar, Stop Flying, AC reduction).
    Predicts footprint change via the trained ML model and analyzes savings via Gemini.
    Stores the simulation in MongoDB.
    """
    return await TwinController.simulate_carbon_twin(payload, db, current_user)
