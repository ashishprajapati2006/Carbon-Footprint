from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from bson import ObjectId


class EmissionPredictionService:
    """
    Analyzes historical carbon logs for a user and runs mathematical projections
    to forecast carbon footprint trends.
    """
    def __init__(self, db):
        self.db = db

    async def predict_future_trend(self, user_id: str, months_ahead: int = 6) -> List[Dict[str, Any]]:
        """
        Retrieves logs, calculates average trends, and returns data points projecting
        future month-by-month CO2 values.
        """
        # Fetch user logs sorted by date ascending
        cursor = self.db["footprint_logs"].find({"user_id": ObjectId(user_id)})
        logs = await cursor.to_list(length=100)

        # Sort logs by date manually to guarantee ascending order
        logs.sort(key=lambda x: x.get("date", datetime.now(timezone.utc)))

        # Base default footprint if no logs exist (e.g. ~500 kg CO2 / month average for single person)
        baseline = 450.0

        if not logs:
            # Generate static future points based on general average baseline
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

        # Extract values
        x_values = []
        y_values = []
        
        # We represent dates as numbers (days from the first log)
        first_date = logs[0]["date"]
        # Ensure first_date is timezone-aware
        if first_date.tzinfo is None:
            first_date = first_date.replace(tzinfo=timezone.utc)
            
        for log in logs:
            log_date = log["date"]
            if log_date.tzinfo is None:
                log_date = log_date.replace(tzinfo=timezone.utc)
            days = (log_date - first_date).days
            x_values.append(days)
            y_values.append(log.get("total_co2_kg", baseline))

        # Perform simple linear regression if we have at least 2 distinct logs
        n = len(logs)
        if n >= 2 and len(set(x_values)) > 1:
            # Least squares line: y = mx + c
            mean_x = sum(x_values) / n
            mean_y = sum(y_values) / n
            
            numerator = sum((x_values[i] - mean_x) * (y_values[i] - mean_y) for i in range(n))
            denominator = sum((x_values[i] - mean_x) ** 2 for i in range(n))
            
            slope = numerator / denominator if denominator != 0 else 0.0
            intercept = mean_y - slope * mean_x
        else:
            # If not enough data points, assume stable flat line based on current average
            slope = 0.0
            intercept = sum(y_values) / n

        # Generate future month projections
        now = datetime.now(timezone.utc)
        projections = []
        last_days = (now - first_date).days

        for i in range(1, months_ahead + 1):
            future_date = now + timedelta(days=30 * i)
            future_days = last_days + (30 * i)
            
            # Compute regression estimate
            predicted_co2 = slope * future_days + intercept
            
            # Avoid predicting negative emissions
            predicted_co2 = max(predicted_co2, 0.0)

            projections.append({
                "date": future_date.strftime("%Y-%m"),
                "co2_kg": round(predicted_co2, 2),
                "confidence": "high" if n >= 5 else "medium"
            })

        # Save predictions to MongoDB carbon_predictions collection
        for proj in projections:
            try:
                await self.db["carbon_predictions"].update_one(
                    {
                        "user_id": ObjectId(user_id),
                        "target_date": proj["date"]
                    },
                    {
                        "$set": {
                            "predicted_co2_kg": proj["co2_kg"],
                            "confidence": proj["confidence"],
                            "created_at": datetime.now(timezone.utc)
                        }
                    },
                    upsert=True
                )
            except Exception as e:
                import logging
                logging.getLogger("ecopilot.predictor").error(f"Failed to upsert carbon prediction: {e}")

        return projections
