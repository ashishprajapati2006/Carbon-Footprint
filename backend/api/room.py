from fastapi import APIRouter, Depends, UploadFile, File, Form
from typing import Any, List

from core.database import get_db
from core.security import get_current_user
from controllers.room import RoomController
from schemas.room import RoomScanResponse

router = APIRouter(prefix="/rooms", tags=["Room Scanning"])

@router.post("/scan", response_model=RoomScanResponse)
async def scan_room_image(
    file: UploadFile = File(...),
    room_type: str = Form("living_room"),
    db: Any = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Processes room captures using Gemini Vision and lists appliance savings opportunities."""
    return await RoomController.scan_room_image(file, room_type, db, current_user)

@router.get("/scans", response_model=List[RoomScanResponse])
async def list_room_scans(db: Any = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Retrieves list of user room eco scan audits."""
    return await RoomController.list_room_scans(db, current_user)
