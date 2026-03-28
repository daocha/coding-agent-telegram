from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from coding_agent_telegram.filters import resolve_project_path
from coding_agent_telegram.telegram_sender import send_text

from .base import logger, require_allowed_chat


class SessionLifecycleCommandMixin:
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
                prompt_text=self._t(update, "lifecycle.provider_selection_required"),
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
                self._t(update, "lifecycle.no_project_selected_example"),
            )
            return None

        project_path = resolve_project_path(self.deps.cfg.workspace_root, project_folder)
        if not project_path.exists() or not project_path.is_dir():
            self._store_pending_action(chat_id, pending_action)
            await send_text(update, context, self._t(update, "project.project_folder_missing_retry", project_folder=project_folder))
            return None

        branch_name = str(chat_state.get("current_branch") or "").strip()
        if self.git.is_git_repo(project_path) and not branch_name:
            self._store_pending_action(chat_id, pending_action)
            await self._send_branch_selection_prompt(
                update,
                context,
                project_folder=project_folder,
                project_path=project_path,
                intro_lines=[self._t(update, "project.branch_selection_required"), ""],
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
                self._t(update, "lifecycle.session_name_exists", session_name=final_session_name),
            )
            return False

        logger.info(
            "Creating session '%s' for chat %s in project '%s' with provider '%s'.",
            creation_label,
            chat_id,
            project_folder,
            provider,
        )
        await send_text(update, context, self._t(update, "lifecycle.creating_session"))
        result = await self._run_with_typing(
            update,
            context,
            self.deps.agent_runner.create_session,
            provider,
            project_path,
            f"Create session: {creation_label}",
            workspace_lock_key=project_folder,
            skip_git_repo_check=self.runtime.should_skip_git_repo_check(project_folder),
            stall_message=self._t(update, "runtime.replacement_session_stall"),
        )

        if not result.success or not result.session_id:
            await send_text(update, context, result.error_message or self._t(update, "lifecycle.failed_create_session"))
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
            self._t(
                update,
                "lifecycle.session_created_successfully",
                session_name=final_session_name,
                session_id=result.session_id,
                project_folder=project_folder,
                provider=provider,
                branch_name=branch_name or self._t(update, "status.current_branch_placeholder"),
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
            await send_text(update, context, self._t(update, "project.project_folder_missing_retry", project_folder=project_folder))
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
