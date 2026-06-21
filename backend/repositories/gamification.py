from bson import ObjectId
from datetime import datetime
from typing import List, Dict, Any, Optional

class GamificationRepository:
    def __init__(self, db: Any):
        self.db = db

    async def get_points_logs(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        cursor = self.db["points_logs"].find({"user_id": ObjectId(user_id)})
        logs = await cursor.to_list(length=limit)
        for log in logs:
            log["_id"] = str(log["_id"])
            log["user_id"] = str(log["user_id"])
        return logs

    async def get_points_logs_by_range(self, user_id: str, start_date: datetime) -> List[Dict[str, Any]]:
        cursor = self.db["points_logs"].find({
            "user_id": ObjectId(user_id),
            "timestamp": {"$gte": start_date}
        })
        logs = await cursor.to_list(length=100)
        for log in logs:
            log["_id"] = str(log["_id"])
            log["user_id"] = str(log["user_id"])
        return logs

    async def get_challenges(self, user_id: str) -> List[Dict[str, Any]]:
        cursor = self.db["challenges"].find({"user_id": ObjectId(user_id)})
        ch_list = await cursor.to_list(length=100)
        for ch in ch_list:
            ch["_id"] = str(ch["_id"])
            ch["user_id"] = str(ch["user_id"])
        return ch_list

    async def get_challenge_by_id(self, quest_id: str) -> Optional[Dict[str, Any]]:
        ch = await self.db["challenges"].find_one({"_id": ObjectId(quest_id)})
        if ch:
            ch["_id"] = str(ch["_id"])
            ch["user_id"] = str(ch["user_id"])
        return ch

    async def update_challenge(self, quest_id: str, updates: Dict[str, Any]) -> bool:
        res = await self.db["challenges"].update_one(
            {"_id": ObjectId(quest_id)},
            {"$set": updates}
        )
        return res.modified_count > 0

    async def insert_challenge(self, challenge: Dict[str, Any]) -> str:
        if isinstance(challenge.get("user_id"), str):
            challenge["user_id"] = ObjectId(challenge["user_id"])
        res = await self.db["challenges"].insert_one(challenge)
        return str(res.inserted_id)

    async def get_all_users_sorted_by_points(self, limit: int = 50) -> List[Dict[str, Any]]:
        cursor = self.db["users"].find({}, {"full_name": 1, "points": 1, "badges": 1}).sort("points", -1)
        users = await cursor.to_list(length=limit)
        for u in users:
            u["_id"] = str(u["_id"])
        return users

    async def get_points_logs_since(self, start_date: datetime) -> List[Dict[str, Any]]:
        cursor = self.db["points_logs"].find({"timestamp": {"$gte": start_date}})
        logs = await cursor.to_list(length=500)
        for log in logs:
            log["_id"] = str(log["_id"])
            log["user_id"] = str(log["user_id"])
        return logs
