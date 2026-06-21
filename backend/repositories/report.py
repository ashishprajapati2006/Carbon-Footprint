from bson import ObjectId
from typing import List, Dict, Any, Optional

class ReportRepository:
    def __init__(self, db: Any):
        self.db = db

    async def insert_report(self, report: Dict[str, Any]) -> str:
        if isinstance(report.get("user_id"), str):
            report["user_id"] = ObjectId(report["user_id"])
        res = await self.db["reports"].insert_one(report)
        return str(res.inserted_id)

    async def get_reports_by_user(self, user_id: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        cursor = self.db["reports"].find({"user_id": ObjectId(user_id)}).skip(offset).limit(limit)
        reports = await cursor.to_list(length=limit)
        for r in reports:
            r["_id"] = str(r["_id"])
            r["user_id"] = str(r["user_id"])
        # Sort descending by created_at
        reports.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        return reports

    async def get_report_by_id(self, report_id: str) -> Optional[Dict[str, Any]]:
        if not ObjectId.is_valid(report_id):
            return None
        r = await self.db["reports"].find_one({"_id": ObjectId(report_id)})
        if r:
            r["_id"] = str(r["_id"])
            r["user_id"] = str(r["user_id"])
        return r

    async def delete_report(self, report_id: str) -> bool:
        if not ObjectId.is_valid(report_id):
            return False
        res = await self.db["reports"].delete_one({"_id": ObjectId(report_id)})
        return res.deleted_count > 0
