from __future__ import annotations

from pathlib import Path
import re
import runpy
from typing import Any

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.py"

DEFAULT_DICE_CREDENTIALS = {
    "username": "your_dice_email@example.com",
    "password": "your_dice_password",
}
DEFAULT_LINKEDIN_CREDENTIALS = {
    "username": "your_linkedin_email@example.com",
    "password": "your_linkedin_password",
}
DEFAULT_CREDENTIALS = dict(DEFAULT_DICE_CREDENTIALS)

DEFAULT_SITE_SETTINGS = {
    "dice_enabled": True,
    "linkedin_enabled": False,
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


def _normalize_credentials(value: Any, defaults: dict[str, str]) -> dict[str, str]:
    mapping = _coerce_mapping(value)
    return {
        "username": str(mapping.get("username", defaults["username"])),
        "password": str(mapping.get("password", defaults["password"])),
    }


def _normalize_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False

    return default


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
    dice_credentials: dict[str, Any],
    linkedin_credentials: dict[str, Any],
    search_settings: dict[str, Any],
    site_settings: dict[str, Any],
) -> str:
    normalized_dice = _normalize_credentials(dice_credentials, DEFAULT_DICE_CREDENTIALS)
    normalized_linkedin = _normalize_credentials(linkedin_credentials, DEFAULT_LINKEDIN_CREDENTIALS)
    keywords = normalize_keywords(
        search_settings.get("keywords", search_settings.get("keyword", ""))
    ) or list(DEFAULT_SEARCH_SETTINGS["keywords"])
    keyword = keywords[0]
    max_applications = _normalize_max_applications(search_settings.get("max_applications"))
    normalized_site_settings = {
        "dice_enabled": _normalize_bool(
            site_settings.get("dice_enabled"),
            DEFAULT_SITE_SETTINGS["dice_enabled"],
        ),
        "linkedin_enabled": _normalize_bool(
            site_settings.get("linkedin_enabled"),
            DEFAULT_SITE_SETTINGS["linkedin_enabled"],
        ),
    }

    return (
        "DICE_CREDENTIALS = {\n"
        f"    \"username\": {normalized_dice['username']!r},\n"
        f"    \"password\": {normalized_dice['password']!r}\n"
        "}\n\n"
        "LINKEDIN_CREDENTIALS = {\n"
        f"    \"username\": {normalized_linkedin['username']!r},\n"
        f"    \"password\": {normalized_linkedin['password']!r}\n"
        "}\n\n"
        "SITE_SETTINGS = {\n"
        f"    \"dice_enabled\": {normalized_site_settings['dice_enabled']!r},\n"
        f"    \"linkedin_enabled\": {normalized_site_settings['linkedin_enabled']!r}\n"
        "}\n\n"
        "SEARCH_SETTINGS = {\n"
        f"    \"keyword\": {keyword!r},\n"
        f"    \"keywords\": {keywords!r},\n"
        f"    \"max_applications\": {max_applications}\n"
        "}\n"
    )


def save_config(
    dice_credentials: dict[str, Any],
    linkedin_credentials: dict[str, Any],
    search_settings: dict[str, Any],
    site_settings: dict[str, Any],
) -> Path:
    CONFIG_PATH.write_text(
        render_config(
            dice_credentials,
            linkedin_credentials,
            search_settings,
            site_settings,
        ),
        encoding="utf-8",
    )
    return CONFIG_PATH


def load_config() -> dict[str, dict[str, Any]]:
    if not CONFIG_PATH.exists():
        save_config(
            DEFAULT_DICE_CREDENTIALS,
            DEFAULT_LINKEDIN_CREDENTIALS,
            DEFAULT_SEARCH_SETTINGS,
            DEFAULT_SITE_SETTINGS,
        )

    namespace = runpy.run_path(str(CONFIG_PATH))
    legacy_credentials = _coerce_mapping(namespace.get("CREDENTIALS"))
    dice_credentials = _normalize_credentials(
        namespace.get("DICE_CREDENTIALS", legacy_credentials),
        DEFAULT_DICE_CREDENTIALS,
    )
    linkedin_credentials = _normalize_credentials(
        namespace.get("LINKEDIN_CREDENTIALS"),
        DEFAULT_LINKEDIN_CREDENTIALS,
    )

    search_settings = {
        **DEFAULT_SEARCH_SETTINGS,
        **_coerce_mapping(namespace.get("SEARCH_SETTINGS")),
    }
    keywords = normalize_keywords(
        search_settings.get("keywords", search_settings.get("keyword"))
    ) or list(DEFAULT_SEARCH_SETTINGS["keywords"])
    search_settings["keywords"] = keywords
    search_settings["keyword"] = keywords[0]
    search_settings["max_applications"] = _normalize_max_applications(
        search_settings.get("max_applications")
    )

    raw_site_settings = {
        **DEFAULT_SITE_SETTINGS,
        **_coerce_mapping(namespace.get("SITE_SETTINGS")),
    }
    site_settings = {
        "dice_enabled": _normalize_bool(
            raw_site_settings.get("dice_enabled"),
            DEFAULT_SITE_SETTINGS["dice_enabled"],
        ),
        "linkedin_enabled": _normalize_bool(
            raw_site_settings.get("linkedin_enabled"),
            DEFAULT_SITE_SETTINGS["linkedin_enabled"],
        ),
    }

    return {
        "credentials": dice_credentials,
        "dice_credentials": dice_credentials,
        "linkedin_credentials": linkedin_credentials,
        "search_settings": search_settings,
        "site_settings": site_settings,
    }
