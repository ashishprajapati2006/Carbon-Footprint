import logging
import math
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from bson import ObjectId

from repositories.user import UserRepository
from repositories.gamification import GamificationRepository
from repositories.footprint import FootprintRepository

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
        start = now - timedelta(days=now.weekday())
        return start.replace(hour=0, minute=0, second=0, microsecond=0)

    @staticmethod
    def get_month_start() -> datetime:
        """Returns the start of the current month (1st of current month 00:00:00 UTC)."""
        now = datetime.now(timezone.utc)
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    @classmethod
    async def award_points(cls, user_id: str, action: str, db: Any) -> Dict[str, Any]:
        """Awards points to a user for a given action using repositories."""
        points = ACTION_POINTS.get(action, 0)
        if points == 0:
            logger.warning(f"Attempted to award points for unrecognized action: {action}")
            return {"awarded": 0, "total": 0, "badges_unlocked": []}

        # 1. Log the points transaction
        gam_repo = GamificationRepository(db)
        log_entry = {
            "user_id": ObjectId(user_id),
            "action": action,
            "points": points,
            "timestamp": datetime.now(timezone.utc)
        }
        await gam_repo.insert_points_log(log_entry)

        # 2. Update user profile and evaluate badge thresholds
        user_repo = UserRepository(db)
        res = await cls._update_user_points_and_badges(user_id, points, user_repo)
        
        # 3. Sync to leaderboard
        try:
            await cls.sync_user_to_leaderboard(user_id, db)
        except Exception as e:
            logger.error(f"Failed to sync user leaderboard stats: {e}")

        logger.info(f"Awarded {points} points to user {user_id} for '{action}'. New badges: {res['badges_unlocked']}")
        return {
            "awarded": points,
            "total_points": res["new_points"],
            "badges_unlocked": res["badges_unlocked"],
            "all_badges": res["new_badges"]
        }

    @classmethod
    async def _update_user_points_and_badges(cls, user_id: str, points: int, user_repo: UserRepository) -> Dict[str, Any]:
        """Helper to fetch user, add points, check badge thresholds, and update."""
        user = await user_repo.get_by_id(user_id)
        if not user:
            logger.error(f"User {user_id} not found when awarding points.")
            return {"new_points": points, "badges_unlocked": [], "new_badges": []}

        current_points = user.get("points", 0)
        current_badges = user.get("badges", [])
        new_points = current_points + points
        new_badges = list(current_badges)

        unlocked_new_badges = []
        for badge_def in BADGE_THRESHOLDS:
            badge_name = badge_def["name"]
            if new_points >= badge_def["points"] and badge_name not in new_badges:
                new_badges.append(badge_name)
                unlocked_new_badges.append(badge_name)

        await user_repo.update_points_and_badges(user_id, new_points, new_badges)
        return {
            "new_points": new_points,
            "badges_unlocked": unlocked_new_badges,
            "new_badges": new_badges
        }

    @classmethod
    async def get_user_stats(cls, user_id: str, db: Any) -> Dict[str, Any]:
        """Retrieves user points and level progression info via repositories."""
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(user_id)
        if not user:
            return {"points": 0, "weekly_points": 0, "monthly_points": 0, "level": 1, "xp_in_level": 0, "badges": []}

        global_points = user.get("points", 0)
        badges = user.get("badges", [])
        level = math.floor(global_points / cls.POINTS_PER_LEVEL) + 1
        xp_in_level = global_points % cls.POINTS_PER_LEVEL

        # Calculate Weekly and Monthly points from transaction logs
        gam_repo = GamificationRepository(db)
        weekly_points = await cls._calculate_time_range_points(user_id, cls.get_week_start(), gam_repo)
        monthly_points = await cls._calculate_time_range_points(user_id, cls.get_month_start(), gam_repo)

        return {
            "points": global_points,
            "weekly_points": weekly_points,
            "monthly_points": monthly_points,
            "level": level,
            "xp_in_level": xp_in_level,
            "badges": badges
        }

    @staticmethod
    async def _calculate_time_range_points(user_id: str, start_date: datetime, gam_repo: GamificationRepository) -> int:
        """Helper to sum points earned by a user since a start date."""
        logs = await gam_repo.get_points_logs_by_range(user_id, start_date)
        return sum(log.get("points", 0) for log in logs)

    @classmethod
    async def sync_user_to_leaderboard(cls, user_id: str, db: Any) -> None:
        """Calculates current user parameters and saves/upserts to the leaderboard collection."""
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(user_id)
        if not user:
            return
        
        foot_repo = FootprintRepository(db)
        monthly_co2 = await cls._calculate_monthly_emissions(user_id, foot_repo)

        global_points = user.get("points", 0)
        badges = user.get("badges", [])
        level_num = math.floor(global_points / cls.POINTS_PER_LEVEL) + 1
        level_name = badges[-1] if badges else f"Level {level_num} Eco-Pioneer"

        gam_repo = GamificationRepository(db)
        await gam_repo.update_leaderboard_entry(
            user_id=user_id,
            username=user.get("full_name", "EcoPilot User"),
            level_name=level_name,
            points=global_points,
            monthly_co2=round(monthly_co2, 2)
        )

    @staticmethod
    async def _calculate_monthly_emissions(user_id: str, foot_repo: FootprintRepository) -> float:
        """Helper to calculate total carbon emissions for the current month."""
        start_of_month = GamificationService.get_month_start()
        logs = await foot_repo.get_footprints_by_range(user_id, start_of_month)
        return sum(log.get("total_co2_kg", 0.0) for log in logs)

    @classmethod
    async def get_leaderboard(cls, period: str, db: Any, current_user_id: str = None) -> List[Dict[str, Any]]:
        """Retrieves leaderboard rankings from the leaderboard collection in MongoDB."""
        gam_repo = GamificationRepository(db)
        entries = await gam_repo.get_all_leaderboard_entries(100)

        # Sync leaderboard if empty
        if not entries:
            user_repo = UserRepository(db)
            cursor = user_repo.db["users"].find({}) # simple user find
            users = await cursor.to_list(length=100)
            for u in users:
                try:
                    await cls.sync_user_to_leaderboard(str(u["_id"]), db)
                except Exception as e:
                    logger.error(f"Failed to sync user {u['_id']}: {e}")
            entries = await gam_repo.get_all_leaderboard_entries(100)

        if period == "monthly":
            return cls._get_monthly_leaderboard(entries, current_user_id)
        elif period == "weekly":
            return await cls._get_weekly_leaderboard(entries, current_user_id, gam_repo)
        else:
            return cls._get_global_leaderboard(entries, current_user_id)

    @staticmethod
    def _get_monthly_leaderboard(entries: list, current_user_id: str = None) -> List[Dict[str, Any]]:
        """Sorts and formats monthly leaderboard rankings (lowest emissions first)."""
        sorted_entries = list(entries)
        sorted_entries.sort(key=lambda x: x.get("monthly_co2_kg", 999999.0))
        return [
            {
                "rank": idx + 1,
                "user_id": str(entry["user_id"]),
                "name": entry.get("username", "EcoPilot User"),
                "level": entry.get("level_name", "Eco-Pioneer"),
                "points": entry.get("points", 0),
                "monthly_co2_kg": entry.get("monthly_co2_kg", 0.0),
                "isMe": str(entry["user_id"]) == str(current_user_id) if current_user_id else False
            }
            for idx, entry in enumerate(sorted_entries)
        ]

    @classmethod
    async def _get_weekly_leaderboard(cls, entries: list, current_user_id: str, gam_repo: GamificationRepository) -> List[Dict[str, Any]]:
        """Sorts and formats weekly leaderboard rankings (highest points earned this week first)."""
        week_start = cls.get_week_start()
        logs = await gam_repo.get_points_logs_since(week_start)
        
        user_points_map = {}
        for log in logs:
            uid_str = str(log["user_id"])
            user_points_map[uid_str] = user_points_map.get(uid_str, 0) + log.get("points", 0)
            
        sorted_entries = list(entries)
        sorted_entries.sort(key=lambda x: user_points_map.get(str(x["user_id"]), 0), reverse=True)
        return [
            {
                "rank": idx + 1,
                "user_id": str(entry["user_id"]),
                "name": entry.get("username", "EcoPilot User"),
                "level": entry.get("level_name", "Eco-Pioneer"),
                "points": user_points_map.get(str(entry["user_id"]), 0),
                "monthly_co2_kg": entry.get("monthly_co2_kg", 0.0),
                "isMe": str(entry["user_id"]) == str(current_user_id) if current_user_id else False
            }
            for idx, entry in enumerate(sorted_entries)
        ]

    @staticmethod
    def _get_global_leaderboard(entries: list, current_user_id: str = None) -> List[Dict[str, Any]]:
        """Sorts and formats global leaderboard rankings (highest points first)."""
        sorted_entries = list(entries)
        sorted_entries.sort(key=lambda x: x.get("points", 0), reverse=True)
        leaderboard_data = [
            {
                "rank": idx + 1,
                "user_id": str(entry["user_id"]),
                "name": entry.get("username", "EcoPilot User"),
                "level": entry.get("level_name", "Eco-Pioneer"),
                "points": entry.get("points", 0),
                "monthly_co2_kg": entry.get("monthly_co2_kg", 0.0),
                "isMe": str(entry["user_id"]) == str(current_user_id) if current_user_id else False
            }
            for idx, entry in enumerate(sorted_entries)
        ]
        
        if not leaderboard_data:
            return [
                {"rank": 1, "user_id": "dummy_1", "name": "Marcus Aurelius", "level": "Carbon Neutral Hero", "points": 180, "isMe": False},
                {"rank": 2, "user_id": "dummy_2", "name": "Clara Schumann", "level": "Eco Warrior", "points": 120, "isMe": False},
                {"rank": 3, "user_id": "dummy_3", "name": "Ada Lovelace", "level": "Eco Warrior", "points": 90, "isMe": False}
            ]
        return leaderboard_data
