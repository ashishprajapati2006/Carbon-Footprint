from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

class CoachRepository:
    def __init__(self, db: Any):
        self.db = db

    async def get_sessions(self, user_id: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        cursor = self.db["coaching_sessions"].find({"user_id": ObjectId(user_id)}).skip(offset).limit(limit)
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

    async def add_message(
        self,
        session_id: str,
        message: Dict[str, Any],
        model: str = "gemini-2.5-flash",
        token_usage: Optional[Dict[str, int]] = None,
        response_time: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        if not ObjectId.is_valid(session_id):
            return False

        # Get session to extract user_id
        session = await self.get_session_by_id(session_id)
        if not session:
            return False
        user_id = ObjectId(session["user_id"])

        # 1. Update the session document for compatibility with legacy array logic
        legacy_msg = {
            "role": message["role"],
            "content": message.get("content") or message.get("message") or "",
            "timestamp": message.get("timestamp") or datetime.now(timezone.utc)
        }
        res_session = await self.db["coaching_sessions"].update_one(
            {"_id": ObjectId(session_id)},
            {
                "$push": {"messages": legacy_msg},
                "$set": {"updated_at": datetime.now(timezone.utc)}
            }
        )

        # 2. Write to the flat chat_history collection
        chat_doc = {
            "conversation_id": ObjectId(session_id),
            "session_id": ObjectId(session_id),
            "user_id": user_id,
            "timestamp": legacy_msg["timestamp"],
            "role": legacy_msg["role"],
            "message": legacy_msg["content"],
            "content": legacy_msg["content"],  # For UI compatibility
            "model": model or "gemini-2.5-flash",
            "token_usage": token_usage or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "response_time": response_time or 0.0,
            "metadata": metadata or {},
            "updated_at": datetime.now(timezone.utc)
        }
        await self.db["chat_history"].insert_one(chat_doc)

        return res_session.modified_count > 0

    async def get_messages(self, session_id: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieves messages for a session from the chat_history collection."""
        if not ObjectId.is_valid(session_id):
            return []
        cursor = self.db["chat_history"].find({"session_id": ObjectId(session_id)}).sort("timestamp", 1).skip(offset).limit(limit)
        messages = await cursor.to_list(length=limit)
        for msg in messages:
            if "_id" in msg:
                msg["_id"] = str(msg["_id"])
            if "session_id" in msg:
                msg["session_id"] = str(msg["session_id"])
            if "conversation_id" in msg:
                msg["conversation_id"] = str(msg["conversation_id"])
            if "user_id" in msg:
                msg["user_id"] = str(msg["user_id"])
            if isinstance(msg.get("timestamp"), datetime):
                msg["timestamp"] = msg["timestamp"].isoformat()
        return messages

    async def update_session_title(self, session_id: str, title: str) -> bool:
        if not ObjectId.is_valid(session_id):
            return False
        res = await self.db["coaching_sessions"].update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"session_title": title, "updated_at": datetime.now(timezone.utc)}}
        )
        return res.modified_count > 0

    async def delete_session(self, session_id: str) -> bool:
        if not ObjectId.is_valid(session_id):
            return False
        # 1. Delete session metadata document
        res_sess = await self.db["coaching_sessions"].delete_one({"_id": ObjectId(session_id)})
        # 2. Delete messages in chat_history
        await self.db["chat_history"].delete_many({"session_id": ObjectId(session_id)})
        return res_sess.deleted_count > 0

    async def search_messages(self, user_id: str, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Searches messages within the user's chat history matching the keyword query."""
        cursor = self.db["chat_history"].find({
            "user_id": ObjectId(user_id),
            "message": {"$regex": query, "$options": "i"}
        }).sort("timestamp", -1).limit(limit)
        results = await cursor.to_list(length=limit)
        for msg in results:
            if "_id" in msg:
                msg["_id"] = str(msg["_id"])
            if "session_id" in msg:
                msg["session_id"] = str(msg["session_id"])
            if "conversation_id" in msg:
                msg["conversation_id"] = str(msg["conversation_id"])
            if "user_id" in msg:
                msg["user_id"] = str(msg["user_id"])
            if isinstance(msg.get("timestamp"), datetime):
                msg["timestamp"] = msg["timestamp"].isoformat()
        return results
