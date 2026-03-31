from pathlib import Path

import pytest

from coding_agent_telegram import stt_setup


def test_detect_stt_prereqs_reports_missing(monkeypatch):
    monkeypatch.setattr(stt_setup.shutil, "which", lambda name: None)
    monkeypatch.setattr(stt_setup.importlib.util, "find_spec", lambda name: None)

    status = stt_setup.detect_stt_prereqs()

    assert status.ready is False
    assert status.missing == ["ffmpeg", "openai-whisper (Python module)"]


def test_detect_stt_prereqs_checks_target_python_when_provided(monkeypatch):
    monkeypatch.setattr(stt_setup.shutil, "which", lambda name: "/usr/bin/ffmpeg")
    monkeypatch.setattr(
        stt_setup.subprocess,
        "run",
        lambda *args, **kwargs: type("Result", (), {"returncode": 0})(),
    )

    status = stt_setup.detect_stt_prereqs(python_bin="/custom/python")

    assert status.ready is True
    assert status.whisper_module is True


def test_ensure_stt_runtime_or_exit_uses_install_hint(monkeypatch):
    monkeypatch.setattr(
        stt_setup,
        "detect_stt_prereqs",
        lambda **kwargs: stt_setup.SttPrereqStatus(ffmpeg=True, whisper_module=False),
    )

    with pytest.raises(SystemExit) as exc:
        stt_setup.ensure_stt_runtime_or_exit(True, install_hint="./install-stt.sh")

    assert "./install-stt.sh" in str(exc.value)
    assert "openai-whisper" in str(exc.value)


def test_set_env_flag_appends_when_missing(tmp_path):
    env_path = tmp_path / ".env_coding_agent_telegram"
    env_path.write_text("WORKSPACE_ROOT=~/git\n", encoding="utf-8")

    stt_setup._set_env_flag(env_path, True)

    text = env_path.read_text(encoding="utf-8")
    assert "ENABLE_OPENAI_WHISPER_SPEECH_TO_TEXT=true" in text
    assert "openai-whisper" in text


def test_set_env_flag_replaces_existing_value(tmp_path):
    env_path = tmp_path / ".env_coding_agent_telegram"
    env_path.write_text("ENABLE_OPENAI_WHISPER_SPEECH_TO_TEXT=false\n", encoding="utf-8")

    stt_setup._set_env_flag(env_path, True)

    text = env_path.read_text(encoding="utf-8")
    assert "ENABLE_OPENAI_WHISPER_SPEECH_TO_TEXT=true" in text
    assert "OPENAI_WHISPER_MODEL=base" in text
    assert "OPENAI_WHISPER_TIMEOUT_SECONDS=120" in text


def test_set_env_flag_preserves_user_customised_model(tmp_path):
    env_path = tmp_path / ".env_coding_agent_telegram"
    env_path.write_text(
        "ENABLE_OPENAI_WHISPER_SPEECH_TO_TEXT=true\n"
        "OPENAI_WHISPER_MODEL=large-v3-turbo\n"
        "OPENAI_WHISPER_TIMEOUT_SECONDS=300\n",
        encoding="utf-8",
    )

    stt_setup._set_env_flag(env_path, True)

    text = env_path.read_text(encoding="utf-8")
    assert "OPENAI_WHISPER_MODEL=large-v3-turbo" in text
    assert "OPENAI_WHISPER_TIMEOUT_SECONDS=300" in text
    assert "OPENAI_WHISPER_MODEL=base" not in text
    assert "OPENAI_WHISPER_TIMEOUT_SECONDS=120" not in text


def test_offer_stt_install_for_new_env_keeps_false_when_declined(monkeypatch, tmp_path):
    env_path = tmp_path / ".env_coding_agent_telegram"
    env_path.write_text("ENABLE_OPENAI_WHISPER_SPEECH_TO_TEXT=false\n", encoding="utf-8")
    monkeypatch.setattr(stt_setup, "_prompt_yes_no", lambda *args, **kwargs: False)

    result = stt_setup.offer_stt_install_for_new_env(
        env_file=str(env_path),
        python_bin="python3",
        installer_label="coding-agent-telegram-stt-install",
    )

    assert result == 0
    assert "ENABLE_OPENAI_WHISPER_SPEECH_TO_TEXT=false" in env_path.read_text(encoding="utf-8")
