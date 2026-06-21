from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from bson import ObjectId

from repositories.footprint import FootprintRepository

class EmissionPredictionService:
    """
    Analyzes historical carbon logs for a user and runs mathematical projections
    to forecast carbon footprint trends.
    """
    def __init__(self, db):
        self.db = db

    async def predict_future_trend(self, user_id: str, months_ahead: int = 6) -> List[Dict[str, Any]]:
        """Retrieves logs, calculates average trends, and returns data points projecting future month-by-month CO2 values."""
        foot_repo = FootprintRepository(self.db)
        # Fetch user logs
        logs = await foot_repo.get_footprints_by_range(user_id, datetime.min.replace(tzinfo=timezone.utc))
        logs.sort(key=lambda x: x.get("date", datetime.now(timezone.utc)))

        if not logs:
            return self._get_default_projections(months_ahead)

        # Represent dates as numbers (days from the first log)
        first_date = logs[0]["date"]
        if first_date.tzinfo is None:
            first_date = first_date.replace(tzinfo=timezone.utc)

        slope, intercept = self._calculate_regression_coefficients(logs, first_date)
        projections = self._generate_projection_points(slope, intercept, first_date, len(logs), months_ahead)
        
        await self._save_projections(user_id, projections, foot_repo)
        return projections

    def _get_default_projections(self, months_ahead: int) -> List[Dict[str, Any]]:
        """Generates mock projections when the user has no logs."""
        baseline = 450.0
        now = datetime.now(timezone.utc)
        projections = []
        for i in range(1, months_ahead + 1):
            future_date = now + timedelta(days=30 * i)
            projections.append({
                "date": future_date.strftime("%Y-%m"),
                "co2_kg": baseline,
                "confidence": "low"
            })
        return projections

    def _calculate_regression_coefficients(self, logs: list, first_date: datetime) -> tuple[float, float]:
        """Calculates slope and intercept from a list of footprint logs."""
        baseline = 450.0
        x_values = []
        y_values = []
        for log in logs:
            log_date = log["date"]
            if log_date.tzinfo is None:
                log_date = log_date.replace(tzinfo=timezone.utc)
            days = (log_date - first_date).days
            x_values.append(days)
            y_values.append(log.get("total_co2_kg", baseline))

        n = len(logs)
        if n >= 2 and len(set(x_values)) > 1:
            mean_x = sum(x_values) / n
            mean_y = sum(y_values) / n
            numerator = sum((x_values[i] - mean_x) * (y_values[i] - mean_y) for i in range(n))
            denominator = sum((x_values[i] - mean_x) ** 2 for i in range(n))
            slope = numerator / denominator if denominator != 0 else 0.0
            intercept = mean_y - slope * mean_x
        else:
            slope = 0.0
            intercept = sum(y_values) / n
        return slope, intercept

    def _generate_projection_points(self, slope: float, intercept: float, first_date: datetime, n_logs: int, months_ahead: int) -> List[Dict[str, Any]]:
        """Generates future projection points based on regression coefficients."""
        now = datetime.now(timezone.utc)
        projections = []
        last_days = (now - first_date).days
        confidence = "high" if n_logs >= 5 else "medium"

        for i in range(1, months_ahead + 1):
            future_date = now + timedelta(days=30 * i)
            future_days = last_days + (30 * i)
            predicted_co2 = max(slope * future_days + intercept, 0.0)

            projections.append({
                "date": future_date.strftime("%Y-%m"),
                "co2_kg": round(predicted_co2, 2),
                "confidence": confidence
            })
        return projections

    async def _save_projections(self, user_id: str, projections: list, foot_repo: FootprintRepository) -> None:
        """Saves projections to MongoDB carbon_predictions collection."""
        import logging
        for proj in projections:
            try:
                await foot_repo.upsert_prediction(
                    user_id=user_id,
                    target_date=proj["date"],
                    co2_kg=proj["co2_kg"],
                    confidence=proj["confidence"]
                )
            except Exception as e:
                logging.getLogger("ecopilot.predictor").error(f"Failed to upsert carbon prediction: {e}")
