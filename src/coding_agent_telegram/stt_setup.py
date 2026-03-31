from __future__ import annotations

import argparse
import importlib
import importlib.util
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from coding_agent_telegram.config import (
    DEFAULT_OPENAI_WHISPER_MODEL,
    DEFAULT_OPENAI_WHISPER_TIMEOUT_SECONDS,
    create_initial_env_file,
    resolve_env_file_path,
)


ENABLE_STT_ENV = "ENABLE_OPENAI_WHISPER_SPEECH_TO_TEXT"
STT_INSTALL_HINT_ENV = "CODING_AGENT_TELEGRAM_STT_INSTALL_HINT"
STT_SIZE_GUIDANCE = (
    "Estimated local footprint: openai-whisper package about 50 MB, ffmpeg about 50 MB, "
    "and Whisper model downloads vary by model size "
    "(tiny about 72 MB, base about 139 MB, large-v3-turbo about 1.5 GB)."
)


@dataclass(frozen=True)
class SttPrereqStatus:
    ffmpeg: bool
    whisper_module: bool

    @property
    def missing(self) -> list[str]:
        missing: list[str] = []
        if not self.ffmpeg:
            missing.append("ffmpeg")
        if not self.whisper_module:
            missing.append("openai-whisper (Python module)")
        return missing

    @property
    def ready(self) -> bool:
        return not self.missing


def _has_whisper_module(python_bin: str | None = None) -> bool:
    if python_bin is None:
        return importlib.util.find_spec("whisper") is not None
    result = subprocess.run(
        [python_bin, "-c", "import importlib.util, sys; raise SystemExit(0 if importlib.util.find_spec('whisper') else 1)"],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def detect_stt_prereqs(*, python_bin: str | None = None) -> SttPrereqStatus:
    importlib.invalidate_caches()
    return SttPrereqStatus(
        ffmpeg=shutil.which("ffmpeg") is not None,
        whisper_module=_has_whisper_module(python_bin),
    )


def ensure_stt_runtime_or_exit(enabled: bool, *, install_hint: Optional[str] = None) -> None:
    if not enabled:
        return

    status = detect_stt_prereqs()
    if status.ready:
        return

    resolved_hint = (install_hint or os.getenv(STT_INSTALL_HINT_ENV, "")).strip() or "coding-agent-telegram-stt-install"
    missing_text = ", ".join(status.missing)
    raise SystemExit(
        "\n".join(
            [
                f"Error: {ENABLE_STT_ENV}=true but speech-to-text prerequisites are missing: {missing_text}",
                f"Run: {resolved_hint}",
                STT_SIZE_GUIDANCE,
            ]
        )
    )


def _resolve_env_path(explicit: str | None = None) -> Path:
    env_path = resolve_env_file_path(Path(explicit).expanduser() if explicit else None)
    env_path.parent.mkdir(parents=True, exist_ok=True)
    if not env_path.exists():
        create_initial_env_file(env_path)
    return env_path


def _set_env_flag(env_path: Path, enabled: bool) -> None:
    lines = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()

    def upsert(key: str, value: str, comments: list[str] | None = None, overwrite: bool = True) -> None:
        replacement = f"{key}={value}"
        for index, line in enumerate(lines):
            if line.startswith(f"{key}="):
                if overwrite:
                    lines[index] = replacement
                return
        if lines and lines[-1].strip():
            lines.append("")
        if comments:
            lines.extend(comments)
        lines.append(replacement)

    upsert(
        ENABLE_STT_ENV,
        "true" if enabled else "false",
        comments=[
            "# If true, enable Telegram voice-message speech-to-text with local openai-whisper.",
            "# Estimated local footprint: package ~50 MB, ffmpeg ~50 MB, model downloads vary by model size.",
        ],
    )
    upsert(
        "OPENAI_WHISPER_MODEL",
        DEFAULT_OPENAI_WHISPER_MODEL,
        comments=[
            "# Whisper model name for Telegram voice-message speech-to-text.",
            "# `turbo` downloads the large-v3-turbo model (~1.5 GB) on first use into ~/.cache/whisper.",
            "# If turbo is not cached yet, the first voice transcription is more likely to hit the timeout.",
        ],
        overwrite=False,
    )
    upsert(
        "OPENAI_WHISPER_TIMEOUT_SECONDS",
        str(DEFAULT_OPENAI_WHISPER_TIMEOUT_SECONDS),
        comments=["# Timeout for a single Whisper transcription call, in seconds."],
        overwrite=False,
    )

    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _prompt_yes_no(prompt: str, *, default: bool = True) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    while True:
        try:
            answer = input(f"{prompt} {suffix} ").strip().lower()
        except EOFError:
            return default
        if not answer:
            return default
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Please answer yes or no.")


def _package_manager() -> tuple[str, list[str]] | tuple[None, None]:
    if sys.platform == "darwin" and shutil.which("brew"):
        return "brew", ["brew", "install", "ffmpeg"]
    if sys.platform.startswith("linux"):
        if shutil.which("apt-get"):
            prefix = ["sudo"] if hasattr(os, "geteuid") and os.geteuid() != 0 and shutil.which("sudo") else []
            return "apt-get", [*prefix, "apt-get", "update", "&&", *prefix, "apt-get", "install", "-y", "ffmpeg"]
        if shutil.which("dnf"):
            prefix = ["sudo"] if hasattr(os, "geteuid") and os.geteuid() != 0 and shutil.which("sudo") else []
            return "dnf", [*prefix, "dnf", "install", "-y", "ffmpeg"]
        if shutil.which("yum"):
            prefix = ["sudo"] if hasattr(os, "geteuid") and os.geteuid() != 0 and shutil.which("sudo") else []
            return "yum", [*prefix, "yum", "install", "-y", "ffmpeg"]
    return None, None


def _run_shell_command(command: str) -> bool:
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, check=False)
    return result.returncode == 0


def _ensure_ffmpeg_installed() -> bool:
    while True:
        status = detect_stt_prereqs()
        if status.ffmpeg:
            return True

        print("Missing required system binary: ffmpeg")

        manager, command_parts = _package_manager()
        if manager == "apt-get":
            install_command = " ".join(command_parts)
        elif command_parts is not None:
            install_command = " ".join(command_parts)
        else:
            install_command = ""

        if install_command:
            if not _prompt_yes_no(f"Install ffmpeg now using {manager}?"):
                return False
            if _run_shell_command(install_command):
                continue
            print("Automatic ffmpeg installation did not complete successfully.")
            if not _prompt_yes_no("Retry ffmpeg installation?"):
                return False
            continue

        print("Automatic ffmpeg installation is not available on this OS/package-manager combination.")
        print("Install ffmpeg manually, then return here and choose continue.")
        if not _prompt_yes_no("Continue after manual installation?", default=False):
            return False


def _ensure_whisper_installed(python_bin: str) -> bool:
    while True:
        status = detect_stt_prereqs(python_bin=python_bin)
        if status.whisper_module:
            return True

        print("Missing required Python package: openai-whisper")
        if not _prompt_yes_no(f"Install openai-whisper with {python_bin} -m pip?"):
            return False
        command = f"{python_bin} -m pip install --upgrade openai-whisper"
        if _run_shell_command(command):
            continue
        print("openai-whisper installation did not complete successfully.")
        if not _prompt_yes_no("Retry openai-whisper installation?"):
            return False


def install_stt_dependencies(*, env_file: str | None = None, python_bin: str | None = None) -> int:
    env_path = _resolve_env_path(env_file)
    resolved_python = python_bin or sys.executable

    print(STT_SIZE_GUIDANCE)
    print(f"Using env file: {env_path}")

    if not _ensure_ffmpeg_installed():
        print("Speech-to-text installation aborted before ffmpeg prerequisites were satisfied.")
        return 1
    if not _ensure_whisper_installed(resolved_python):
        print("Speech-to-text installation aborted before openai-whisper was installed.")
        return 1

    _set_env_flag(env_path, True)
    print(f"Speech-to-text prerequisites are ready. Enabled {ENABLE_STT_ENV}=true in {env_path}.")
    return 0


def offer_stt_install_for_new_env(
    *,
    env_file: str | None = None,
    python_bin: str | None = None,
    installer_label: str,
) -> int:
    env_path = _resolve_env_path(env_file)
    print("A new env file was created for coding-agent-telegram.")
    print(STT_SIZE_GUIDANCE)
    if not _prompt_yes_no(
        f"Do you want to enable local Whisper speech-to-text now? This will run {installer_label}.",
        default=False,
    ):
        print(f"Keeping {ENABLE_STT_ENV}=false in {env_path}.")
        return 0

    result = install_stt_dependencies(env_file=str(env_path), python_bin=python_bin)
    if result != 0:
        print(f"Speech-to-text setup did not complete. Keeping {ENABLE_STT_ENV}=false unless you enable it later.")
        _set_env_flag(env_path, False)
        return 0
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        argv = ["install"]

    parser = argparse.ArgumentParser(description="Install or validate local Whisper speech-to-text support.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    install_parser = subparsers.add_parser("install", help="Install missing speech-to-text prerequisites.")
    install_parser.add_argument("--env-file", help="Explicit env file path to update.")
    install_parser.add_argument("--python-bin", help="Python executable to use for pip installation.")
    offer_parser = subparsers.add_parser("offer", help="Prompt whether to enable speech-to-text for a new env file.")
    offer_parser.add_argument("--env-file", help="Explicit env file path to update.")
    offer_parser.add_argument("--python-bin", help="Python executable to use for pip installation.")
    offer_parser.add_argument("--installer-label", required=True, help="User-facing installer command label.")

    args = parser.parse_args(argv)

    if args.command == "install":
        return install_stt_dependencies(env_file=args.env_file, python_bin=args.python_bin)
    if args.command == "offer":
        return offer_stt_install_for_new_env(
            env_file=args.env_file,
            python_bin=args.python_bin,
            installer_label=args.installer_label,
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
