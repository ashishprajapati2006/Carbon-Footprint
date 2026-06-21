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
    async def award_points(cls, user_id: str, action: str, db) -> Dict[str, Any]:
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

        logger.info(f"Awarded {points} points to user {user_id} for '{action}'. Total: {new_points}. New badges: {unlocked_new_badges}")
        return {
            "awarded": points,
            "total_points": new_points,
            "badges_unlocked": unlocked_new_badges,
            "all_badges": new_badges
        }

    @classmethod
    async def get_user_stats(cls, user_id: str, db) -> Dict[str, Any]:
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

        # Calculate Level (200 XP per level progression)
        level = math.floor(global_points / 200) + 1
        xp_in_level = global_points % 200

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
    async def get_leaderboard(cls, period: str, db, current_user_id: str = None) -> List[Dict[str, Any]]:
        """
        Computes leaderboard rankings for the specified period ('weekly', 'monthly', 'global').
        """
        # 1. Fetch all users
        users_cursor = db["users"].find({})
        users = await users_cursor.to_list(length=100)

        user_scores = []

        if period == "global":
            for u in users:
                user_scores.append({
                    "user_id": str(u["_id"]),
                    "name": u.get("full_name", "EcoPilot User"),
                    "points": u.get("points", 0),
                    "badges": u.get("badges", [])
                })
        else:
            # Filter logs based on period
            start_date = cls.get_week_start() if period == "weekly" else cls.get_month_start()
            
            # Retrieve all logs in the period
            logs_cursor = db["points_logs"].find({
                "timestamp": {"$gte": start_date}
            })
            period_logs = await logs_cursor.to_list(length=5000)

            # Sum points per user
            user_points_map = {}
            for log in period_logs:
                uid_str = str(log["user_id"])
                user_points_map[uid_str] = user_points_map.get(uid_str, 0) + log.get("points", 0)

            for u in users:
                uid_str = str(u["_id"])
                user_scores.append({
                    "user_id": uid_str,
                    "name": u.get("full_name", "EcoPilot User"),
                    "points": user_points_map.get(uid_str, 0),
                    "badges": u.get("badges", [])
                })

        # Sort descending by points
        user_scores.sort(key=lambda x: x["points"], reverse=True)

        # Format output standings
        leaderboard_data = []
        for idx, entry in enumerate(user_scores):
            points = entry["points"]
            level_num = math.floor(points / 200) + 1
            
            # Map top badges or standard naming as Standing Level
            badges = entry["badges"]
            if badges:
                level_name = badges[-1]  # Highest unlocked badge
            else:
                level_name = f"Level {level_num} Eco-Pioneer"

            leaderboard_data.append({
                "rank": idx + 1,
                "user_id": entry["user_id"],
                "name": entry["name"],
                "level": level_name,
                "points": points,
                "isMe": entry["user_id"] == str(current_user_id) if current_user_id else False
            })

        # Ensure we return at least a default list if there's no data
        if not leaderboard_data:
            leaderboard_data = [
                {"rank": 1, "user_id": "dummy_1", "name": "Marcus Aurelius", "level": "Carbon Neutral Hero", "points": 180, "isMe": False},
                {"rank": 2, "user_id": "dummy_2", "name": "Clara Schumann", "level": "Eco Warrior", "points": 120, "isMe": False},
                {"rank": 3, "user_id": "dummy_3", "name": "Ada Lovelace", "level": "Eco Warrior", "points": 90, "isMe": False}
            ]

        return leaderboard_data
