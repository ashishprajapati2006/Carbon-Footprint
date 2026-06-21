import sys
from functools import lru_cache
from pydantic import ValidationError
from .settings import Settings


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached instance of the Settings class.
    Reads variables from environment or a local .env file.
    """
    try:
        return Settings()
    except ValidationError as e:
        print("\n=== ENVIRONMENT CONFIGURATION ERROR ===", file=sys.stderr)
        print("One or more environment variables failed validation:\n", file=sys.stderr)
        for error in e.errors():
            loc_path = " -> ".join(str(loc) for loc in error.get("loc", []))
            msg = error.get("msg")
            print(f"  ❌ \033[91m{loc_path}\033[0m: {msg}", file=sys.stderr)
        print("\n========================================\n", file=sys.stderr)
        raise e


# Instantiate globally so import config validates immediately
settings = get_settings()
