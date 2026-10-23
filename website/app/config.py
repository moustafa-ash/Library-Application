import os
from pathlib import Path

from dotenv import dotenv_values


def load_config():
    values = {**dotenv_values(Path(__file__).resolve().parents[1] / ".env"), **os.environ}
    return {
        "SECRET_KEY": values.get("SECRET_KEY"),
        "DB_HOST": values.get("DB_HOST", "localhost"),
        "DB_PORT": values.get("DB_PORT", "3306"),
        "DB_USER": values.get("DB_USER"),
        "DB_PASSWORD": values.get("DB_PASSWORD", ""),
        "DB_NAME": values.get("DB_NAME", "library"),
        "AUTH_DB_NAME": values.get("AUTH_DB_NAME", "registration"),
        "SESSION_TYPE": "cachelib",
        "SESSION_PERMANENT": False,
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": values.get("SESSION_COOKIE_SECURE", "false").lower() == "true",
    }


def validate_config(config):
    for key in ("SECRET_KEY", "DB_HOST", "DB_USER", "DB_NAME", "AUTH_DB_NAME"):
        value = config.get(key)
        if not value or str(value).startswith("replace_with_"):
            raise ValueError(f"Set {key} in website/.env before starting the application.")
    try:
        port = int(config["DB_PORT"])
    except (TypeError, ValueError):
        raise ValueError("DB_PORT must be an integer between 1 and 65535.") from None
    if not 1 <= port <= 65535:
        raise ValueError("DB_PORT must be an integer between 1 and 65535.")
    config["DB_PORT"] = port
