from bson import ObjectId
from typing import List, Dict, Any

class TwinRepository:
    def __init__(self, db: Any):
        self.db = db

    async def get_user_footprint_logs(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        cursor = self.db["footprint_logs"].find({"user_id": ObjectId(user_id)})
        return await cursor.to_list(length=limit)

    async def insert_simulation(self, simulation_record: Dict[str, Any]) -> str:
        if isinstance(simulation_record.get("user_id"), str):
            simulation_record["user_id"] = ObjectId(simulation_record["user_id"])
        res = await self.db["carbon_twin_simulations"].insert_one(simulation_record)
        return str(res.inserted_id)
