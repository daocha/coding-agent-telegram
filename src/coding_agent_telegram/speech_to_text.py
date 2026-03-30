from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from coding_agent_telegram.config import AppConfig, DEFAULT_OPENAI_WHISPER_MODEL


_MODEL_CACHE_FILENAMES = {
    "tiny": "tiny.pt",
    "tiny.en": "tiny.en.pt",
    "base": "base.pt",
    "base.en": "base.en.pt",
    "small": "small.pt",
    "small.en": "small.en.pt",
    "medium": "medium.pt",
    "medium.en": "medium.en.pt",
    "large": "large-v3.pt",
    "large-v1": "large-v1.pt",
    "large-v2": "large-v2.pt",
    "large-v3": "large-v3.pt",
    "large-v3-turbo": "large-v3-turbo.pt",
    "turbo": "large-v3-turbo.pt",
}


class SpeechToTextError(RuntimeError):
    def __init__(self, code: str, *, likely_first_download: bool = False) -> None:
        super().__init__(code)
        self.code = code
        self.likely_first_download = likely_first_download


@dataclass(frozen=True)
class SpeechToTextResult:
    text: str
    model: str


class WhisperSpeechToText:
    def __init__(self, cfg: AppConfig) -> None:
        self.enabled = cfg.enable_openai_whisper_speech_to_text
        self.model = cfg.openai_whisper_model or DEFAULT_OPENAI_WHISPER_MODEL
        self.timeout_seconds = cfg.openai_whisper_timeout_seconds

    def _model_cache_path(self) -> Path:
        cache_root = Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache")).expanduser()
        file_name = _MODEL_CACHE_FILENAMES.get(self.model, f"{self.model}.pt")
        return cache_root / "whisper" / file_name

    def _likely_first_download(self) -> bool:
        return not self._model_cache_path().exists()

    def transcribe_file(self, audio_path: Path) -> SpeechToTextResult:
        likely_first_download = self._likely_first_download()

        with tempfile.TemporaryDirectory(prefix="coding-agent-telegram-whisper-") as output_dir:
            command = [
                sys.executable,
                "-m",
                "whisper",
                str(audio_path),
                "--model",
                self.model,
                "--task",
                "transcribe",
                "--output_format",
                "json",
                "--output_dir",
                output_dir,
                "--verbose",
                "False",
                "--fp16",
                "False",
                "--condition_on_previous_text",
                "False",
            ]
            try:
                result = subprocess.run(
                    command,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                )
            except subprocess.TimeoutExpired as exc:
                raise SpeechToTextError("timeout", likely_first_download=likely_first_download) from exc

            if result.returncode != 0:
                raise SpeechToTextError("failed", likely_first_download=likely_first_download)

            transcript_path = Path(output_dir) / f"{audio_path.stem}.json"
            if not transcript_path.exists():
                raise SpeechToTextError("failed", likely_first_download=likely_first_download)

            try:
                payload = json.loads(transcript_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise SpeechToTextError("failed", likely_first_download=likely_first_download) from exc

        text = str(payload.get("text") or "").strip()
        if not text:
            raise SpeechToTextError("empty", likely_first_download=likely_first_download)
        return SpeechToTextResult(text=text, model=self.model)
