from __future__ import annotations

import importlib.resources
import json
import logging
from functools import lru_cache
from typing import Any


logger = logging.getLogger(__name__)
DEFAULT_LOCALE = "en"
SUPPORTED_LOCALES = ("de", "fr", "ja", "ko", "nl", "th", "vi", "zh-CN", "zh-HK", "zh-TW")


def normalize_locale(language_code: str | None) -> str:
    if not language_code:
        return DEFAULT_LOCALE
    normalized = language_code.strip().replace("_", "-")
    lowered = normalized.lower()
    if lowered.startswith("zh-hk") or lowered.startswith("zh-mo"):
        return "zh-HK"
    if lowered.startswith("zh-tw") or lowered.startswith("zh-hant"):
        return "zh-TW"
    if lowered.startswith("zh"):
        return "zh-CN"
    base = lowered.split("-", 1)[0]
    return base if base in SUPPORTED_LOCALES else DEFAULT_LOCALE


def locale_from_update(update: Any) -> str:
    effective_user = getattr(update, "effective_user", None)
    if effective_user is not None:
        return normalize_locale(getattr(effective_user, "language_code", None))
    return DEFAULT_LOCALE


@lru_cache(maxsize=None)
def _load_locale_catalog(locale: str) -> dict[str, str]:
    resource = importlib.resources.files("coding_agent_telegram").joinpath(f"resources/locales/{locale}.json")
    try:
        return json.loads(resource.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.warning("Locale catalog not found for %s.", locale)
    except (OSError, json.JSONDecodeError):
        logger.exception("Failed to load locale catalog for %s.", locale)
    return {}


def translate(locale: str, key: str, **kwargs: Any) -> str:
    resolved_locale = normalize_locale(locale)
    template = _load_locale_catalog(resolved_locale).get(key)
    if template is None and resolved_locale != DEFAULT_LOCALE:
        template = _load_locale_catalog(DEFAULT_LOCALE).get(key)
    return (template or key).format(**kwargs)
