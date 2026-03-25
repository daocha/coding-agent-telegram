from __future__ import annotations

import sys

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py
from setuptools.command.develop import develop as _develop
from setuptools.command.egg_info import egg_info as _egg_info
from setuptools.command.install import install as _install


POST_INSTALL_GUIDE = """

Post-installation guide for coding-agent-telegram:
1. Run ./startup.sh
2. If .env does not exist, the script will create it from src/coding_agent_telegram/resources/.env.example
3. Edit .env and set WORKSPACE_ROOT, TELEGRAM_BOT_TOKENS, and ALLOWED_CHAT_IDS
4. Re-run ./startup.sh to start the server
5. In Telegram, use /project <folder> and then /new <session_name> [provider]
""".strip()


def _print_guide_once() -> None:
    if getattr(_print_guide_once, "_printed", False):
        return
    sys.stderr.write(POST_INSTALL_GUIDE + "\n")
    sys.stderr.flush()
    _print_guide_once._printed = True


class build_py(_build_py):
    def run(self):
        _print_guide_once()
        super().run()


class egg_info(_egg_info):
    def run(self):
        _print_guide_once()
        super().run()


class install(_install):
    def run(self):
        _print_guide_once()
        super().run()


class develop(_develop):
    def run(self):
        _print_guide_once()
        super().run()


_print_guide_once()


setup(
    cmdclass={
        "build_py": build_py,
        "egg_info": egg_info,
        "install": install,
        "develop": develop,
    }
)
