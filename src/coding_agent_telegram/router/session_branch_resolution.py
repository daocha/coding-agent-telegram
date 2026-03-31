from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from coding_agent_telegram.filters import resolve_project_path
from coding_agent_telegram.telegram_sender import send_text

from .base import require_allowed_chat


class SessionBranchResolutionMixin:
    def _branch_discrepancy_keyboard(self, update: Update, stored_branch: str, current_branch: str) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        self._t(update, "branch_resolution.use_branch", branch_name=stored_branch),
                        callback_data="branchdiscrepancy:stored",
                    ),
                    InlineKeyboardButton(
                        self._t(update, "branch_resolution.use_branch", branch_name=current_branch),
                        callback_data="branchdiscrepancy:current",
                    ),
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
            self._t(None, "branch_resolution.create_from_instead_of_origin", new_branch=new_branch, source_branch=source_branch),
            self._t(None, "project.project_label", project_folder=project_folder),
            self._t(None, "project.branch_target_label", new_branch=new_branch),
        ]
        if default_branch:
            lines.append(self._t(None, "project.default_branch_label", branch_name=default_branch))
        if current_branch and current_branch != default_branch:
            lines.append(self._t(None, "project.current_branch_in_repo_label", branch_name=current_branch))
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
                text="\n".join(
                    [
                        self._t(update, "branch_resolution.discrepancy_detected"),
                        self._t(update, "branch_resolution.session_label", session_name=session_name),
                        self._t(update, "project.project_label", project_folder=project_folder),
                        self._t(update, "branch_resolution.stored_branch_label", branch_name=stored_branch),
                        self._t(update, "project.current_branch_in_repo_label", branch_name=current_branch),
                        "",
                        self._t(update, "branch_resolution.choose_branch_to_use"),
                    ]
                ),
                reply_markup=self._branch_discrepancy_keyboard(update, stored_branch, current_branch),
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
            await send_text(
                update,
                context,
                self._t(update, "project.project_folder_missing_retry", project_folder=project_folder),
            )
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
            await query.edit_message_text(self._t(update, "branch_resolution.no_pending_decision"))
            return
        branch_resolution = pending_action.get("branch_resolution")
        if not isinstance(branch_resolution, dict) or branch_resolution.get("kind") != "discrepancy":
            await query.edit_message_text(self._t(update, "branch_resolution.no_pending_discrepancy"))
            return

        chat_state = self.deps.store.get_chat_state(self.deps.bot_id, chat_id)
        active_session_id = chat_state.get("active_session_id")
        session = chat_state.get("sessions", {}).get(active_session_id) if active_session_id else None
        if not isinstance(session, dict):
            await query.edit_message_text(self._t(update, "branch_resolution.no_active_session"))
            return

        project_folder = str(session.get("project_folder") or "").strip()
        project_path = resolve_project_path(self.deps.cfg.workspace_root, project_folder)
        if not project_path.exists() or not project_path.is_dir():
            await query.edit_message_text(
                self._t(update, "project.project_folder_missing_retry", project_folder=project_folder)
            )
            return

        stored_branch = str(branch_resolution.get("stored_branch") or "").strip()
        current_branch = str(branch_resolution.get("current_branch") or "").strip()
        if choice == "current":
            self.deps.store.set_current_branch(self.deps.bot_id, chat_id, current_branch or None)
            self.deps.store.set_active_session_branch(self.deps.bot_id, chat_id, current_branch)
            pending_action = dict(pending_action)
            pending_action.pop("branch_resolution", None)
            self._store_pending_action(chat_id, pending_action)
            await query.edit_message_text(self._t(update, "branch_resolution.using_current_branch", branch_name=current_branch))
            await self._continue_pending_action(update, context, drain_queue_after_completion=True)
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
                    self._t(update, "branch_resolution.stored_branch_unavailable_no_fallback", branch_name=stored_branch)
                )
                return
            pending_action = dict(pending_action)
            pending_action["branch_resolution"] = {
                "kind": "switch_source",
                "new_branch": stored_branch,
            }
            self._store_pending_action(chat_id, pending_action)
            fallback_lines = [
                self._t(update, "branch_resolution.stored_branch_unavailable"),
                self._t(update, "branch_resolution.missing_local_and_origin", branch_name=stored_branch),
                "",
                self._t(update, "branch_resolution.create_branch_from_choices", branch_name=stored_branch),
                self._t(update, "project.project_label", project_folder=project_folder),
                self._t(update, "project.branch_target_label", new_branch=stored_branch),
            ]
            if default_branch:
                fallback_lines.append(self._t(update, "project.default_branch_label", branch_name=default_branch))
            if current_branch and current_branch != default_branch:
                fallback_lines.append(self._t(update, "project.current_branch_in_repo_label", branch_name=current_branch))
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
            "\n".join(
                [
                    self._t(update, "branch_resolution.choose_restore_method"),
                    self._t(update, "project.project_label", project_folder=project_folder),
                    self._t(update, "project.branch_target_label", new_branch=stored_branch),
                ]
            ),
            reply_markup=self._branch_source_keyboard(
                source_branch=stored_branch,
                new_branch=stored_branch,
                allow_local=allow_local,
                allow_origin=allow_origin,
            ),
        )
