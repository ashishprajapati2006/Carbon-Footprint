import logging
from datetime import datetime, timezone
from typing import Any
from fastapi import UploadFile, HTTPException, status
from bson import ObjectId

from core.config import settings
from ocr.ocr_svc import OCRService
from services.analysis_svc import BillAnalysisService
from ai.gemini_ai import GeminiAIService
from services.gamification_svc import GamificationService
from repositories.bill import BillRepository
from repositories.footprint import FootprintRepository

logger = logging.getLogger("ecopilot.bill")

class BillController:
    @staticmethod
    async def _extract_ocr_text(file_bytes: bytes, filename: str, content_type: str, gemini: GeminiAIService, analysis_service: BillAnalysisService) -> tuple[dict | None, str]:
        """Extracts parsed utility metrics data and text content from file bytes."""
        parsed_data = None
        ocr_text = ""
        
        if not gemini.is_mock:
            try:
                logger.info("Performing direct multimodal analysis on the statement...")
                parsed_data = await analysis_service.analyze_bill_multimodal(file_bytes, content_type)
                ocr_text = (
                    f"Multimodal Scan Results:\n"
                    f"Period: {parsed_data.get('billing_period')}\n"
                    f"Consumption: {parsed_data.get('consumption_value')} {parsed_data.get('consumption_unit')}\n"
                    f"Cost: {parsed_data.get('total_cost')}"
                )
            except Exception as e:
                logger.warning(f"Direct multimodal analysis failed: {e}. Falling back to OCR pipeline...")

        if not parsed_data:
            from ocr.ocr_svc import OCRService
            ocr_service = OCRService()
            ocr_text = await ocr_service.perform_ocr(file_bytes, filename, content_type)
            if not ocr_text.strip():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Failed to extract readable text from statement. Ensure the document is clear."
                )
            try:
                parsed_data = await analysis_service.analyze_bill_text(ocr_text)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to process utility statement: {e}"
                )
        return parsed_data, ocr_text

    @staticmethod
    def _build_bill_entry(parsed_data: dict, ocr_text: str, filename: str, carbon_footprint: float, trend_data: dict, user_id: str) -> dict:
        """Helper to build utility statement document for logging."""
        return {
            "user_id": ObjectId(user_id),
            "file_url": filename,
            "billing_period": parsed_data["billing_period"],
            "consumption_value": parsed_data["consumption_value"],
            "consumption_unit": parsed_data["consumption_unit"],
            "total_cost": parsed_data["total_cost"],
            "carbon_footprint_kg": carbon_footprint,
            "savings_opportunities": parsed_data["savings_opportunities"],
            "trend": trend_data,
            "extracted_raw_text": ocr_text[:1000],
            "analyzed_at": datetime.now(timezone.utc)
        }

    @staticmethod
    async def _log_footprint_from_bill(consumption_value: float, consumption_unit: str, carbon_footprint: float, user_id: str, db: Any) -> None:
        """Logs corresponding footprint entry from statement consumption data."""
        category = "energy"
        u_lower = consumption_unit.lower()
        if u_lower == "therms":
            category = "gas"
        elif u_lower in ["gallons", "liters", "ccf"]:
            category = "water"

        footprint_entry = {
            "user_id": ObjectId(user_id),
            "date": datetime.now(timezone.utc),
            "categories": {
                category: {
                    "usage": consumption_value,
                    "unit": consumption_unit,
                    "co2_kg": carbon_footprint
                }
            },
            "total_co2_kg": round(carbon_footprint, 2)
        }
        foot_repo = FootprintRepository(db)
        await foot_repo.log_footprint(footprint_entry)

    @staticmethod
    async def upload_bill(file: UploadFile, db: Any, current_user: dict) -> dict:
        from utils.file_validator import validate_uploaded_file, sanitize_filename
        
        allowed_exts = {"pdf", "png", "jpg", "jpeg"}
        allowed_mimes = {"application/pdf", "image/png", "image/jpeg", "image/jpg"}
        
        try:
            file_bytes = await validate_uploaded_file(
                file=file,
                allowed_extensions=allowed_exts,
                allowed_mimes=allowed_mimes,
                max_size=settings.max_upload_size
            )
        finally:
            await file.close()
            
        filename = sanitize_filename(file.filename or "statement.jpg")
        content_type = file.content_type or "image/jpeg"

        gemini = GeminiAIService()
        analysis_service = BillAnalysisService(gemini)
        
        parsed_data, ocr_text = await BillController._extract_ocr_text(file_bytes, filename, content_type, gemini, analysis_service)
            
        try:
            carbon_footprint = analysis_service.calculate_carbon_footprint(parsed_data["consumption_value"], parsed_data["consumption_unit"])
            trend_data = await analysis_service.calculate_trend(
                user_id=current_user["id"],
                current_period=parsed_data["billing_period"],
                current_value=parsed_data["consumption_value"],
                current_cost=parsed_data["total_cost"],
                current_unit=parsed_data["consumption_unit"],
                db=db
            )

            bill_entry = BillController._build_bill_entry(parsed_data, ocr_text, filename, carbon_footprint, trend_data, current_user["id"])
            repo = BillRepository(db)
            inserted_id = await repo.log_bill_analysis(bill_entry)
            bill_entry["_id"] = inserted_id
            bill_entry["user_id"] = str(bill_entry["user_id"])

            await BillController._log_footprint_from_bill(parsed_data["consumption_value"], parsed_data["consumption_unit"], carbon_footprint, current_user["id"], db)

            try:
                await GamificationService.award_points(current_user["id"], "bill_upload", db)
            except Exception as e:
                logger.error(f"Failed to award bill upload points: {e}")

            if isinstance(bill_entry["analyzed_at"], datetime):
                bill_entry["analyzed_at"] = bill_entry["analyzed_at"].isoformat()
            return bill_entry

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process utility statement: {e}"
            )

    @staticmethod
    async def get_bills(db: Any, current_user: dict) -> list:
        repo = BillRepository(db)
        return await repo.get_history(current_user["id"])
