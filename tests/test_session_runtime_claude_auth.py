from types import SimpleNamespace

from coding_agent_telegram.agent_runner import AgentRunResult
from coding_agent_telegram.session_runtime import SessionRuntime


def _runtime(locale: str = "en") -> SessionRuntime:
    return SessionRuntime(
        cfg=SimpleNamespace(locale=locale),
        store=None,
        agent_runner=None,
        bot_id="bot-a",
        git=None,
        run_with_typing=None,
        register_reply_options=None,
    )


def _result(error_message, *, error_code=None) -> AgentRunResult:
    return AgentRunResult(
        session_id=None,
        success=False,
        assistant_text="",
        error_message=error_message,
        raw_events=[],
        error_code=error_code,
    )


def test_agent_failure_text_uses_claude_auth_guidance_for_claude_auth_error():
    runtime = _runtime()
    result = _result("Failed to authenticate: OAuth session expired and could not be refreshed")

    text = runtime._agent_failure_text(None, "claude", result)

    assert "claude setup-token" in text
    assert "claude-auth" in text


def test_agent_failure_text_ignores_auth_wording_for_other_providers():
    runtime = _runtime()
    result = _result("Failed to authenticate: OAuth session expired and could not be refreshed")

    text = runtime._agent_failure_text(None, "codex", result)

    assert text == "Failed to authenticate: OAuth session expired and could not be refreshed"


def test_agent_failure_text_falls_back_to_sanitized_error_for_non_auth_failures():
    runtime = _runtime()
    result = _result("Rate limit exceeded at /Users/daocha/git/some-project/file.py")

    text = runtime._agent_failure_text(None, "claude", result)

    assert text == "Rate limit exceeded at <path>"


def test_agent_failure_text_aborted_takes_priority_over_auth_wording():
    runtime = _runtime()
    result = _result(
        "Failed to authenticate: OAuth session expired and could not be refreshed",
        error_code="agent_aborted",
    )

    text = runtime._agent_failure_text(None, "claude", result)

    assert text == "Agent run aborted by /abort."
