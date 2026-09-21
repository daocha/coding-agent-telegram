from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from coding_agent_telegram.telegram_sender import send_text

from .base import require_allowed_chat
from .session_lifecycle_commands import SESSION_PRIMING_PROMPT


class SessionModelCommandMixin:
    def _configured_default_model(self, provider: str) -> str:
        if provider == "codex":
            return self.deps.cfg.codex_model
        if provider == "claude":
            return self.deps.cfg.claude_model
        return self.deps.cfg.copilot_model

    def _model_choices(self, provider: str) -> tuple[str, ...]:
        if provider == "codex":
            return self.deps.cfg.codex_model_choices
        if provider == "claude":
            return self.deps.cfg.claude_model_choices
        return self.deps.cfg.copilot_model_choices

    def _default_model_label(self, provider: str) -> str:
        return self._configured_default_model(provider) or self._t(None, "model.cli_default")

    def _build_model_keyboard(self, provider: str, current_model: str) -> InlineKeyboardMarkup:
        def marker(model: str) -> str:
            return f" ({self._t(None, 'model.status_current')})" if model == current_model else ""

        default_label = f"{self._t(None, 'model.default_option')} [{self._default_model_label(provider)}]"
        rows = [
            [
                InlineKeyboardButton(
                    f"{default_label}{marker('')}",
                    callback_data="model:default",
                    api_kwargs={"style": "success"},
                )
            ]
        ]
        # Encode the choice's position rather than the model string itself: some
        # vendor model ids are long enough that "model:set:<id>" would exceed
        # Telegram's 64-byte callback_data limit and silently break the keyboard.
        rows.extend(
            [
                InlineKeyboardButton(
                    f"{model}{marker(model)}",
                    callback_data=f"model:set:{index}",
                    api_kwargs={"style": "success"},
                )
            ]
            for index, model in enumerate(self._model_choices(provider))
        )
        return InlineKeyboardMarkup(rows)

    @require_allowed_chat()
    async def handle_model(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self._notify_if_current_project_busy(update, context):
            return

        chat_id = update.effective_chat.id
        active_id, session, project_path = self._active_session_context(chat_id)
        if session is None:
            await send_text(update, context, self._t(update, "common.no_active_session"))
            return

        if len(context.args) > 1:
            await send_text(update, context, self._t(update, "model.usage_model"))
            return

        provider = session.get("provider", "codex")

        if context.args:
            model = context.args[0].strip()
            if not model:
                await send_text(update, context, self._t(update, "model.usage_model"))
                return
            await self._validate_and_set_model(
                update,
                context,
                chat_id=chat_id,
                active_id=active_id,
                session=session,
                project_path=project_path,
                provider=provider,
                model=model,
            )
            return

        current_model = (session.get("model") or "").strip()
        is_custom = bool(current_model) and current_model not in self._model_choices(provider)
        prompt_key = "model.current_model_prompt_custom" if is_custom else "model.current_model_prompt"
        await context.bot.send_message(
            chat_id=chat_id,
            text=self._t(
                update,
                prompt_key,
                model=current_model or self._default_model_label(provider),
            ),
            reply_markup=self._build_model_keyboard(provider, current_model),
        )

    async def _validate_and_set_model(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        *,
        chat_id: int,
        active_id: str,
        session: dict,
        project_path,
        provider: str,
        model: str,
    ) -> None:
        # Models already on the curated list came from the button picker or the
        # operator's config, so there is no need to re-probe the CLI for them.
        if model in self._model_choices(provider):
            self.deps.store.set_session_model(self.deps.bot_id, chat_id, active_id, model)
            await send_text(update, context, self._t(update, "model.current_model_set", model=model))
            return

        project_folder = session["project_folder"]
        if not project_path.exists() or not project_path.is_dir():
            await send_text(
                update,
                context,
                self._t(update, "project.project_folder_missing_retry", project_folder=project_folder),
            )
            return

        await send_text(update, context, self._t(update, "model.validating", model=model))
        # A throwaway, read-only priming call is the only way to find out whether a CLI
        # accepts a given --model value -- none of the providers expose a way to list or
        # validate model ids up front. Nothing is persisted unless this succeeds.
        result = await self._run_with_typing(
            update,
            context,
            self.deps.agent_runner.create_session,
            provider,
            project_path,
            SESSION_PRIMING_PROMPT,
            workspace_lock_key=project_folder,
            skip_git_repo_check=self.runtime.should_skip_git_repo_check(project_folder),
            priming_only=True,
            model=model,
            stall_message=self._t(update, "runtime.replacement_session_stall"),
        )
        if result is None:
            return

        if not result.success or not result.session_id:
            error_text = result.error_message or self._t(update, "model.invalid_model_generic")
            await send_text(update, context, self._t(update, "model.invalid_model", model=model, error=error_text))
            return

        self.deps.store.set_session_model(self.deps.bot_id, chat_id, active_id, model)
        await send_text(update, context, self._t(update, "model.current_model_set", model=model))

    @require_allowed_chat(answer_callback=True)
    async def handle_model_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if query is None or query.data is None:
            return

        await query.answer()
        if await self._notify_if_current_project_busy(update, context):
            return

        chat_id = update.effective_chat.id
        active_id, session, _ = self._active_session_context(chat_id)
        if session is None:
            await query.edit_message_text(self._t(update, "common.no_active_session"))
            return

        provider = session.get("provider", "codex")
        data = query.data

        if data == "model:default":
            model = ""
        else:
            _, _, index_text = data.partition("model:set:")
            choices = self._model_choices(provider)
            try:
                index = int(index_text)
            except ValueError:
                index = -1
            if not (0 <= index < len(choices)):
                # The list or provider changed since this keyboard was rendered
                # (e.g. an operator edited *_MODEL_CHOICES, or /provider was run
                # in between) -- tell the user instead of silently doing nothing.
                await query.edit_message_text(self._t(update, "model.stale_selection"))
                return
            model = choices[index]

        self.deps.store.set_session_model(self.deps.bot_id, chat_id, active_id, model)
        await query.edit_message_text(
            self._t(
                update,
                "model.current_model_set",
                model=model or self._default_model_label(provider),
            )
        )
