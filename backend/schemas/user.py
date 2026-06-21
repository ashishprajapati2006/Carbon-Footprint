from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from .base import PyObjectId


class ProfileSchema(BaseModel):
    country: str = "US"
    diet_preference: str = "omnivore"
    household_size: int = 1
    has_car: bool = False


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str
    profile: Optional[ProfileSchema] = Field(default_factory=ProfileSchema)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: PyObjectId = Field(alias="_id")
    email: EmailStr
    full_name: str
    profile: ProfileSchema
    created_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    full_name: Optional[str] = None


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6)
