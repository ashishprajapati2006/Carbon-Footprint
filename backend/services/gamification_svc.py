import logging
import math
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from bson import ObjectId

logger = logging.getLogger("ecopilot.gamification_svc")

ACTION_POINTS = {
    "daily_tracking": 10,
    "bill_upload": 50,
    "challenge_claim": 100,
    "coach_usage": 20
}

BADGE_THRESHOLDS = [
    {"name": "Eco Warrior", "points": 100},
    {"name": "Green Hero", "points": 500},
    {"name": "Carbon Crusher", "points": 1000},
    {"name": "Net Zero Champion", "points": 2500}
]

class GamificationService:
    POINTS_PER_LEVEL = 200

    @staticmethod
    def get_week_start() -> datetime:
        """Returns the start of the current week (Monday 00:00:00 UTC)."""
        now = datetime.now(timezone.utc)
        # weekday() is 0 for Monday, 6 for Sunday
        start = now - timedelta(days=now.weekday())
        return start.replace(hour=0, minute=0, second=0, microsecond=0)

    @staticmethod
    def get_month_start() -> datetime:
        """Returns the start of the current month (1st of current month 00:00:00 UTC)."""
        now = datetime.now(timezone.utc)
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    @classmethod
    async def award_points(cls, user_id: str, action: str, db: Any) -> Dict[str, Any]:
        """
        Awards points to a user for a given action.
        Logs the transaction, updates user total points/badges, and returns update details.
        """
        points = ACTION_POINTS.get(action, 0)
        if points == 0:
            logger.warning(f"Attempted to award points for unrecognized action: {action}")
            return {"awarded": 0, "total": 0, "badges_unlocked": []}

        # 1. Log the points transaction
        log_entry = {
            "user_id": ObjectId(user_id),
            "action": action,
            "points": points,
            "timestamp": datetime.now(timezone.utc)
        }
        await db["points_logs"].insert_one(log_entry)

        # 2. Get the current user profile
        user = await db["users"].find_one({"_id": ObjectId(user_id)})
        if not user:
            logger.error(f"User {user_id} not found when awarding points.")
            return {"awarded": points, "total": points, "badges_unlocked": []}

        current_points = user.get("points", 0)
        current_badges = user.get("badges", [])

        new_points = current_points + points
        new_badges = list(current_badges)

        # 3. Evaluate Badge thresholds
        unlocked_new_badges = []
        for badge_def in BADGE_THRESHOLDS:
            badge_name = badge_def["name"]
            req_points = badge_def["points"]
            if new_points >= req_points and badge_name not in new_badges:
                new_badges.append(badge_name)
                unlocked_new_badges.append(badge_name)

        # 4. Save to user document
        await db["users"].update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"points": new_points, "badges": new_badges}}
        )

        # Sync user profile & emissions to leaderboard collection
        try:
            await cls.sync_user_to_leaderboard(user_id, db)
        except Exception as e:
            logger.error(f"Failed to sync user leaderboard stats: {e}")

        logger.info(f"Awarded {points} points to user {user_id} for '{action}'. Total: {new_points}. New badges: {unlocked_new_badges}")
        return {
            "awarded": points,
            "total_points": new_points,
            "badges_unlocked": unlocked_new_badges,
            "all_badges": new_badges
        }

    @classmethod
    async def get_user_stats(cls, user_id: str, db: Any) -> Dict[str, Any]:
        """
        Retrieves user points (Weekly, Monthly, Global), level information, and badges.
        """
        user = await db["users"].find_one({"_id": ObjectId(user_id)})
        if not user:
            return {
                "points": 0,
                "weekly_points": 0,
                "monthly_points": 0,
                "level": 1,
                "xp_in_level": 0,
                "badges": []
            }

        global_points = user.get("points", 0)
        badges = user.get("badges", [])

        # Calculate Level (XP per level progression)
        level = math.floor(global_points / cls.POINTS_PER_LEVEL) + 1
        xp_in_level = global_points % cls.POINTS_PER_LEVEL

        # Calculate Weekly and Monthly points from transaction logs
        week_start = cls.get_week_start()
        month_start = cls.get_month_start()

        # Query weekly logs
        weekly_cursor = db["points_logs"].find({
            "user_id": ObjectId(user_id),
            "timestamp": {"$gte": week_start}
        })
        weekly_logs = await weekly_cursor.to_list(length=1000)
        weekly_points = sum(log.get("points", 0) for log in weekly_logs)

        # Query monthly logs
        monthly_cursor = db["points_logs"].find({
            "user_id": ObjectId(user_id),
            "timestamp": {"$gte": month_start}
        })
        monthly_logs = await monthly_cursor.to_list(length=1000)
        monthly_points = sum(log.get("points", 0) for log in monthly_logs)

        return {
            "points": global_points,
            "weekly_points": weekly_points,
            "monthly_points": monthly_points,
            "level": level,
            "xp_in_level": xp_in_level,
            "badges": badges
        }

    @classmethod
    async def sync_user_to_leaderboard(cls, user_id: str, db: Any) -> None:
        """Calculates current user parameters and saves/upserts to the leaderboard collection."""
        user = await db["users"].find_one({"_id": ObjectId(user_id)})
        if not user:
            return
        
        # Calculate monthly CO2
        start_of_month = cls.get_month_start()
        cursor = db["footprint_logs"].find({
            "user_id": ObjectId(user_id),
            "date": {"$gte": start_of_month}
        })
        logs = await cursor.to_list(length=500)
        monthly_co2 = sum(log.get("total_co2_kg", 0.0) for log in logs)

        global_points = user.get("points", 0)
        badges = user.get("badges", [])
        level_num = math.floor(global_points / cls.POINTS_PER_LEVEL) + 1
        level_name = badges[-1] if badges else f"Level {level_num} Eco-Pioneer"

        await db["leaderboard"].update_one(
            {"user_id": ObjectId(user_id)},
            {
                "$set": {
                    "username": user.get("full_name", "EcoPilot User"),
                    "level_name": level_name,
                    "points": global_points,
                    "monthly_co2_kg": round(monthly_co2, 2),
                    "updated_at": datetime.now(timezone.utc)
                }
            },
            upsert=True
        )

    @classmethod
    async def get_leaderboard(cls, period: str, db: Any, current_user_id: str = None) -> List[Dict[str, Any]]:
        """
        Retrieves leaderboard rankings from the leaderboard collection in MongoDB.
        """
        # Fetch entries from leaderboard collection
        cursor = db["leaderboard"].find({})
        entries = await cursor.to_list(length=100)

        # If leaderboard collection is completely empty, run sync for all existing users
        if not entries:
            users_cursor = db["users"].find({})
            users = await users_cursor.to_list(length=100)
            for u in users:
                try:
                    await cls.sync_user_to_leaderboard(str(u["_id"]), db)
                except Exception as e:
                    logger.error(f"Failed to sync user {u['_id']}: {e}")
            cursor = db["leaderboard"].find({})
            entries = await cursor.to_list(length=100)

        # Sort based on period
        if period == "monthly":
            # Monthly leaderboard sorted by monthly_co2_kg ascending (lower emissions rank 1)
            entries.sort(key=lambda x: x.get("monthly_co2_kg", 999999.0))
            leaderboard_data = []
            for idx, entry in enumerate(entries):
                leaderboard_data.append({
                    "rank": idx + 1,
                    "user_id": str(entry["user_id"]),
                    "name": entry.get("username", "EcoPilot User"),
                    "level": entry.get("level_name", "Eco-Pioneer"),
                    "points": entry.get("points", 0),
                    "monthly_co2_kg": entry.get("monthly_co2_kg", 0.0),
                    "isMe": str(entry["user_id"]) == str(current_user_id) if current_user_id else False
                })
        elif period == "weekly":
            # Sort weekly by points earned in the current week
            week_start = cls.get_week_start()
            logs_cursor = db["points_logs"].find({"timestamp": {"$gte": week_start}})
            period_logs = await logs_cursor.to_list(length=5000)
            
            user_points_map = {}
            for log in period_logs:
                uid_str = str(log["user_id"])
                user_points_map[uid_str] = user_points_map.get(uid_str, 0) + log.get("points", 0)
                
            entries.sort(key=lambda x: user_points_map.get(str(x["user_id"]), 0), reverse=True)
            
            leaderboard_data = []
            for idx, entry in enumerate(entries):
                uid_str = str(entry["user_id"])
                leaderboard_data.append({
                    "rank": idx + 1,
                    "user_id": uid_str,
                    "name": entry.get("username", "EcoPilot User"),
                    "level": entry.get("level_name", "Eco-Pioneer"),
                    "points": user_points_map.get(uid_str, 0),
                    "monthly_co2_kg": entry.get("monthly_co2_kg", 0.0),
                    "isMe": uid_str == str(current_user_id) if current_user_id else False
                })
        else: # global
            entries.sort(key=lambda x: x.get("points", 0), reverse=True)
            leaderboard_data = []
            for idx, entry in enumerate(entries):
                leaderboard_data.append({
                    "rank": idx + 1,
                    "user_id": str(entry["user_id"]),
                    "name": entry.get("username", "EcoPilot User"),
                    "level": entry.get("level_name", "Eco-Pioneer"),
                    "points": entry.get("points", 0),
                    "monthly_co2_kg": entry.get("monthly_co2_kg", 0.0),
                    "isMe": str(entry["user_id"]) == str(current_user_id) if current_user_id else False
                })

        # Ensure we return at least a default list if there's no data
        if not leaderboard_data:
            leaderboard_data = [
                {"rank": 1, "user_id": "dummy_1", "name": "Marcus Aurelius", "level": "Carbon Neutral Hero", "points": 180, "isMe": False},
                {"rank": 2, "user_id": "dummy_2", "name": "Clara Schumann", "level": "Eco Warrior", "points": 120, "isMe": False},
                {"rank": 3, "user_id": "dummy_3", "name": "Ada Lovelace", "level": "Eco Warrior", "points": 90, "isMe": False}
            ]

        return leaderboard_data
