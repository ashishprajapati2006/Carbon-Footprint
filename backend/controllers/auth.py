from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from bson import ObjectId

from core.security import (
    get_password_hash, 
    verify_password, 
    create_access_token, 
    create_refresh_token
)
from repositories.user import UserRepository
from schemas.user import UserRegister, UserLogin, TokenResponse, TokenRefreshRequest, PasswordResetRequest, PasswordResetConfirm

class AuthController:
    @staticmethod
    async def register(user_data: UserRegister, db) -> TokenResponse:
        repo = UserRepository(db)
        existing_user = await repo.get_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address is already registered."
            )

        user_dict = user_data.model_dump()
        user_dict["password_hash"] = get_password_hash(user_dict.pop("password"))
        user_dict["created_at"] = datetime.now(timezone.utc)

        user_id = await repo.create(user_dict)

        access_token = create_access_token(data={"sub": user_data.email})
        refresh_token = create_refresh_token()

        expire_at = datetime.now(timezone.utc) + timedelta(days=30)
        await repo.create_refresh_token(refresh_token, user_id, expire_at)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token
        )

    @staticmethod
    async def login(credentials: UserLogin, db) -> TokenResponse:
        repo = UserRepository(db)
        user = await repo.get_by_email(credentials.email)
        if not user or not verify_password(credentials.password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password credentials."
            )

        user_id = str(user["_id"])

        access_token = create_access_token(data={"sub": user["email"]})
        refresh_token = create_refresh_token()

        expire_at = datetime.now(timezone.utc) + timedelta(days=30)
        await repo.create_refresh_token(refresh_token, user_id, expire_at)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token
        )

    @staticmethod
    async def refresh_tokens(payload: TokenRefreshRequest, db) -> TokenResponse:
        repo = UserRepository(db)
        db_token = await repo.get_refresh_token(payload.refresh_token)
        if not db_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked refresh token."
            )

        expires_at = db_token["expires_at"]
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if datetime.now(timezone.utc) > expires_at:
            await repo.delete_refresh_token(payload.refresh_token)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired."
            )

        user = await repo.get_by_id(str(db_token["user_id"]))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User associated with token not found."
            )

        await repo.delete_refresh_token(payload.refresh_token)

        new_access = create_access_token(data={"sub": user["email"]})
        new_refresh = create_refresh_token()

        expire_at = datetime.now(timezone.utc) + timedelta(days=30)
        await repo.create_refresh_token(new_refresh, str(user["_id"]), expire_at)

        return TokenResponse(
            access_token=new_access,
            refresh_token=new_refresh
        )

    @staticmethod
    async def logout(payload: TokenRefreshRequest, db) -> dict:
        repo = UserRepository(db)
        deleted = await repo.delete_refresh_token(payload.refresh_token)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token was already revoked or is invalid."
            )
        return {"message": "Successfully logged out."}

    @staticmethod
    async def request_password_reset(payload: PasswordResetRequest, db) -> dict:
        repo = UserRepository(db)
        user = await repo.get_by_email(payload.email)
        if not user:
            return {"message": "If the email is registered, a reset link will be sent."}

        reset_token = create_refresh_token()
        expire_at = datetime.now(timezone.utc) + timedelta(minutes=15)

        await repo.create_password_reset(reset_token, payload.email, expire_at)

        print(f"\n[SMTP MOCK] Password Reset Request for {payload.email}:")
        print(f"  Token: {reset_token}")
        print(f"  Expiration: {expire_at.isoformat()}\n")

        return {"message": "If the email is registered, a reset link will be sent."}

    @staticmethod
    async def confirm_password_reset(payload: PasswordResetConfirm, db) -> dict:
        repo = UserRepository(db)
        db_reset = await repo.get_password_reset(payload.token)
        if not db_reset:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token."
            )

        expires_at = db_reset["expires_at"]
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if datetime.now(timezone.utc) > expires_at:
            await repo.delete_password_reset(payload.token)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired."
            )

        hashed_pwd = get_password_hash(payload.new_password)
        await repo.update_password(db_reset["email"], hashed_pwd)
        await repo.delete_password_reset(payload.token)

        user = await repo.get_by_email(db_reset["email"])
        if user:
            await repo.delete_all_refresh_tokens(str(user["_id"]))

        return {"message": "Password updated successfully."}
