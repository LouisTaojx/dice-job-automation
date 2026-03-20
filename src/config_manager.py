from __future__ import annotations

from pathlib import Path
import re
import runpy
from typing import Any

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.py"

DEFAULT_CREDENTIALS = {
    "username": "your_email@example.com",
    "password": "your_password",
}

DEFAULT_SEARCH_SETTINGS = {
    "keyword": "Data Engineer",
    "keywords": ["Data Engineer"],
    "max_applications": 10,
}

def get_config_path() -> Path:
    return CONFIG_PATH


def _coerce_mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _normalize_max_applications(value: Any) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return DEFAULT_SEARCH_SETTINGS["max_applications"]

    return normalized if normalized > 0 else DEFAULT_SEARCH_SETTINGS["max_applications"]


def normalize_keywords(value: Any) -> list[str]:
    if isinstance(value, str):
        raw_keywords = re.split(r"[\r\n,]+", value)
    elif isinstance(value, (list, tuple, set)):
        raw_keywords = list(value)
    elif value is None:
        raw_keywords = []
    else:
        raw_keywords = [value]

    keywords: list[str] = []
    for item in raw_keywords:
        normalized = " ".join(str(item).split()).strip()
        if normalized:
            keywords.append(normalized)

    return keywords


def render_config(
    credentials: dict[str, Any],
    search_settings: dict[str, Any],
) -> str:
    username = str(credentials.get("username", ""))
    password = str(credentials.get("password", ""))
    keywords = normalize_keywords(
        search_settings.get("keywords", search_settings.get("keyword", ""))
    ) or list(DEFAULT_SEARCH_SETTINGS["keywords"])
    keyword = keywords[0]
    max_applications = _normalize_max_applications(search_settings.get("max_applications"))

    return (
        "CREDENTIALS = {\n"
        f"    \"username\": {username!r},\n"
        f"    \"password\": {password!r}\n"
        "}\n\n"
        "SEARCH_SETTINGS = {\n"
        f"    \"keyword\": {keyword!r},\n"
        f"    \"keywords\": {keywords!r},\n"
        f"    \"max_applications\": {max_applications}\n"
        "}\n"
    )


def save_config(
    credentials: dict[str, Any],
    search_settings: dict[str, Any],
) -> Path:
    CONFIG_PATH.write_text(
        render_config(credentials, search_settings),
        encoding="utf-8",
    )
    return CONFIG_PATH


def load_config() -> dict[str, dict[str, Any]]:
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CREDENTIALS, DEFAULT_SEARCH_SETTINGS)

    namespace = runpy.run_path(str(CONFIG_PATH))
    credentials = {**DEFAULT_CREDENTIALS, **_coerce_mapping(namespace.get("CREDENTIALS"))}
    search_settings = {**DEFAULT_SEARCH_SETTINGS, **_coerce_mapping(namespace.get("SEARCH_SETTINGS"))}
    keywords = normalize_keywords(
        search_settings.get("keywords", search_settings.get("keyword"))
    ) or list(DEFAULT_SEARCH_SETTINGS["keywords"])
    search_settings["keywords"] = keywords
    search_settings["keyword"] = keywords[0]
    search_settings["max_applications"] = _normalize_max_applications(
        search_settings.get("max_applications")
    )

    return {
        "credentials": credentials,
        "search_settings": search_settings,
    }
