from bson import ObjectId
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
