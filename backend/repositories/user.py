from bson import ObjectId
from datetime import datetime
from typing import Dict, Any, Optional, List

class UserRepository:
    def __init__(self, db: Any):
        self.db = db

    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        return await self.db["users"].find_one({"email": email})

    async def get_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        return await self.db["users"].find_one({"_id": ObjectId(user_id)})

    async def create(self, user_data: Dict[str, Any]) -> str:
        res = await self.db["users"].insert_one(user_data)
        return str(res.inserted_id)

    async def update_profile(self, user_id: str, profile_data: Dict[str, Any]) -> bool:
        res = await self.db["users"].update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"profile": profile_data}}
        )
        return res.modified_count > 0

    async def update_password(self, email: str, password_hash: str) -> bool:
        res = await self.db["users"].update_one(
            {"email": email},
            {"$set": {"password_hash": password_hash}}
        )
        return res.modified_count > 0

    async def create_refresh_token(self, token: str, user_id: str, expires_at: datetime):
        await self.db["refresh_tokens"].insert_one({
            "token": token,
            "user_id": ObjectId(user_id),
            "expires_at": expires_at
        })

    async def get_refresh_token(self, token: str) -> Optional[Dict[str, Any]]:
        return await self.db["refresh_tokens"].find_one({"token": token})

    async def delete_refresh_token(self, token: str) -> bool:
        res = await self.db["refresh_tokens"].delete_one({"token": token})
        return res.deleted_count > 0

    async def delete_all_refresh_tokens(self, user_id: str) -> int:
        res = await self.db["refresh_tokens"].delete_many({"user_id": ObjectId(user_id)})
        return res.deleted_count

    async def create_password_reset(self, token: str, email: str, expires_at: datetime):
        await self.db["password_resets"].insert_one({
            "token": token,
            "email": email,
            "expires_at": expires_at
        })

    async def get_password_reset(self, token: str) -> Optional[Dict[str, Any]]:
        return await self.db["password_resets"].find_one({"token": token})

    async def delete_password_reset(self, token: str) -> bool:
        res = await self.db["password_resets"].delete_one({"token": token})
        return res.deleted_count > 0

    async def update_points_and_badges(self, user_id: str, points: int, badges: List[str]) -> bool:
        res = await self.db["users"].update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"points": points, "badges": badges}}
        )
        return res.modified_count > 0

