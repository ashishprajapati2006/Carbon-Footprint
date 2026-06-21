from bson import ObjectId
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional


class FootprintRepository:
    def __init__(self, db: Any):
        self.db = db

    async def log_footprint(self, log_entry: Dict[str, Any]) -> str:
        # Convert user_id if string
        if isinstance(log_entry.get("user_id"), str):
            log_entry["user_id"] = ObjectId(log_entry["user_id"])
        res = await self.db["footprint_logs"].insert_one(log_entry)
        return str(res.inserted_id)

    async def get_history(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        cursor = self.db["footprint_logs"].find({"user_id": ObjectId(user_id)})
        logs = await cursor.to_list(length=limit)
        
        # Format IDs for serialization convenience
        for log in logs:
            log["_id"] = str(log["_id"])
            log["user_id"] = str(log["user_id"])
            
        # Sort descending by date
        logs.sort(key=lambda x: x.get("date"), reverse=True)
        return logs

    async def get_latest_log(self, user_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.db["footprint_logs"].find({"user_id": ObjectId(user_id)}).sort("date", -1)
        logs = await cursor.to_list(length=1)
        if logs:
            log = logs[0]
            log["_id"] = str(log["_id"])
            log["user_id"] = str(log["user_id"])
            return log
        return None

    async def get_footprints_by_range(self, user_id: str, start_date: datetime, end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        query = {
            "user_id": ObjectId(user_id),
            "date": {"$gte": start_date}
        }
        if end_date:
            query["date"]["$lte"] = end_date
        cursor = self.db["footprint_logs"].find(query)
        logs = await cursor.to_list(length=1000)
        for log in logs:
            log["_id"] = str(log["_id"])
            log["user_id"] = str(log["user_id"])
        return logs

    async def upsert_prediction(self, user_id: str, target_date: str, co2_kg: float, confidence: str) -> bool:
        res = await self.db["carbon_predictions"].update_one(
            {
                "user_id": ObjectId(user_id),
                "target_date": target_date
            },
            {
                "$set": {
                    "predicted_co2_kg": co2_kg,
                    "confidence": confidence,
                    "created_at": datetime.now(timezone.utc)
                }
            },
            upsert=True
        )
        return res.modified_count > 0 or res.upserted_id is not None

