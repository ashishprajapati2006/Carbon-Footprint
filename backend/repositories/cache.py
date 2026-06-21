import time
from typing import Any, Optional
from core.database import DatabaseManager

class CacheRepository:
    """
    MongoDB repository for API response caching.
    Ensures shared caching across all application instances (Vercel/Render)
    to protect Gemini API quota.
    """
    def __init__(self, db: Any = None):
        self.db = db

    def _get_db(self):
        if self.db is not None:
            return self.db
        return DatabaseManager.get_db()

    async def get_cache(self, key: str) -> Optional[Any]:
        db = self._get_db()
        doc = await db["api_cache"].find_one({"key": key})
        if doc:
            if time.time() > doc.get("expiry", 0):
                await db["api_cache"].delete_one({"key": key})
                return None
            return doc.get("value")
        return None

    async def set_cache(self, key: str, value: Any, ttl_seconds: int) -> None:
        db = self._get_db()
        expiry = time.time() + ttl_seconds
        await db["api_cache"].update_one(
            {"key": key},
            {"$set": {"value": value, "expiry": expiry}},
            upsert=True
        )

    async def delete_cache(self, key: str) -> None:
        db = self._get_db()
        await db["api_cache"].delete_one({"key": key})

    async def clear_cache(self) -> None:
        db = self._get_db()
        await db["api_cache"].delete_many({})
