from bson import ObjectId
from typing import List, Dict, Any, Optional

class BillRepository:
    def __init__(self, db):
        self.db = db

    async def log_bill_analysis(self, scan_entry: Dict[str, Any]) -> str:
        if isinstance(scan_entry.get("user_id"), str):
            scan_entry["user_id"] = ObjectId(scan_entry["user_id"])
        res = await self.db["bill_analyses"].insert_one(scan_entry)
        return str(res.inserted_id)

    async def get_history(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        cursor = self.db["bill_analyses"].find({"user_id": ObjectId(user_id)})
        scans = await cursor.to_list(length=limit)
        
        for scan in scans:
            scan["_id"] = str(scan["_id"])
            scan["user_id"] = str(scan["user_id"])
            
        scans.sort(key=lambda x: x.get("billing_period", ""), reverse=True)
        return scans

    async def get_by_id(self, bill_id: str) -> Optional[Dict[str, Any]]:
        bill = await self.db["bill_analyses"].find_one({"_id": ObjectId(bill_id)})
        if bill:
            bill["_id"] = str(bill["_id"])
            bill["user_id"] = str(bill["user_id"])
        return bill
