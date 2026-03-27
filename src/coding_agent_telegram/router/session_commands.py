from __future__ import annotations

import shutil  # Backward compatibility for tests/monkeypatches using the legacy module path.

from .session_branch_resolution import SessionBranchResolutionMixin
from .session_common import SessionCommonMixin
from .session_lifecycle_commands import SessionLifecycleCommandMixin
from .session_provider_commands import SessionProviderCommandMixin
from .session_status_commands import SessionStatusCommandMixin


class SessionCommandMixin(
    SessionCommonMixin,
    SessionProviderCommandMixin,
    SessionBranchResolutionMixin,
    SessionLifecycleCommandMixin,
    SessionStatusCommandMixin,
):
    """Compatibility mixin that groups session-related command helpers."""
