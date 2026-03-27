import io
from pathlib import Path

from coding_agent_telegram.agent_runner import AgentStallInfo, MultiAgentRunner


class _FakeProcess:
    def __init__(self):
        self.stdout = io.StringIO("")
        self.stderr = io.StringIO("")
        self.returncode = 0
        self._poll_calls = 0

    def poll(self):
        self._poll_calls += 1
        if self._poll_calls == 1:
            return None
        return self.returncode


def test_runner_reports_stall_without_killing_process(monkeypatch):
    process = _FakeProcess()
    captured: list[AgentStallInfo] = []
    monotonic_values = iter([0.0, 70.0, 70.0])

    def fake_popen(args, cwd=None, env=None, stdout=None, stderr=None, text=None, start_new_session=None):
        return process

    monkeypatch.setattr("coding_agent_telegram.agent_runner.subprocess.Popen", fake_popen)
    monkeypatch.setattr("coding_agent_telegram.agent_runner.time.sleep", lambda _: None)
    monkeypatch.setattr("coding_agent_telegram.agent_runner.time.monotonic", lambda: next(monotonic_values))

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )

    result = runner.create_session("copilot", Path("/tmp/project"), "hello", on_stall=captured.append)

    assert result.success is True
    assert len(captured) == 1
    assert captured[0].idle_seconds >= runner.STALL_WARNING_AFTER_SECONDS
    assert captured[0].seen_output is False
