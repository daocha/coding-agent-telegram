from __future__ import annotations

import shutil
import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from coding_agent_telegram.telegram_sender import send_text

from .base import require_allowed_chat


class SessionProviderCommandMixin:
    PROVIDER_BIN_AVAILABLE_CACHE_TTL_SECONDS = 12 * 60 * 60
    PROVIDER_BIN_MISSING_CACHE_TTL_SECONDS = 5 * 60

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
