from bson import ObjectId
from typing import List, Dict, Any

class RoomRepository:
    def __init__(self, db):
        self.db = db

    async def log_room_analysis(self, scan_entry: Dict[str, Any]) -> str:
        if isinstance(scan_entry.get("user_id"), str):
            scan_entry["user_id"] = ObjectId(scan_entry["user_id"])
        res = await self.db["room_analyses"].insert_one(scan_entry)
        return str(res.inserted_id)

    async def get_history(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        cursor = self.db["room_analyses"].find({"user_id": ObjectId(user_id)})
        scans = await cursor.to_list(length=limit)
        
        for scan in scans:
            scan["_id"] = str(scan["_id"])
            scan["user_id"] = str(scan["user_id"])
            
        scans.sort(key=lambda x: x.get("analyzed_at") or "", reverse=True)
        return scans
