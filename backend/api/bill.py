from fastapi import APIRouter, Depends, UploadFile, File
from typing import List, Any

from core.database import get_db
from core.security import get_current_user
from controllers.bill import BillController
from schemas.bill import BillAnalysisResponse

router = APIRouter(prefix="/bills", tags=["Utility Bill Analysis"])

@router.post("/upload", response_model=BillAnalysisResponse)
async def upload_bill(
    file: UploadFile = File(...),
    db: Any = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Uploads and scans utility statement data logs using Gemini Vision."""
    return await BillController.upload_bill(file, db, current_user)

@router.get("", response_model=List[BillAnalysisResponse])
async def get_bills(
    db: Any = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Retrieves previous user bill analyses logs."""
    return await BillController.get_bills(db, current_user)
