from fastapi import APIRouter, Depends, status
from typing import Any

from core.database import get_db
from core.security import get_current_user, rate_limit_auth
from schemas.user import (
    UserRegister, 
    UserLogin, 
    UserResponse, 
    TokenResponse, 
    TokenRefreshRequest,
    PasswordResetRequest,
    PasswordResetConfirm
)
from controllers.auth import AuthController

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(rate_limit_auth)])
async def register(user_data: UserRegister, db: Any = Depends(get_db)):
    """Registers a new user and issues a JWT access and database refresh token."""
    return await AuthController.register(user_data, db)

@router.post("/login", response_model=TokenResponse, dependencies=[Depends(rate_limit_auth)])
async def login(credentials: UserLogin, db: Any = Depends(get_db)):
    """Authenticates credentials and issues rotated token pairs."""
    return await AuthController.login(credentials, db)

@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(payload: TokenRefreshRequest, db: Any = Depends(get_db)):
    """Rotates refresh tokens and issues fresh access tokens if valid."""
    return await AuthController.refresh_tokens(payload, db)

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(payload: TokenRefreshRequest, db: Any = Depends(get_db)):
    """Revokes a refresh token from the database, ending the user session."""
    return await AuthController.logout(payload, db)

@router.post("/password-reset/request", status_code=status.HTTP_200_OK, dependencies=[Depends(rate_limit_auth)])
async def request_password_reset(payload: PasswordResetRequest, db: Any = Depends(get_db)):
    """Generates a password reset token and outputs it to logs."""
    return await AuthController.request_password_reset(payload, db)

@router.post("/password-reset/confirm", status_code=status.HTTP_200_OK)
async def confirm_password_reset(payload: PasswordResetConfirm, db: Any = Depends(get_db)):
    """Validates the reset token and updates the user's password."""
    return await AuthController.confirm_password_reset(payload, db)

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Returns profile metadata of the authenticated session."""
    current_user["_id"] = str(current_user["_id"])
    return current_user
