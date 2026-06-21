from datetime import datetime, timezone
from fastapi import HTTPException, status
from bson import ObjectId

from repositories.gamification import GamificationRepository
from services.gamification_svc import GamificationService

class GamificationController:
    @staticmethod
    async def get_user_stats(db, current_user: dict) -> dict:
        user_id = current_user["id"]
        stats = await GamificationService.get_user_stats(user_id, db)
        return stats

    @staticmethod
    async def get_leaderboard(period: str, db, current_user: dict) -> dict:
        user_id = current_user["id"]
        leaderboard = await GamificationService.get_leaderboard(period, db, current_user_id=user_id)
        return leaderboard

    @staticmethod
    async def get_challenges(db, current_user: dict) -> list:
        user_id = current_user["id"]
        repo = GamificationRepository(db)
        
        challenges = await repo.get_challenges(user_id)
        
        if not challenges:
            default_quests = [
                {
                    "user_id": ObjectId(user_id),
                    "quest_title": "Meatless Commute",
                    "description": "Eat vegetarian or vegan meals for 3 consecutive days.",
                    "xp_yield": 120,
                    "goal_amount": 3,
                    "current_amount": 2,
                    "category": "food",
                    "status": "in_progress",
                    "updated_at": datetime.now(timezone.utc)
                },
                {
                    "user_id": ObjectId(user_id),
                    "quest_title": "Transit Traveler",
                    "description": "Swap driving single commutes for rail or bus travel.",
                    "xp_yield": 150,
                    "goal_amount": 1,
                    "current_amount": 0,
                    "category": "transport",
                    "status": "in_progress",
                    "updated_at": datetime.now(timezone.utc)
                },
                {
                    "user_id": ObjectId(user_id),
                    "quest_title": "Standby Shutdown",
                    "description": "Audit and unplug 5 idle phantom electrical loads.",
                    "xp_yield": 60,
                    "goal_amount": 5,
                    "current_amount": 5,
                    "category": "energy",
                    "status": "completed",
                    "updated_at": datetime.now(timezone.utc)
                },
                {
                    "user_id": ObjectId(user_id),
                    "quest_title": "Refuse Restraint",
                    "description": "Keep household waste below 5kg this week.",
                    "xp_yield": 80,
                    "goal_amount": 1,
                    "current_amount": 1,
                    "category": "waste",
                    "status": "completed",
                    "updated_at": datetime.now(timezone.utc)
                }
            ]
            for quest in default_quests:
                quest_id = await repo.insert_challenge(quest)
                quest["_id"] = quest_id
                
            challenges = default_quests

        # Format ObjectIds and timestamps for JSON output
        formatted_challenges = []
        for ch in challenges:
            status_val = ch.get("status", "in_progress")
            if status_val == "in_progress" and ch.get("current_amount", 0) >= ch.get("goal_amount", 1):
                status_val = "completed"
                
            formatted_challenges.append({
                "id": str(ch["_id"]),
                "user_id": str(ch["user_id"]),
                "quest_title": ch.get("quest_title", ""),
                "description": ch.get("description", ""),
                "xp_yield": ch.get("xp_yield", 50),
                "goal_amount": ch.get("goal_amount", 1),
                "current_amount": ch.get("current_amount", 0),
                "category": ch.get("category", "food"),
                "status": status_val,
                "updated_at": ch.get("updated_at", datetime.now(timezone.utc)).isoformat() if isinstance(ch.get("updated_at"), datetime) else ch.get("updated_at")
            })
            
        return formatted_challenges

    @staticmethod
    async def claim_challenge(challenge_id: str, db, current_user: dict) -> dict:
        user_id = current_user["id"]
        repo = GamificationRepository(db)
        
        # Try fetching challenge
        challenge = await repo.get_challenge_by_id(challenge_id)
        
        if not challenge or challenge["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Challenge not found."
            )
            
        status_val = challenge.get("status", "in_progress")
        current_amt = challenge.get("current_amount", 0)
        goal_amt = challenge.get("goal_amount", 1)
        
        if status_val == "claimed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Challenge reward already claimed."
            )
            
        if status_val == "in_progress" and current_amt < goal_amt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Challenge not yet completed."
            )
            
        # Update to claimed
        await repo.update_challenge(challenge_id, {
            "status": "claimed",
            "updated_at": datetime.now(timezone.utc)
        })
        
        # Award +100 points
        award_res = await GamificationService.award_points(user_id, "challenge_claim", db)
        
        return {
            "message": "Challenge reward claimed successfully!",
            "awarded": award_res["awarded"],
            "total_points": award_res["total_points"],
            "badges_unlocked": award_res["badges_unlocked"]
        }
