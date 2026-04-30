import os
from pathlib import Path

from dotenv import load_dotenv


env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

_FILE_PATH = Path(__file__).resolve()
WORKSPACE_ROOT = next((parent for parent in _FILE_PATH.parents if (parent / "Database").exists()), _FILE_PATH.parents[1])
DEFAULT_SQLITE_PATH = WORKSPACE_ROOT / "Database" / "s92.db"
DEFAULT_SECRET_KEY = "CHANGE_ME_IN_PROD"


def get_app_env() -> str:
    return os.getenv("APP_ENV", "development").strip().lower() or "development"


def is_production() -> bool:
    return get_app_env() == "production"


def get_bool_env(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def get_database_url() -> str:
    database_url = (os.getenv("DATABASE_URL") or "").strip()
    if database_url:
        return database_url
    if is_production():
        raise RuntimeError("DATABASE_URL is required when APP_ENV=production.")
    return f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"


def get_allowed_origins() -> list[str]:
    raw_value = os.getenv("ALLOWED_ORIGINS", "")
    return [origin.strip() for origin in raw_value.split(",") if origin.strip()]


def should_auto_create_schema() -> bool:
    return get_bool_env("ENABLE_AUTO_SCHEMA_CREATE", default=not is_production())


def should_seed_rules_on_startup() -> bool:
    return get_bool_env("ENABLE_RULE_SEED_ON_STARTUP", default=not is_production())


def should_enable_news_scheduler() -> bool:
    return get_bool_env("ENABLE_NEWS_SCHEDULER", default=not is_production())


def validate_runtime_config() -> None:
    database_url = get_database_url()
    secret_key = (os.getenv("FINTRIX_SECRET_KEY") or "").strip()
    allowed_origins = get_allowed_origins()

    if not is_production():
        return

    if not secret_key or secret_key == DEFAULT_SECRET_KEY:
        raise RuntimeError("FINTRIX_SECRET_KEY must be set to a strong unique value in production.")

    if database_url.startswith("sqlite"):
        raise RuntimeError("SQLite is not supported for production deployments. Use Supabase Postgres.")

    if not allowed_origins:
        raise RuntimeError("ALLOWED_ORIGINS must be set in production.")
