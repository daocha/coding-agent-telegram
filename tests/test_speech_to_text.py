import json
import subprocess
from pathlib import Path

import pytest

from coding_agent_telegram.config import AppConfig
from coding_agent_telegram.speech_to_text import SpeechToTextError, WhisperSpeechToText


def _cfg(tmp_path: Path, *, model: str = "base", timeout: int = 120) -> AppConfig:
    return AppConfig(
        workspace_root=tmp_path,
        state_file=tmp_path / "state.json",
        state_backup_file=tmp_path / "state.json.bak",
        log_level="INFO",
        log_dir=tmp_path / "logs",
        telegram_bot_tokens=("token",),
        allowed_chat_ids={123},
        codex_bin="codex",
        copilot_bin="copilot",
        codex_model="",
        copilot_model="",
        copilot_autopilot=True,
        copilot_no_ask_user=True,
        copilot_allow_all=True,
        copilot_allow_all_tools=False,
        copilot_allow_tools=(),
        copilot_deny_tools=(),
        copilot_available_tools=(),
        codex_approval_policy="never",
        codex_sandbox_mode="workspace-write",
        codex_skip_git_repo_check=False,
        enable_commit_command=False,
        snapshot_text_file_max_bytes=200000,
        max_telegram_message_length=3000,
        enable_sensitive_diff_filter=True,
        enable_secret_scrub_filter=True,
        enable_openai_whisper_speech_to_text=True,
        openai_whisper_model=model,
        openai_whisper_timeout_seconds=timeout,
        default_agent_provider="codex",
        agent_hard_timeout_seconds=0,
        app_internal_root=tmp_path / ".coding-agent-telegram",
        locale="en",
    )


def test_model_cache_path_maps_turbo_alias(tmp_path):
    transcriber = WhisperSpeechToText(_cfg(tmp_path, model="turbo"))

    assert transcriber._model_cache_path().name == "large-v3-turbo.pt"


def test_transcribe_file_returns_text(monkeypatch, tmp_path):
    audio_path = tmp_path / "voice.ogg"
    audio_path.write_bytes(b"voice")
    transcriber = WhisperSpeechToText(_cfg(tmp_path))

    def fake_run(command, **kwargs):
        output_dir = Path(command[command.index("--output_dir") + 1])
        (output_dir / "voice.json").write_text(json.dumps({"text": "hello world"}), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("coding_agent_telegram.speech_to_text.subprocess.run", fake_run)

    result = transcriber.transcribe_file(audio_path)

    assert result.text == "hello world"
    assert result.model == "base"


def test_transcribe_file_timeout_marks_likely_first_download(monkeypatch, tmp_path):
    audio_path = tmp_path / "voice.ogg"
    audio_path.write_bytes(b"voice")
    transcriber = WhisperSpeechToText(_cfg(tmp_path, model="turbo", timeout=1))
    monkeypatch.setattr(WhisperSpeechToText, "_likely_first_download", lambda self: True)

    def fake_run(command, **kwargs):
        raise subprocess.TimeoutExpired(command, timeout=1)

    monkeypatch.setattr("coding_agent_telegram.speech_to_text.subprocess.run", fake_run)

    with pytest.raises(SpeechToTextError) as exc:
        transcriber.transcribe_file(audio_path)

    assert exc.value.code == "timeout"
    assert exc.value.likely_first_download is True
