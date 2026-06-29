from __future__ import annotations

import configparser
import os
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = ROOT_DIR / "config" / "app.conf"
DEMO_TODAY = "2026-06-18"


def load_dotenv() -> None:
    """Load a tiny .env subset without adding a runtime dependency."""
    env_path = ROOT_DIR / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_dotenv()


def _resolve_path(raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    if path.is_absolute():
        return path
    return ROOT_DIR / path


def _read_config() -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    parser.read(CONFIG_FILE, encoding="utf-8")
    return parser


def _as_bool(value: str | bool | None, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off", ""}:
        return False
    return default


def _as_int(value: str | None, default: int) -> int:
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _config_value(
    section: str,
    option: str,
    default: str,
    env_names: tuple[str, ...] = (),
) -> str:
    for env_name in env_names:
        if env_name in os.environ:
            return os.environ[env_name]
    if CONFIG.has_option(section, option):
        return CONFIG.get(section, option)
    return default


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def relative_to_root(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT_DIR))
    except ValueError:
        return str(path)


CONFIG_FILE = _resolve_path(os.getenv("APP_CONFIG_FILE", str(DEFAULT_CONFIG_PATH)))
CONFIG = _read_config()

APP_NAME = _config_value("app", "name", "DB Sentinel Agent", ("APP_NAME",))
APP_PUBLIC_URL = _config_value(
    "app",
    "public_url",
    "http://127.0.0.1:5173",
    ("APP_PUBLIC_URL",),
)

FRONTEND_HOST = _config_value("frontend", "host", "127.0.0.1", ("FRONTEND_HOST",))
FRONTEND_PORT = _as_int(
    _config_value("frontend", "port", "5173", ("FRONTEND_PORT",)),
    5173,
)
FRONTEND_API_BASE_URL = _config_value(
    "frontend",
    "api_base_url",
    "",
    ("VITE_API_BASE_URL", "FRONTEND_API_BASE_URL"),
).strip()
FRONTEND_RUNTIME_CONFIG_PATH = _resolve_path(
    _config_value(
        "frontend",
        "runtime_config_path",
        "public/runtime-config.js",
        ("FRONTEND_RUNTIME_CONFIG_PATH",),
    )
)

BACKEND_HOST = _config_value("backend", "host", "127.0.0.1", ("BACKEND_HOST",))
BACKEND_PORT = _as_int(
    _config_value("backend", "port", "8000", ("BACKEND_PORT",)),
    8000,
)
CORS_ORIGINS = _csv(
    _config_value(
        "backend",
        "cors_origins",
        "http://127.0.0.1:5173,http://localhost:5173",
        ("CORS_ORIGINS",),
    )
)

DB_PATH = _resolve_path(
    _config_value(
        "database",
        "path",
        "backend/data/db_sentinel_demo.sqlite3",
        ("DB_PATH",),
    )
)
DATA_DIR = DB_PATH.parent
DEMO_RESET_ENABLED = _as_bool(
    _config_value("database", "reset_enabled", "false", ("ENABLE_DEMO_RESET",)),
    False,
)

OPENAI_BASE_URL = _config_value(
    "llm",
    "openai_base_url",
    "https://api.openai.com/v1",
    ("OPENAI_BASE_URL",),
)
OPENAI_MODEL = _config_value("llm", "openai_model", "", ("OPENAI_MODEL",))


def public_runtime_config() -> dict[str, Any]:
    api_base_url = FRONTEND_API_BASE_URL or ""
    return {
        "appName": APP_NAME,
        "publicUrl": APP_PUBLIC_URL,
        "apiBaseUrl": api_base_url,
        "apiDisplay": api_base_url or "same-origin /api",
        "configFile": relative_to_root(CONFIG_FILE),
        "backend": {
            "host": BACKEND_HOST,
            "port": BACKEND_PORT,
        },
        "database": {
            "name": DB_PATH.name,
            "path": relative_to_root(DB_PATH),
            "mode": "readonly",
            "resetEnabled": DEMO_RESET_ENABLED,
        },
    }
