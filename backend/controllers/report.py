"""
Report Controller — Automated Carbon Sustainability Report Generation.

Generates comprehensive sustainability reports for EcoPilot users:
  - Aggregates carbon footprint history from MongoDB into monthly/annual summaries
  - Computes carbon trend analysis (improving / worsening / stable)
  - Produces AI-generated sustainability narrative via Google Gemini
  - Renders downloadable PDF reports with embedded carbon charts
  - Supports email delivery of sustainability reports (SMTP integration)

Aligned with SDG 13 (Climate Action): provides data-driven insights to help
users quantify and reduce their carbon impact over time.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from fastapi import HTTPException, status
from fastapi.responses import Response

from schemas.report import ReportGenerateRequest
from services.report_svc import ReportService
from services.pdf_svc import PDFService
from repositories.report import ReportRepository

logger = logging.getLogger("ecopilot.report_controller")


class ReportController:
    @staticmethod
    async def generate_report(payload: ReportGenerateRequest, db: Any, current_user: dict) -> dict:
        try:
            report = await ReportService.generate_report(
                user_id=current_user["id"],
                report_type=payload.report_type,
                send_email=payload.send_email,
                db=db
            )
            # Serialize datetimes
            if isinstance(report.get("start_date"), datetime):
                report["start_date"] = report["start_date"].isoformat()
            if isinstance(report.get("end_date"), datetime):
                report["end_date"] = report["end_date"].isoformat()
            if isinstance(report.get("created_at"), datetime):
                report["created_at"] = report["created_at"].isoformat()
            return report
        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate sustainability report: {e}"
            )

    @staticmethod
    async def get_reports(db: Any, current_user: dict) -> list:
        repo = ReportRepository(db)
        reports = await repo.get_reports_by_user(current_user["id"])
        for r in reports:
            if isinstance(r.get("start_date"), datetime):
                r["start_date"] = r["start_date"].isoformat()
            if isinstance(r.get("end_date"), datetime):
                r["end_date"] = r["end_date"].isoformat()
            if isinstance(r.get("created_at"), datetime):
                r["created_at"] = r["created_at"].isoformat()
        return reports

    @staticmethod
    async def get_report(report_id: str, db: Any, current_user: dict) -> dict:
        repo = ReportRepository(db)
        report = await repo.get_report_by_id(report_id)
        if not report or report["user_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sustainability report not found."
            )
        if isinstance(report.get("start_date"), datetime):
            report["start_date"] = report["start_date"].isoformat()
        if isinstance(report.get("end_date"), datetime):
            report["end_date"] = report["end_date"].isoformat()
        if isinstance(report.get("created_at"), datetime):
            report["created_at"] = report["created_at"].isoformat()
        return report

    @staticmethod
    async def get_report_pdf(report_id: str, db: Any, current_user: dict) -> Response:
        repo = ReportRepository(db)
        report = await repo.get_report_by_id(report_id)
        if not report or report["user_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sustainability report not found."
            )
        
        try:
            pdf_bytes = PDFService.generate_report_pdf(report)
            filename = f"EcoPilot_Report_{report.get('report_type', 'monthly')}_{report_id}.pdf"
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"'
                }
            )
        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to compile report PDF: {e}"
            )

    @staticmethod
    async def delete_report(report_id: str, db: Any, current_user: dict) -> dict:
        repo = ReportRepository(db)
        report = await repo.get_report_by_id(report_id)
        if not report or report["user_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sustainability report not found."
            )
        
        success = await repo.delete_report(report_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete report."
            )
        return {"message": "Sustainability report deleted successfully."}
