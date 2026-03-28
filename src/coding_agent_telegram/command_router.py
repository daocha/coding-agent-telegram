from __future__ import annotations

from coding_agent_telegram.router.base import CommandRouterBase, RouterDeps
from coding_agent_telegram.router.git_commands import GitCommandMixin
from coding_agent_telegram.router.message_commands import MessageCommandMixin
from coding_agent_telegram.router.project_commands import ProjectCommandMixin
from coding_agent_telegram.router.queue_processing import QueueProcessingMixin
from coding_agent_telegram.router.session_commands import SessionCommandMixin
from coding_agent_telegram.router.switch_commands import SwitchCommandMixin


class CommandRouter(
    ProjectCommandMixin,
    GitCommandMixin,
    SwitchCommandMixin,
    SessionCommandMixin,
    QueueProcessingMixin,
    MessageCommandMixin,
    CommandRouterBase,
):
    """Compose categorized command handlers behind the historical router API."""
