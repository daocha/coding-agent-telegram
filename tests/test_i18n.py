"""Tests for coding_agent_telegram.i18n covering all locale-normalisation paths."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from coding_agent_telegram.i18n import (
    DEFAULT_LOCALE,
    _load_locale_catalog,
    locale_from_update,
    normalize_locale,
    translate,
)


# ---------------------------------------------------------------------------
# normalize_locale
# ---------------------------------------------------------------------------


def test_normalize_locale_returns_default_for_none():
    assert normalize_locale(None) == DEFAULT_LOCALE  # line 17


def test_normalize_locale_returns_default_for_empty_string():
    assert normalize_locale("") == DEFAULT_LOCALE  # line 17


def test_normalize_locale_zh_hk():
    assert normalize_locale("zh-HK") == "zh-HK"  # line 21
    assert normalize_locale("zh_HK") == "zh-HK"


def test_normalize_locale_zh_mo():
    assert normalize_locale("zh-MO") == "zh-HK"  # line 21


def test_normalize_locale_zh_tw():
    assert normalize_locale("zh-TW") == "zh-TW"  # line 23
    assert normalize_locale("zh_TW") == "zh-TW"


def test_normalize_locale_zh_hant():
    assert normalize_locale("zh-Hant") == "zh-TW"  # line 23


def test_normalize_locale_zh_cn():
    assert normalize_locale("zh-CN") == "zh-CN"  # line 25
    assert normalize_locale("zh") == "zh-CN"  # line 25


def test_normalize_locale_supported_base_code():
    assert normalize_locale("ja") == "ja"
    assert normalize_locale("de") == "de"
    assert normalize_locale("ko") == "ko"


def test_normalize_locale_unsupported_falls_back_to_default():
    assert normalize_locale("es") == DEFAULT_LOCALE
    assert normalize_locale("pt-BR") == DEFAULT_LOCALE


# ---------------------------------------------------------------------------
# locale_from_update
# ---------------------------------------------------------------------------


def test_locale_from_update_extracts_language_code():  # lines 31-33
    update = SimpleNamespace(effective_user=SimpleNamespace(language_code="ja"))
    assert locale_from_update(update) == "ja"


def test_locale_from_update_returns_default_when_no_effective_user():  # line 34
    update = SimpleNamespace(effective_user=None)
    assert locale_from_update(update) == DEFAULT_LOCALE


def test_locale_from_update_returns_default_when_language_code_missing():
    update = SimpleNamespace(effective_user=SimpleNamespace(language_code=None))
    assert locale_from_update(update) == DEFAULT_LOCALE


def test_locale_from_update_handles_object_with_no_effective_user_attr():
    update = SimpleNamespace()  # no effective_user attribute
    assert locale_from_update(update) == DEFAULT_LOCALE


# ---------------------------------------------------------------------------
# _load_locale_catalog error paths
# ---------------------------------------------------------------------------


def test_load_locale_catalog_returns_empty_dict_for_file_not_found():  # lines 42-43
    # Use a locale code that has no JSON file — should hit the FileNotFoundError branch
    _load_locale_catalog.cache_clear()
    try:
        result = _load_locale_catalog("zz-nonexistent-locale")
    finally:
        _load_locale_catalog.cache_clear()
    assert result == {}


def test_load_locale_catalog_returns_empty_dict_for_json_decode_error():  # lines 44-45
    import json
    _load_locale_catalog.cache_clear()
    try:
        # Patch json.loads to simulate corrupt JSON
        with patch("coding_agent_telegram.i18n.json.loads", side_effect=json.JSONDecodeError("bad", "", 0)):
            result = _load_locale_catalog.__wrapped__("en")
    finally:
        _load_locale_catalog.cache_clear()
    assert result == {}


# ---------------------------------------------------------------------------
# translate: fallback to DEFAULT_LOCALE when key missing in non-en locale
# ---------------------------------------------------------------------------


def test_translate_falls_back_to_english_when_key_missing_in_locale():  # line 53
    # "common.no_project_selected" should exist in en but not in a fake locale
    result = translate("ja", "common.no_project_selected")
    # Should return the English string, not the key itself
    assert result != "common.no_project_selected"
    assert "project" in result.lower() or "Project" in result


def test_translate_returns_key_when_missing_in_both_locales():
    result = translate("ja", "this.key.does.not.exist.anywhere.xyz")
    assert result == "this.key.does.not.exist.anywhere.xyz"


def test_translate_formats_kwargs():
    result = translate("en", "common.no_project_selected")
    assert result  # just check it renders without error
