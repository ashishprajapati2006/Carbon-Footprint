from fastapi import APIRouter, Depends, Query, status
from typing import Any, List

from core.database import get_db
from core.security import get_current_user
from controllers.gamification import GamificationController
from schemas.leaderboard import UserStatsResponse, LeaderboardResponse
from schemas.challenge import ChallengeResponse, ChallengeClaimResponse

router = APIRouter(prefix="/gamification", tags=["Gamification Engine"])

@router.get("/stats", response_model=UserStatsResponse)
async def get_user_stats(
    db: Any = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Retrieves points (Weekly, Monthly, Global), level progress, and badges for the current user."""
    return await GamificationController.get_user_stats(db, current_user)

@router.get("/leaderboard", response_model=List[LeaderboardResponse])
async def get_leaderboard(
    period: str = Query("global", pattern="^(weekly|monthly|global)$"),
    db: Any = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Retrieves leaderboard rankings for the specified period ('weekly', 'monthly', 'global')."""
    return await GamificationController.get_leaderboard(period, db, current_user)

@router.get("/challenges", response_model=List[ChallengeResponse])
async def get_challenges(
    db: Any = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Retrieves user's challenges, initializing defaults if none exist."""
    return await GamificationController.get_challenges(db, current_user)

@router.post("/challenges/{challenge_id}/claim", response_model=ChallengeClaimResponse)
async def claim_challenge(
    challenge_id: str,
    db: Any = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Claims the points for a completed challenge and awards 100 points."""
    return await GamificationController.claim_challenge(challenge_id, db, current_user)
