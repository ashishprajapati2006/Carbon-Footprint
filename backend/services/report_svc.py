import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List
from bson import ObjectId

from ai.gemini_ai import GeminiAIService
from ml.predictor import EmissionPredictionService
from services.gamification_svc import GamificationService
from services.pdf_svc import PDFService
from services.email_svc import EmailService
from repositories.report import ReportRepository

logger = logging.getLogger("ecopilot.report_svc")

class ReportService:
    @staticmethod
    async def generate_report(user_id: str, report_type: str, send_email: bool, db: Any) -> Dict[str, Any]:
        """
        Gathers performance metrics, runs predictions, requests Gemini summary,
        persists the report, and optionally sends it as a PDF attachment via email.
        """
        logger.info(f"Generating {report_type} sustainability report for user {user_id}...")
        repo = ReportRepository(db)
        
        # 1. Determine date ranges
        end_date = datetime.now(timezone.utc)
        if report_type == "weekly":
            start_date = end_date - timedelta(days=7)
            prior_start_date = end_date - timedelta(days=14)
            prior_end_date = start_date
        else:  # monthly
            start_date = end_date - timedelta(days=30)
            prior_start_date = end_date - timedelta(days=60)
            prior_end_date = start_date

        # 2. Compute carbon trend
        cursor_current = db["footprint_logs"].find({
            "user_id": ObjectId(user_id),
            "date": {"$gte": start_date, "$lte": end_date}
        })
        current_logs = await cursor_current.to_list(length=500)
        current_co2 = sum(log.get("total_co2_kg", 0.0) for log in current_logs)

        cursor_prior = db["footprint_logs"].find({
            "user_id": ObjectId(user_id),
            "date": {"$gte": prior_start_date, "$lte": prior_end_date}
        })
        prior_logs = await cursor_prior.to_list(length=500)
        prior_co2 = sum(log.get("total_co2_kg", 0.0) for log in prior_logs)

        if prior_co2 > 0:
            pct_change = ((current_co2 - prior_co2) / prior_co2) * 100
        else:
            pct_change = 0.0
            
        direction = "decrease" if current_co2 < prior_co2 else "increase" if current_co2 > prior_co2 else "stable"
        carbon_trend = {
            "total_co2_kg": round(current_co2, 2),
            "previous_co2_kg": round(prior_co2, 2),
            "percentage_change": round(abs(pct_change), 2),
            "direction": direction
        }

        # 3. Retrieve predictions
        predictor = EmissionPredictionService(db)
        predictions = await predictor.predict_future_trend(user_id, months_ahead=3)

        # 4. Gather achievements
        achievements = await GamificationService.get_user_stats(user_id, db)
        
        # 5. Gather personalized suggestions
        suggestions = [
            {
                "category": "energy",
                "recommendation": "Replace standard light bulbs with high-efficiency 9W LEDs.",
                "difficulty": "Easy",
                "co2_reduction": "25 kg CO2 / month"
            },
            {
                "category": "transport",
                "recommendation": "Switch daily travel commutes to electric vehicles or public transit.",
                "difficulty": "Medium",
                "co2_reduction": "150 kg CO2 / month"
            },
            {
                "category": "food",
                "recommendation": "Adopt a low-impact plant-based vegetarian or vegan diet 4 days a week.",
                "difficulty": "Easy",
                "co2_reduction": "60 kg CO2 / month"
            }
        ]

        # 6. Request AI narrative summary from Gemini
        gemini = GeminiAIService()
        try:
            ai_summary = await gemini.generate_report_summary(
                report_type=report_type,
                trend=carbon_trend,
                predictions=predictions,
                achievements=achievements
            )
        except Exception as e:
            logger.error(f"Failed to generate AI report summary: {e}")
            ai_summary = (
                f"EcoPilot report review: Carbon footprint was {current_co2:.2f} kg CO2e, showing a "
                f"{carbon_trend['percentage_change']:.1f}% {direction} versus prior period. "
                "Keep working on optimizing utility drawer draws and swapping transport options!"
            )

        # 7. Compile report record
        report_data = {
            "user_id": ObjectId(user_id),
            "report_type": report_type,
            "start_date": start_date,
            "end_date": end_date,
            "carbon_trend": carbon_trend,
            "predictions": predictions,
            "achievements": {
                "xp_earned": achievements.get("points", 0),
                "badges_unlocked": achievements.get("badges", [])
            },
            "suggestions": suggestions,
            "ai_summary": ai_summary,
            "created_at": datetime.now(timezone.utc)
        }

        # 8. Save report to MongoDB
        report_id = await repo.insert_report(report_data)
        report_data["_id"] = report_id
        report_data["user_id"] = str(report_data["user_id"])

        # 9. Send report email with PDF attachment if requested
        if send_email:
            try:
                user = await db["users"].find_one({"_id": ObjectId(user_id)})
                if user and user.get("email"):
                    pdf_bytes = PDFService.generate_report_pdf(report_data)
                    await EmailService.send_report_email(user["email"], report_data, pdf_bytes)
            except Exception as e:
                logger.error(f"Failed to compile PDF or dispatch report email: {e}")

        return report_data
