from fastapi import APIRouter, Depends, status, Response
from typing import List, Any

from core.database import get_db
from core.security import get_current_user
from schemas.report import ReportGenerateRequest, ReportResponse
from schemas.coach import GenericMessageResponse
from controllers.report import ReportController

router = APIRouter(prefix="/reports", tags=["Sustainability Reports"])

@router.post("/generate", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def generate_report(
    payload: ReportGenerateRequest,
    db: Any = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Compiles and registers a weekly or monthly performance report."""
    return await ReportController.generate_report(payload, db, current_user)

@router.get("", response_model=List[ReportResponse])
async def get_reports(
    db: Any = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Retrieves all generated reports for the active user."""
    return await ReportController.get_reports(db, current_user)

@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    db: Any = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Retrieves detailed information of a specific report."""
    return await ReportController.get_report(report_id, db, current_user)

@router.get("/{report_id}/pdf")
async def get_report_pdf(
    report_id: str,
    db: Any = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Downloads the compiled PDF version of the report."""
    return await ReportController.get_report_pdf(report_id, db, current_user)

@router.delete("/{report_id}", response_model=GenericMessageResponse)
async def delete_report(
    report_id: str,
    db: Any = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Deletes a report instance from MongoDB."""
    return await ReportController.delete_report(report_id, db, current_user)
