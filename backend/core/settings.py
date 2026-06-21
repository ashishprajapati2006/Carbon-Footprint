import os
from enum import Enum
from typing import Any
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvironmentType(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class Settings(BaseSettings):
    # MongoDB
    mongodb_uri: str = Field("mongodb://localhost:27017/ecopilot", alias="MONGODB_URI")

    # JWT
    jwt_secret: str = Field("default_fallback_secret_key_change_me", alias="JWT_SECRET")
    jwt_algorithm: str = Field("HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(1440, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    # Gemini
    gemini_api_key: str = Field("dummy_api_key", alias="GEMINI_API_KEY")

    # Frontend & Backend
    next_public_api_url: str = Field("http://localhost:3000", alias="NEXT_PUBLIC_API_URL")
    backend_url: str = Field("http://localhost:8000", alias="BACKEND_URL")

    # Google Vision
    google_application_credentials: str = Field("dummy_path.json", alias="GOOGLE_APPLICATION_CREDENTIALS")

    # Email
    email_host: str = Field("smtp.gmail.com", alias="EMAIL_HOST")
    email_port: int = Field(587, alias="EMAIL_PORT")
    email_user: str = Field("user@example.com", alias="EMAIL_USER")
    email_password: str = Field("password", alias="EMAIL_PASSWORD")

    # Uploads
    max_upload_size: int = Field(10485760, alias="MAX_UPLOAD_SIZE")

    # Environment
    environment: EnvironmentType = Field(EnvironmentType.DEVELOPMENT, alias="ENVIRONMENT")

    # Pydantic settings config mapping
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # Validators
    @field_validator("mongodb_uri")
    @classmethod
    def validate_mongodb_uri(cls, v: str) -> str:
        # Allow empty or dummy for development testing fallback
        if v == "dummy" or not v:
            return v
        if not (v.startswith("mongodb://") or v.startswith("mongodb+srv://")):
            raise ValueError(
                "MONGODB_URI must start with 'mongodb://' or 'mongodb+srv://'"
            )
        return v

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("JWT_SECRET cannot be empty or whitespace-only")
        return v

    @field_validator("jwt_algorithm")
    @classmethod
    def validate_jwt_algorithm(cls, v: str) -> str:
        valid_algorithms = {"HS256", "HS384", "HS512", "RS256", "RS384", "RS512"}
        if v not in valid_algorithms:
            raise ValueError(f"JWT_ALGORITHM must be one of {valid_algorithms}")
        return v

    @field_validator("access_token_expire_minutes")
    @classmethod
    def validate_token_expire(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be a positive integer")
        return v

    @field_validator("gemini_api_key")
    @classmethod
    def validate_gemini_api_key(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("GEMINI_API_KEY cannot be empty")
        return v.strip()

    @field_validator("next_public_api_url", "backend_url")
    @classmethod
    def validate_urls(cls, v: str, info: Any) -> str:
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError(f"{info.field_name.upper()} must start with 'http://' or 'https://'")
        return v

    @field_validator("email_port")
    @classmethod
    def validate_email_port(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError("EMAIL_PORT must be between 1 and 65535")
        return v

    @field_validator("max_upload_size")
    @classmethod
    def validate_max_upload_size(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("MAX_UPLOAD_SIZE must be greater than 0")
        return v
