from datetime import datetime, timezone
from fastapi import UploadFile, HTTPException, status
from bson import ObjectId

from ocr.vision_svc import VisionAnalysisService
from ai.gemini_ai import GeminiAIService
from repositories.room import RoomRepository

class RoomController:
    @staticmethod
    async def scan_room_image(file: UploadFile, room_type: str, db, current_user: dict) -> dict:
        repo = RoomRepository(db)
        file_bytes = await file.read()
        content_type = file.content_type or "image/jpeg"

        gemini = GeminiAIService()
        vision_svc = VisionAnalysisService(gemini)

        try:
            audit_data = await vision_svc.audit_room_image(file_bytes, content_type, room_type)

            scan_entry = {
                "user_id": ObjectId(current_user["id"]),
                "image_url": file.filename,
                "room_type": audit_data.get("room_type", room_type),
                "detected_appliances": audit_data.get("detected_appliances", []),
                "total_energy_waste_kwh": audit_data.get("total_energy_waste_kwh", 0.0),
                "total_carbon_impact_kg": audit_data.get("total_carbon_impact_kg", 0.0),
                "total_yearly_cost_usd": audit_data.get("total_yearly_cost_usd", 0.0),
                "overall_room_eco_score": audit_data.get("overall_room_eco_score", 50),
                "recommendations": audit_data.get("recommendations", []),
                "analyzed_at": datetime.now(timezone.utc)
            }

            inserted_id = await repo.log_room_analysis(scan_entry)
            scan_entry["_id"] = inserted_id
            scan_entry["user_id"] = str(scan_entry["user_id"])

            if isinstance(scan_entry["analyzed_at"], datetime):
                scan_entry["analyzed_at"] = scan_entry["analyzed_at"].isoformat()

            return scan_entry

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to scan room image: {e}"
            )

    @staticmethod
    async def list_room_scans(db, current_user: dict) -> list:
        repo = RoomRepository(db)
        scans = await repo.get_history(current_user["id"])
        
        for scan in scans:
            if isinstance(scan.get("analyzed_at"), datetime):
                scan["analyzed_at"] = scan["analyzed_at"].isoformat()
        return scans
