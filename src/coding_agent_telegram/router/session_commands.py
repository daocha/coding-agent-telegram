from __future__ import annotations

import asyncio
import shutil
import time
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from coding_agent_telegram.filters import resolve_project_path
from coding_agent_telegram.telegram_sender import send_text

from .base import logger, require_allowed_chat


class SessionCommandMixin:
    PROVIDER_BIN_AVAILABLE_CACHE_TTL_SECONDS = 12 * 60 * 60
    PROVIDER_BIN_MISSING_CACHE_TTL_SECONDS = 5 * 60

    def _next_available_session_name(self, chat_id: int, base_name: str) -> str:
        existing_names = {
            data.get("name", "").strip().lower()
            for data in self.deps.store.list_sessions(self.deps.bot_id, chat_id).values()
            if data.get("name", "").strip()
        }
        if base_name.lower() not in existing_names:
            return base_name
        suffix = 1
        while True:
            candidate = f"{base_name}-{suffix}"
            if candidate.lower() not in existing_names:
                return candidate
            suffix += 1

    def _selected_provider(self, chat_state: dict[str, object]) -> str:
        provider = str(chat_state.get("current_provider") or "").strip().lower()
        return provider if provider in {"codex", "copilot"} else ""

    def _provider_bin(self, provider: str) -> str:
        return self.deps.cfg.codex_bin if provider == "codex" else self.deps.cfg.copilot_bin

    def _provider_available(self, provider: str) -> bool:
        bin_name = self._provider_bin(provider)
        now = time.monotonic()
        cache = getattr(self, "_provider_availability_cache", {})
        cached = cache.get(provider)
        if cached is not None:
            cached_at, cached_available, cached_bin_name = cached
            ttl = (
                self.PROVIDER_BIN_AVAILABLE_CACHE_TTL_SECONDS
                if cached_available
                else self.PROVIDER_BIN_MISSING_CACHE_TTL_SECONDS
            )
            if cached_bin_name == bin_name and now - cached_at < ttl:
                return cached_available

        available = shutil.which(bin_name) is not None
        cache[provider] = (now, available, bin_name)
        self._provider_availability_cache = cache
        return available

    async def _ensure_provider_available(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        provider: str,
    ) -> bool:
        if self._provider_available(provider):
            return True
        provider_label = "Codex" if provider == "codex" else "Copilot"
        await send_text(
            update,
            context,
            (
                f"{provider_label} CLI not found: {self._provider_bin(provider)}\n"
                "Run /provider to choose an available provider or update the bot config."
            ),
        )
        return False

    def _build_provider_keyboard(self, current_provider: str) -> InlineKeyboardMarkup:
        def button_label(provider: str) -> str:
            provider_label = "Codex" if provider == "codex" else "Copilot"
            status = "available" if self._provider_available(provider) else "missing"
            marker = "current" if provider == current_provider else status
            return f"{provider_label} ({marker})"

        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(button_label("codex"), callback_data="provider:set:codex"),
                    InlineKeyboardButton(button_label("copilot"), callback_data="provider:set:copilot"),
                ]
            ]
        )

    def _active_session_matches_current_context(self, chat_state: dict[str, object]) -> bool:
        active_session_id = chat_state.get("active_session_id")
        if not active_session_id:
            return False
        session = chat_state.get("sessions", {}).get(active_session_id)
        if not isinstance(session, dict):
            return False
        return (
            session.get("project_folder") == chat_state.get("current_project_folder")
            and session.get("provider", "codex") == self._selected_provider(chat_state)
        )

    def _branch_discrepancy_keyboard(self, stored_branch: str, current_branch: str) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(f"use {stored_branch}", callback_data="branchdiscrepancy:stored"),
                    InlineKeyboardButton(f"use {current_branch}", callback_data="branchdiscrepancy:current"),
                ]
            ]
        )

    def _multi_branch_source_keyboard(
        self,
        *,
        new_branch: str,
        source_branches: list[str],
        project_path,
    ) -> InlineKeyboardMarkup | None:
        rows: list[list[InlineKeyboardButton]] = []
        seen: set[tuple[str, str]] = set()
        for source_branch in source_branches:
            if not source_branch:
                continue
            row: list[InlineKeyboardButton] = []
            if self.git.local_branch_exists(project_path, source_branch):
                key = ("local", source_branch)
                if key not in seen:
                    row.append(
                        InlineKeyboardButton(
                            f"local/{source_branch}",
                            callback_data=f"branchsource:local:{source_branch}:{new_branch}",
                        )
                    )
                    seen.add(key)
            if self.git.remote_branch_exists(project_path, source_branch):
                key = ("origin", source_branch)
                if key not in seen:
                    row.append(
                        InlineKeyboardButton(
                            f"origin/{source_branch}",
                            callback_data=f"branchsource:origin:{source_branch}:{new_branch}",
                        )
                    )
                    seen.add(key)
            if row:
                rows.append(row)
        if not rows:
            return None
        return InlineKeyboardMarkup(rows)

    async def _offer_branch_source_fallback(
        self,
        query,
        *,
        project_folder: str,
        project_path,
        source_kind: str,
        source_branch: str,
        new_branch: str,
        error_message: str,
    ) -> bool:
        if source_kind != "origin":
            return False

        current_branch = str(self.git.current_branch(project_path) or "").strip()
        default_branch = str(self.git.default_branch(project_path) or "").strip()
        keyboard = self._multi_branch_source_keyboard(
            new_branch=new_branch,
            source_branches=[default_branch, current_branch],
            project_path=project_path,
        )
        if keyboard is None:
            return False

        lines = [
            error_message.strip(),
            "",
            f"Do you want to create branch {new_branch} from one of these branches instead of origin/{source_branch}?",
            f"Project: {project_folder}",
            f"Branch target: {new_branch}",
        ]
        if default_branch:
            lines.append(f"Default branch: {default_branch}")
        if current_branch and current_branch != default_branch:
            lines.append(f"Current branch in repo: {current_branch}")
        await query.edit_message_text("\n".join(lines), reply_markup=keyboard)
        return True

    async def _prompt_branch_discrepancy(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        *,
        session_name: str,
        project_folder: str,
        stored_branch: str,
        current_branch: str,
    ) -> None:
        if update.effective_chat is not None:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=(
                    "Branch discrepancy detected before running the active session.\n"
                    f"Session: {session_name}\n"
                    f"Project: {project_folder}\n"
                    f"Stored branch: {stored_branch}\n"
                    f"Current branch in repo: {current_branch}\n\n"
                    "Choose which branch to use."
                ),
                reply_markup=self._branch_discrepancy_keyboard(stored_branch, current_branch),
            )

    async def _resolve_branch_discrepancy_if_needed(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> bool:
        chat_id = update.effective_chat.id
        pending_action = self._pending_action(chat_id)
        if not pending_action:
            return True

        branch_resolution = pending_action.get("branch_resolution")
        if not isinstance(branch_resolution, dict):
            return True

        chat_state = self.deps.store.get_chat_state(self.deps.bot_id, chat_id)
        active_session_id = chat_state.get("active_session_id")
        if not active_session_id:
            self._store_pending_action(chat_id, None)
            return False
        session = chat_state.get("sessions", {}).get(active_session_id)
        if not isinstance(session, dict):
            self._store_pending_action(chat_id, None)
            return False

        project_folder = str(session.get("project_folder") or "").strip()
        project_path = resolve_project_path(self.deps.cfg.workspace_root, project_folder)
        if not project_path.exists() or not project_path.is_dir():
            await send_text(update, context, f"Project folder does not exist: {project_folder}\nRun /project {project_folder} again.")
            return False

        if branch_resolution.get("kind") == "discrepancy":
            stored_branch = str(branch_resolution.get("stored_branch") or "").strip()
            current_branch = str(branch_resolution.get("current_branch") or "").strip()
            if not stored_branch or not current_branch:
                return True
            await self._prompt_branch_discrepancy(
                update,
                context,
                session_name=str(session.get("name") or active_session_id),
                project_folder=project_folder,
                stored_branch=stored_branch,
                current_branch=current_branch,
            )
            return False

        return True

    def _pending_action(self, chat_id: int) -> dict[str, object] | None:
        chat_state = self.deps.store.get_chat_state(self.deps.bot_id, chat_id)
        pending_action = chat_state.get("pending_action")
        return pending_action if isinstance(pending_action, dict) else None

    def _store_pending_action(self, chat_id: int, pending_action: dict[str, object] | None) -> None:
        self.deps.store.set_pending_action(self.deps.bot_id, chat_id, pending_action)

    def _auto_session_name(self, project_folder: str, branch_name: str, provider: str, chat_id: int) -> str:
        branch_label = (branch_name or "current").replace("/", "-")
        base_name = f"{project_folder}-{branch_label}-{provider}"
        if self._next_available_session_name(chat_id, base_name) == base_name:
            return base_name
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        fallback_name = f"{base_name}-{timestamp}"
        return self._next_available_session_name(chat_id, fallback_name)

    async def _prompt_for_provider_selection(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        *,
        prompt_text: str,
        pending_action: dict[str, object] | None,
    ) -> None:
        chat_id = update.effective_chat.id
        self._store_pending_action(chat_id, pending_action)
        current_provider = self._selected_provider(self.deps.store.get_chat_state(self.deps.bot_id, chat_id))
        if update.effective_chat is not None:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=prompt_text,
                reply_markup=self._build_provider_keyboard(current_provider),
            )

    async def _resolve_session_prerequisites(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        *,
        pending_action: dict[str, object] | None,
    ) -> tuple[str, str, str, object] | None:
        chat_id = update.effective_chat.id
        chat_state = self.deps.store.get_chat_state(self.deps.bot_id, chat_id)
        provider = self._selected_provider(chat_state)
        if not provider:
            await self._prompt_for_provider_selection(
                update,
                context,
                prompt_text="Provider selection is required before creating or continuing a session.",
                pending_action=pending_action,
            )
            return None
        if not await self._ensure_provider_available(update, context, provider):
            return None

        project_folder = str(chat_state.get("current_project_folder") or "").strip()
        if not project_folder:
            self._store_pending_action(chat_id, pending_action)
            await send_text(
                update,
                context,
                "No project selected.\nPlease run /project <project_folder> first.\nExample: /project backend",
            )
            return None

        project_path = resolve_project_path(self.deps.cfg.workspace_root, project_folder)
        if not project_path.exists() or not project_path.is_dir():
            self._store_pending_action(chat_id, pending_action)
            await send_text(update, context, f"Project folder does not exist: {project_folder}\nRun /project {project_folder} again.")
            return None

        branch_name = str(chat_state.get("current_branch") or "").strip()
        if self.git.is_git_repo(project_path) and not branch_name:
            self._store_pending_action(chat_id, pending_action)
            await self._send_branch_selection_prompt(
                update,
                context,
                project_folder=project_folder,
                project_path=project_path,
                intro_lines=["Branch selection is required before creating or continuing a session.", ""],
            )
            return None

        return provider, project_folder, branch_name, project_path

    async def _create_session_for_context(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        *,
        session_name: str | None,
        use_session_id_as_name: bool,
        provider: str,
        project_folder: str,
        branch_name: str,
        project_path,
    ) -> bool:
        chat_id = update.effective_chat.id
        requested_session_name = (session_name or "").strip()
        creation_label = requested_session_name or "new session"
        final_session_name = requested_session_name
        if not use_session_id_as_name and not final_session_name:
            final_session_name = self._auto_session_name(project_folder, branch_name, provider, chat_id)

        existing_sessions = self.deps.store.list_sessions(self.deps.bot_id, chat_id)
        if final_session_name and any(
            data.get("name", "").strip().lower() == final_session_name.lower() for data in existing_sessions.values()
        ):
            await send_text(
                update,
                context,
                f"Session name already exists: {final_session_name}\nPlease use a different session name.",
            )
            return False

        logger.info(
            "Creating session '%s' for chat %s in project '%s' with provider '%s'.",
            creation_label,
            chat_id,
            project_folder,
            provider,
        )
        await send_text(update, context, "Creating session...")
        result = await self._run_with_typing(
            update,
            context,
            self.deps.agent_runner.create_session,
            provider,
            project_path,
            f"Create session: {creation_label}",
            workspace_lock_key=project_folder,
            skip_git_repo_check=self.runtime.should_skip_git_repo_check(project_folder),
            stall_message=(
                "Session creation appears stuck.\n"
                "The local agent process is still running but has not produced output.\n"
                "On macOS this often means a hidden permission dialog is waiting for input on the machine running the bot."
            ),
        )

        if not result.success or not result.session_id:
            await send_text(update, context, result.error_message or "Failed to create a session.")
            return False

        if use_session_id_as_name:
            final_session_name = result.session_id

        self.deps.store.create_session(
            self.deps.bot_id,
            chat_id,
            result.session_id,
            final_session_name,
            project_folder,
            provider,
            branch_name=branch_name,
        )
        logger.info(
            "Created session '%s' (%s) for chat %s in project '%s'.",
            final_session_name,
            result.session_id,
            chat_id,
            project_folder,
        )
        await send_text(
            update,
            context,
            (
                f"Session created successfully: {final_session_name}\n"
                f"Session ID: {result.session_id}\n"
                f"Project: {project_folder}\n"
                f"Provider: {provider}\n"
                f"Branch: {branch_name or '(current branch)'}"
            ),
        )
        return True

    async def _continue_pending_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        chat_id = update.effective_chat.id
        pending_action = self._pending_action(chat_id)
        if not pending_action:
            return False

        resolved = await self._resolve_session_prerequisites(update, context, pending_action=pending_action)
        if resolved is None:
            return False
        provider, project_folder, branch_name, project_path = resolved
        kind = str(pending_action.get("kind") or "")

        if kind == "new_session":
            if await self._create_session_for_context(
                update,
                context,
                session_name=str(pending_action.get("session_name") or "").strip() or None,
                use_session_id_as_name=bool(pending_action.get("use_session_id_as_name")),
                provider=provider,
                project_folder=project_folder,
                branch_name=branch_name,
                project_path=project_path,
            ):
                self._store_pending_action(chat_id, None)
                return True
            return False

        if kind == "message":
            user_message = str(pending_action.get("user_message") or "").strip()
            if not user_message:
                self._store_pending_action(chat_id, None)
                return False
            chat_state = self.deps.store.get_chat_state(self.deps.bot_id, chat_id)
            if not self._active_session_matches_current_context(chat_state):
                if not await self._create_session_for_context(
                    update,
                    context,
                    session_name=str(pending_action.get("session_name") or "").strip() or None,
                    use_session_id_as_name=False,
                    provider=provider,
                    project_folder=project_folder,
                    branch_name=branch_name,
                    project_path=project_path,
                ):
                    return False
            if not await self._ensure_active_session_ready_for_run(update, context):
                return False
            self._store_pending_action(chat_id, None)
            self._last_run_results[chat_id] = await self.runtime.run_active_session(update, context, user_message=user_message)
            return True

        self._store_pending_action(chat_id, None)
        return False

    async def _ensure_active_session_ready_for_run(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        chat_id = update.effective_chat.id
        chat_state = self.deps.store.get_chat_state(self.deps.bot_id, chat_id)
        active_session_id = chat_state.get("active_session_id")
        if not active_session_id:
            return False
        session = chat_state.get("sessions", {}).get(active_session_id)
        if not isinstance(session, dict):
            return False

        project_folder = str(session.get("project_folder") or "").strip()
        project_path = resolve_project_path(self.deps.cfg.workspace_root, project_folder)
        if not project_path.exists() or not project_path.is_dir():
            await send_text(update, context, f"Project folder does not exist: {project_folder}\nRun /project {project_folder} again.")
            return False
        if not self.git.is_git_repo(project_path):
            return True

        stored_branch = str(session.get("branch_name") or "").strip()
        current_branch = str(self.git.current_branch(project_path) or "").strip()
        if not stored_branch or not current_branch or stored_branch == current_branch:
            return True

        pending_action = self._pending_action(chat_id)
        if pending_action is None:
            return True
        branch_resolution = pending_action.get("branch_resolution")
        if isinstance(branch_resolution, dict) and branch_resolution.get("kind") == "discrepancy":
            return await self._resolve_branch_discrepancy_if_needed(update, context)

        pending_action = dict(pending_action)
        pending_action["branch_resolution"] = {
            "kind": "discrepancy",
            "session_id": active_session_id,
            "stored_branch": stored_branch,
            "current_branch": current_branch,
        }
        self._store_pending_action(chat_id, pending_action)
        await self._prompt_branch_discrepancy(
            update,
            context,
            session_name=str(session.get("name") or active_session_id),
            project_folder=project_folder,
            stored_branch=stored_branch,
            current_branch=current_branch,
        )
        return False

    @require_allowed_chat()
    async def handle_new(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self._notify_if_current_project_busy(update, context):
            return
        chat_id = update.effective_chat.id
        session_name = " ".join(context.args).strip() or None
        self._store_pending_action(
            chat_id,
            {
                "kind": "new_session",
                "session_name": session_name,
                "use_session_id_as_name": not bool(session_name),
            },
        )
        await self._continue_pending_action(update, context)

    @require_allowed_chat()
    async def handle_provider(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self._notify_if_current_project_busy(update, context):
            return
        if context.args:
            await send_text(update, context, "Usage: /provider")
            return

        chat_id = update.effective_chat.id
        chat_state = self.deps.store.get_chat_state(self.deps.bot_id, chat_id)
        current_provider = self._selected_provider(chat_state)
        if update.effective_chat is not None:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=(
                    f"Current provider: {current_provider or '(not selected)'}\n"
                    "Choose the provider for new sessions."
                ),
                reply_markup=self._build_provider_keyboard(current_provider),
            )

    @require_allowed_chat(answer_callback=True)
    async def handle_provider_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if query is None or query.data is None:
            return

        await query.answer()
        if await self._notify_if_current_project_busy(update, context):
            return
        _, _, provider = query.data.partition("provider:set:")
        if provider not in {"codex", "copilot"}:
            return

        chat_id = update.effective_chat.id
        previous_provider = self._selected_provider(self.deps.store.get_chat_state(self.deps.bot_id, chat_id))
        if not self._provider_available(provider):
            provider_label = "Codex" if provider == "codex" else "Copilot"
            await query.edit_message_text(
                f"{provider_label} CLI not found: {self._provider_bin(provider)}\nUpdate the bot config or install that CLI first."
            )
            return

        self.deps.store.set_current_provider(self.deps.bot_id, chat_id, provider)
        await query.edit_message_text(f"Current provider set to: {provider}")
        if previous_provider != provider and not self._pending_action(chat_id):
            self._store_pending_action(
                chat_id,
                {
                    "kind": "new_session",
                    "session_name": None,
                    "use_session_id_as_name": True,
                },
            )
        await self._continue_pending_action(update, context)

    @require_allowed_chat(answer_callback=True)
    async def handle_branch_discrepancy_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if query is None or query.data is None:
            return

        await query.answer()
        choice = query.data.partition("branchdiscrepancy:")[2]
        if choice not in {"stored", "current"}:
            return

        chat_id = update.effective_chat.id
        pending_action = self._pending_action(chat_id)
        if pending_action is None:
            await query.edit_message_text("No pending branch decision was found.")
            return
        branch_resolution = pending_action.get("branch_resolution")
        if not isinstance(branch_resolution, dict) or branch_resolution.get("kind") != "discrepancy":
            await query.edit_message_text("No pending branch discrepancy was found.")
            return

        chat_state = self.deps.store.get_chat_state(self.deps.bot_id, chat_id)
        active_session_id = chat_state.get("active_session_id")
        session = chat_state.get("sessions", {}).get(active_session_id) if active_session_id else None
        if not isinstance(session, dict):
            await query.edit_message_text("No active session is available.")
            return

        project_folder = str(session.get("project_folder") or "").strip()
        project_path = resolve_project_path(self.deps.cfg.workspace_root, project_folder)
        if not project_path.exists() or not project_path.is_dir():
            await query.edit_message_text(f"Project folder does not exist: {project_folder}\nRun /project {project_folder} again.")
            return

        stored_branch = str(branch_resolution.get("stored_branch") or "").strip()
        current_branch = str(branch_resolution.get("current_branch") or "").strip()
        if choice == "current":
            self.deps.store.set_current_branch(self.deps.bot_id, chat_id, current_branch or None)
            self.deps.store.set_active_session_branch(self.deps.bot_id, chat_id, current_branch)
            pending_action = dict(pending_action)
            pending_action.pop("branch_resolution", None)
            self._store_pending_action(chat_id, pending_action)
            await query.edit_message_text(f"Using current branch: {current_branch}")
            await self._continue_pending_action(update, context)
            return

        allow_local = self.git.local_branch_exists(project_path, stored_branch)
        allow_origin = self.git.remote_branch_exists(project_path, stored_branch)
        if not allow_local and not allow_origin:
            default_branch = str(self.git.default_branch(project_path) or "").strip()
            keyboard = self._multi_branch_source_keyboard(
                new_branch=stored_branch,
                source_branches=[default_branch, current_branch],
                project_path=project_path,
            )
            if keyboard is None:
                await query.edit_message_text(
                    (
                        f"Stored branch is no longer available: {stored_branch}\n"
                        "No fallback source branch is available."
                    )
                )
                return
            pending_action = dict(pending_action)
            pending_action["branch_resolution"] = {
                "kind": "switch_source",
                "new_branch": stored_branch,
            }
            self._store_pending_action(chat_id, pending_action)
            fallback_lines = [
                "Stored branch is no longer available.",
                f"Missing local/{stored_branch} and origin/{stored_branch}.",
                "",
                f"Do you want to create branch {stored_branch} from one of these branches?",
                f"Project: {project_folder}",
                f"Branch target: {stored_branch}",
            ]
            if default_branch:
                fallback_lines.append(f"Default branch: {default_branch}")
            if current_branch and current_branch != default_branch:
                fallback_lines.append(f"Current branch in repo: {current_branch}")
            await query.edit_message_text(
                "\n".join(fallback_lines),
                reply_markup=keyboard,
            )
            return
        pending_action = dict(pending_action)
        pending_action["branch_resolution"] = {
            "kind": "switch_source",
            "source_branch": stored_branch,
            "new_branch": stored_branch,
        }
        self._store_pending_action(chat_id, pending_action)
        await query.edit_message_text(
            (
                "Choose how to restore the stored branch.\n"
                f"Project: {project_folder}\n"
                f"Branch target: {stored_branch}"
            ),
            reply_markup=self._branch_source_keyboard(
                source_branch=stored_branch,
                new_branch=stored_branch,
                allow_local=allow_local,
                allow_origin=allow_origin,
            ),
        )

    @require_allowed_chat()
    async def handle_current(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_chat.id
        active_id, session = await self._active_session_or_notify(update, context)
        if active_id is None or session is None:
            return

        logger.info(
            "Reported current session '%s' (%s) for chat %s.",
            session["name"],
            active_id,
            chat_id,
        )
        await send_text(
            update,
            context,
            (
                f"Current session: {session['name']}\n"
                f"Session ID: {active_id}\n"
                f"Project: {session['project_folder']}\n"
                f"Provider: {session.get('provider', 'codex')}\n"
                f"Branch: {session.get('branch_name') or '(current branch)'}"
            ),
        )

    @require_allowed_chat()
    async def handle_abort(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if context.args:
            await send_text(update, context, "Usage: /abort")
            return

        chat_id = update.effective_chat.id
        chat_state = self.deps.store.get_chat_state(self.deps.bot_id, chat_id)
        project_folder = str(chat_state.get("current_project_folder") or "").strip()
        if not project_folder:
            await send_text(update, context, "No project selected.\nPlease run /project <project_folder> first.")
            return

        project_path = resolve_project_path(self.deps.cfg.workspace_root, project_folder)
        if not project_path.exists() or not project_path.is_dir():
            await send_text(update, context, f"Project folder does not exist: {project_folder}\nRun /project {project_folder} again.")
            return

        aborted = await asyncio.to_thread(self.deps.agent_runner.abort_running_process, project_path)
        if not aborted:
            await send_text(update, context, "No running agent process was found for the current project.")
            return
        await send_text(update, context, "Abort signal sent for the current project run.")

    @require_allowed_chat(answer_callback=True)
    async def handle_queue_continue_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if query is None or query.data is None:
            return

        await query.answer()
        _, _, decision = query.data.partition("queuecontinue:")
        chat_id = update.effective_chat.id
        if decision == "yes":
            await query.edit_message_text("Continuing with the pending queued questions.")
            await self._drain_chat_message_queue(chat_id, context)
            return
        if decision == "no":
            self._clear_chat_message_queue(chat_id)
            await query.edit_message_text("Pending queued questions were discarded.")
