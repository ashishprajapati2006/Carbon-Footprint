from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime
from typing import List, Dict, Any, Optional

class CoachRepository:
    def __init__(self, db):
        self.db = db

    async def get_sessions(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        cursor = self.db["coaching_sessions"].find({"user_id": ObjectId(user_id)})
        sessions = await cursor.to_list(length=limit)
        
        for sess in sessions:
            sess["_id"] = str(sess["_id"])
            sess["user_id"] = str(sess["user_id"])
            
        sessions.sort(key=lambda x: x.get("updated_at") or "", reverse=True)
        return sessions

    async def create_session(self, session: Dict[str, Any]) -> str:
        if isinstance(session.get("user_id"), str):
            session["user_id"] = ObjectId(session["user_id"])
        res = await self.db["coaching_sessions"].insert_one(session)
        return str(res.inserted_id)

    async def get_session_by_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        if not ObjectId.is_valid(session_id):
            return None
        sess = await self.db["coaching_sessions"].find_one({"_id": ObjectId(session_id)})
        if sess:
            sess["_id"] = str(sess["_id"])
            sess["user_id"] = str(sess["user_id"])
        return sess

    async def add_message(self, session_id: str, message: Dict[str, Any]) -> bool:
        if not ObjectId.is_valid(session_id):
            return False
        res = await self.db["coaching_sessions"].update_one(
            {"_id": ObjectId(session_id)},
            {
                "$push": {"messages": message},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        return res.modified_count > 0

    async def delete_session(self, session_id: str) -> bool:
        if not ObjectId.is_valid(session_id):
            return False
        res = await self.db["coaching_sessions"].delete_one({"_id": ObjectId(session_id)})
        return res.deleted_count > 0
