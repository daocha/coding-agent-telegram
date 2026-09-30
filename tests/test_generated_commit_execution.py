from __future__ import annotations

import asyncio
import shlex
import subprocess
from types import SimpleNamespace

import pytest

from coding_agent_telegram.git_utils import GitWorkspaceManager
from test_command_router import _make_commit_router, FakeBot, FakeGitManager


@pytest.mark.parametrize('command', [
    'git commit -a -m "Short summary"',
    'git add file.txt && git commit -m "Summary" -m "Details" --only -- file.txt',
])
def test_generated_commit_accepts_supported_variants(tmp_path, command):
    router, _ = _make_commit_router(tmp_path, git_manager=FakeGitManager(is_git_repo=True))
    assert router._extract_generated_commit_command('```bash\n' + command + '\n```') == command


@pytest.mark.parametrize('command', [
    'git add file.txt && git commit --unsupported -m "Summary"',
    'git add file.txt && git commit -m "unterminated',
    'git add file.txt && python script.py && git commit -m "Summary"',
])
def test_invalid_generated_command_does_not_stage_files(tmp_path, command):
    router, _ = _make_commit_router(tmp_path, git_manager=FakeGitManager(is_git_repo=True))
    assert router._extract_generated_commit_command('```bash\n' + command + '\n```') is None
    token = '0123456789ab'
    router._generated_commit_commands()[token] = {
        'chat_id': '123', 'command': command, 'session_id': 'sess_commit',
        'project_folder': 'backend', 'branch_name': '',
    }
    async def answer():
        pass
    async def edit(text):
        pass
    update = SimpleNamespace(effective_chat=SimpleNamespace(id=123, type='private'),
        callback_query=SimpleNamespace(data=f'commitexec:confirm:{token}', answer=answer, edit_message_text=edit))
    asyncio.run(router.handle_commit_execute_callback(update, SimpleNamespace(args=[], bot=FakeBot())))
    assert not router.git.safe_git_commands
    assert token not in router._generated_commit_commands()


def test_long_generated_commit_executes_and_excludes_unrelated_staged_file(tmp_path):
    router, _ = _make_commit_router(tmp_path, git_manager=FakeGitManager(is_git_repo=True))
    project = tmp_path / 'backend'
    def git(*args):
        return subprocess.run(['git', *args], cwd=project, check=True, capture_output=True, text=True).stdout
    git('init')
    git('config', 'user.name', 'Test')
    git('config', 'user.email', 'test@example.invalid')
    git('config', 'commit.gpgsign', 'false')
    (project / 'baseline').write_text('base')
    git('add', 'baseline')
    git('commit', '-m', 'Baseline')
    (project / 'unrelated.txt').write_text('leave staged')
    git('add', 'unrelated.txt')
    paths = [f'file {index:03d} with spaces.txt' for index in range(100)]
    for path in paths:
        (project / path).write_text('new content')
    messages = ['Concise summary', 'Details with punctuation: && ; | < >', 'Unicode: 中文']
    command = shlex.join(['git', 'add', '--', *paths]) + ' && ' + shlex.join(
        ['git', 'commit', *[arg for message in messages for arg in ('-m', message)], '--only', '--', *paths])
    assert len(command) > 4096
    extracted = router._extract_generated_commit_command('```bash\n' + command + '\n```')
    assert extracted == command
    commands, ignored = router._validated_commit_commands(extracted)
    assert not ignored
    assert router._commands_use_only_project_paths(project, commands)
    manager = GitWorkspaceManager()
    for args in commands:
        result = manager.run_safe_commit_command(project, router._effective_git_args(args))
        assert result.success, result.message
    assert git('log', '-1', '--format=%B').strip() == '\n\n'.join(messages)
    assert git('diff', '--cached', '--name-only').strip() == 'unrelated.txt'
    assert len(git('diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD').splitlines()) == 100
