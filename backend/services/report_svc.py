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
from repositories.footprint import FootprintRepository
from repositories.user import UserRepository

logger = logging.getLogger("ecopilot.report_svc")

class ReportService:
    @staticmethod
    async def generate_report(user_id: str, report_type: str, send_email: bool, db: Any) -> Dict[str, Any]:
        """Gathers performance metrics, runs predictions, requests Gemini summary, and persists report."""
        logger.info(f"Generating {report_type} sustainability report for user {user_id}...")
        repo = ReportRepository(db)
        foot_repo = FootprintRepository(db)

        # 1. Compute carbon trend
        start_date, end_date, prior_start_date, prior_end_date = ReportService._get_report_date_ranges(report_type)
        carbon_trend = await ReportService._compute_carbon_trend(user_id, start_date, end_date, prior_start_date, prior_end_date, foot_repo)

        # 2. Retrieve predictions & achievements
        predictor = EmissionPredictionService(db)
        predictions = await predictor.predict_future_trend(user_id, months_ahead=3)
        achievements = await GamificationService.get_user_stats(user_id, db)

        # 3. Generate AI summary & suggestions
        ai_summary = await ReportService._generate_ai_summary(report_type, carbon_trend, predictions, achievements)
        suggestions = ReportService._gather_suggestions()

        # 4. Compile and save report
        report_data = ReportService._compile_report_record(user_id, report_type, start_date, end_date, carbon_trend, predictions, achievements, suggestions, ai_summary)
        report_id = await repo.insert_report(report_data)
        report_data["_id"] = report_id
        report_data["user_id"] = str(report_data["user_id"])

        # 5. Dispatch email if requested
        if send_email:
            await ReportService._send_report_email(user_id, report_data, db)

        return report_data

    @staticmethod
    def _get_report_date_ranges(report_type: str) -> tuple[datetime, datetime, datetime, datetime]:
        """Calculates current and prior period date boundaries based on report type."""
        end_date = datetime.now(timezone.utc)
        if report_type == "weekly":
            start_date = end_date - timedelta(days=7)
            prior_start_date = end_date - timedelta(days=14)
            prior_end_date = start_date
        else:
            start_date = end_date - timedelta(days=30)
            prior_start_date = end_date - timedelta(days=60)
            prior_end_date = start_date
        return start_date, end_date, prior_start_date, prior_end_date

    @staticmethod
    async def _compute_carbon_trend(user_id: str, start: datetime, end: datetime, prior_start: datetime, prior_end: datetime, foot_repo: FootprintRepository) -> Dict[str, Any]:
        """Calculates carbon footprint difference and trend direction between current and prior periods."""
        current_logs = await foot_repo.get_footprints_by_range(user_id, start, end)
        current_co2 = sum(log.get("total_co2_kg", 0.0) for log in current_logs)

        prior_logs = await foot_repo.get_footprints_by_range(user_id, prior_start, prior_end)
        prior_co2 = sum(log.get("total_co2_kg", 0.0) for log in prior_logs)

        pct_change = ((current_co2 - prior_co2) / prior_co2) * 100 if prior_co2 > 0 else 0.0
        direction = "decrease" if current_co2 < prior_co2 else "increase" if current_co2 > prior_co2 else "stable"
        
        return {
            "total_co2_kg": round(current_co2, 2),
            "previous_co2_kg": round(prior_co2, 2),
            "percentage_change": round(abs(pct_change), 2),
            "direction": direction
        }

    @staticmethod
    async def _generate_ai_summary(report_type: str, trend: dict, predictions: list, achievements: dict) -> str:
        """Invokes Gemini to construct a natural-language report summary."""
        gemini = GeminiAIService()
        try:
            return await gemini.generate_report_summary(
                report_type=report_type,
                trend=trend,
                predictions=predictions,
                achievements=achievements
            )
        except Exception as e:
            logger.error(f"Failed to generate AI report summary: {e}")
            total_co2 = trend.get("total_co2_kg", 0.0)
            pct = trend.get("percentage_change", 0.0)
            direction = trend.get("direction", "stable")
            return (
                f"EcoPilot report review: Carbon footprint was {total_co2:.2f} kg CO2e, showing a "
                f"{pct:.1f}% {direction} versus prior period. "
                "Keep working on optimizing utility drawer draws and swapping transport options!"
            )

    @staticmethod
    def _gather_suggestions() -> List[Dict[str, str]]:
        """Gathers personalized carbon mitigation recommendations."""
        return [
            {"category": "energy", "recommendation": "Replace standard light bulbs with high-efficiency 9W LEDs.", "difficulty": "Easy", "co2_reduction": "25 kg CO2 / month"},
            {"category": "transport", "recommendation": "Switch daily travel commutes to electric vehicles or public transit.", "difficulty": "Medium", "co2_reduction": "150 kg CO2 / month"},
            {"category": "food", "recommendation": "Adopt a low-impact plant-based vegetarian or vegan diet 4 days a week.", "difficulty": "Easy", "co2_reduction": "60 kg CO2 / month"}
        ]

    @staticmethod
    def _compile_report_record(user_id: str, report_type: str, start: datetime, end: datetime, trend: dict, predictions: list, achievements: dict, suggestions: list, ai_summary: str) -> Dict[str, Any]:
        """Assembles a report metadata document to save to MongoDB."""
        return {
            "user_id": ObjectId(user_id),
            "report_type": report_type,
            "start_date": start,
            "end_date": end,
            "carbon_trend": trend,
            "predictions": predictions,
            "achievements": {
                "xp_earned": achievements.get("points", 0),
                "badges_unlocked": achievements.get("badges", [])
            },
            "suggestions": suggestions,
            "ai_summary": ai_summary,
            "created_at": datetime.now(timezone.utc)
        }

    @staticmethod
    async def _send_report_email(user_id: str, report_data: dict, db: Any) -> None:
        """Sends PDF report attachment via email using UserRepository."""
        try:
            user_repo = UserRepository(db)
            user = await user_repo.get_by_id(user_id)
            if user and user.get("email"):
                pdf_bytes = PDFService.generate_report_pdf(report_data)
                await EmailService.send_report_email(user["email"], report_data, pdf_bytes)
        except Exception as e:
            logger.error(f"Failed to compile PDF or dispatch report email: {e}")
