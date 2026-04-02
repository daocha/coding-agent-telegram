from __future__ import annotations
import html

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from coding_agent_telegram.filters import resolve_project_path
from coding_agent_telegram.i18n import translate
from coding_agent_telegram.native_sessions import discover_native_project_sessions
from coding_agent_telegram.telegram_sender import send_html_text, send_text

from .base import logger, require_allowed_chat


class SwitchCommandMixin:
    def _switch_origin_label(self, chat_id: int, origin: str) -> str:
        key = "switch.source_native_cli" if origin == "native" else "switch.source_bot_managed"
        return translate(self._chat_locale(chat_id), key)

    def _switch_status_label(self, chat_id: int, status: str) -> str:
        key = "switch.status_active" if status == "active" else "switch.status_idle"
        return translate(self._chat_locale(chat_id), key)

    def _switch_listing_entries(self, chat_id: int) -> tuple[list[dict[str, str]], str | None]:
        chat_state = self.deps.store.get_chat_state(self.deps.bot_id, chat_id)
        bot_sessions = self.deps.store.list_sessions(self.deps.bot_id, chat_id)
        active_session_id = chat_state.get("active_session_id")
        entries: list[dict[str, str]] = []
        seen_session_ids = set()

        for session_id, data in self._sorted_sessions(bot_sessions):
            seen_session_ids.add(session_id)
            origin = data.get("origin", "bot")
            entries.append(
                {
                    "session_id": session_id,
                    "name": data["name"],
                    "project_folder": data["project_folder"],
                    "provider": data.get("provider", "codex"),
                    "branch_name": data.get("branch_name") or "",
                    "updated_at": data.get("updated_at") or data.get("created_at") or "",
                    "created_at": data.get("created_at") or "",
                    "origin": origin,
                    "origin_label": data.get("origin_label", "Bot managed session"),
                    "initialized_from": data.get("initialized_from", "Bot-managed session from state.json"),
                    "status": "active" if session_id == active_session_id else "idle",
                }
            )

        current_project_folder = str(chat_state.get("current_project_folder") or "").strip()
        current_provider = str(chat_state.get("current_provider") or "").strip().lower()
        if not current_project_folder:
            return entries, None

        project_path = resolve_project_path(self.deps.cfg.workspace_root, current_project_folder)
        if not project_path.exists() or not project_path.is_dir():
            return entries, current_project_folder

        native_sessions = discover_native_project_sessions(
            project_path,
            current_project_folder,
            provider=current_provider or None,
        )
        for session_id, record in sorted(
            native_sessions.items(),
            key=lambda item: (item[1].updated_at or item[1].created_at, item[0]),
            reverse=True,
        ):
            if session_id in seen_session_ids:
                continue
            entries.append(
                {
                    "session_id": session_id,
                    "name": record.name,
                    "project_folder": record.project_folder,
                    "provider": record.provider,
                    "branch_name": record.branch_name,
                    "updated_at": record.updated_at,
                    "created_at": record.created_at,
                    "origin": "native",
                    "origin_label": record.source_label,
                    "initialized_from": record.initialized_from,
                    "status": "active" if session_id == active_session_id else "idle",
                }
            )
        entries.sort(key=lambda item: (item["updated_at"] or item["created_at"], item["session_id"]), reverse=True)
        return entries, current_project_folder

    def _build_switch_page_from_entries(
        self,
        chat_id: int,
        entries: list[dict[str, str]],
        current_project_folder: str | None,
        page: int,
    ) -> tuple[str, InlineKeyboardMarkup | None]:
        locale = self._chat_locale(chat_id)
        total_sessions = len(entries)
        total_pages = max(1, (total_sessions + self.SWITCH_PAGE_SIZE - 1) // self.SWITCH_PAGE_SIZE)
        page = min(max(page, 1), total_pages)
        start = (page - 1) * self.SWITCH_PAGE_SIZE
        page_items = entries[start : start + self.SWITCH_PAGE_SIZE]

        project_line = (
            translate(locale, "switch.current_project_filter", project_folder=f"<code>{html.escape(current_project_folder)}</code>")
            if current_project_folder
            else translate(locale, "switch.current_project_filter_none")
        )
        lines = [
            translate(locale, "switch.available_sessions", page=page, total_pages=total_pages),
            "",
            f"🤖 = {translate(locale, 'switch.source_bot_managed')}",
            f"💻 = {translate(locale, 'switch.source_native_cli')}",
            project_line,
            "",
        ]
        for idx, entry in enumerate(page_items, start=start + 1):
            branch_name = entry["branch_name"] or "(current branch)"
            marker = "🤖" if entry["origin"] == "bot" else "💻"
            status_label = self._switch_status_label(chat_id, entry["status"])
            lines.append(
                f"{idx}. {marker} {html.escape(entry['name'])} | <code>{html.escape(entry['project_folder'])}</code> &lt;{html.escape(branch_name)}&gt; | {html.escape(entry['provider'])} | {html.escape(status_label)}"
            )
            lines.append(f"session_id: {entry['session_id']}")
            lines.append(f"{translate(locale, 'switch.initialized_label')}: {html.escape(entry['initialized_from'])}")
            lines.append("")

        lines.extend(
            [
                translate(locale, "switch.use_label"),
                "/switch &lt;session_id&gt;",
                translate(locale, "switch.native_import_note"),
            ]
        )
        reply_markup = None
        if total_pages > 1:
            nav_buttons: list[InlineKeyboardButton] = []
            if page > 1:
                nav_buttons.append(
                    InlineKeyboardButton(
                        translate(locale, "diff.button_prev_page"),
                        callback_data=f"switchpage:{page - 1}",
                    )
                )
            if page < total_pages:
                nav_buttons.append(
                    InlineKeyboardButton(
                        translate(locale, "diff.button_next_page"),
                        callback_data=f"switchpage:{page + 1}",
                    )
                )
            if nav_buttons:
                reply_markup = InlineKeyboardMarkup([nav_buttons])
        return "\n".join(lines).strip(), reply_markup

    @require_allowed_chat()
    async def handle_switch(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self._notify_if_current_project_busy(update, context):
            return
        chat_id = update.effective_chat.id
        entries, current_project_folder = self._switch_listing_entries(chat_id)

        if not context.args:
            if not entries:
                await send_text(update, context, self._t(update, "switch.no_sessions_found"))
                return
            logger.info("Listed sessions page 1 for chat %s (%d sessions total).", chat_id, len(entries))
            text, reply_markup = self._build_switch_page_from_entries(chat_id, entries, current_project_folder, 1)
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML",
                reply_markup=reply_markup,
            )
            return

        if len(context.args) == 2 and context.args[0].lower() == "page":
            if not entries:
                await send_text(update, context, self._t(update, "switch.no_sessions_found"))
                return
            try:
                page = int(context.args[1])
            except ValueError:
                await send_text(update, context, self._t(update, "switch.invalid_page_number"))
                return
            if page < 1:
                await send_text(update, context, self._t(update, "switch.invalid_page_number"))
                return
            logger.info("Listed sessions page %d for chat %s (%d sessions total).", page, chat_id, len(entries))
            text, reply_markup = self._build_switch_page_from_entries(chat_id, entries, current_project_folder, page)
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML",
                reply_markup=reply_markup,
            )
            return

        session_id = " ".join(context.args).strip()
        session = self.deps.store.get_session(self.deps.bot_id, chat_id, session_id)
        native_entries = {entry["session_id"]: entry for entry in entries if entry["origin"] == "native"}
        imported_from_native = False
        native_origin_label = ""
        native_initialized_from = ""
        if session is None and session_id in native_entries:
            native_entry = native_entries[session_id]
            self.deps.store.create_session(
                self.deps.bot_id,
                chat_id,
                native_entry["session_id"],
                native_entry["name"],
                native_entry["project_folder"],
                native_entry["provider"],
                branch_name=native_entry["branch_name"] or None,
                origin="native",
                origin_label=native_entry["origin_label"],
                initialized_from=native_entry["initialized_from"],
            )
            session = self.deps.store.get_session(self.deps.bot_id, chat_id, session_id)
            imported_from_native = session is not None
            native_origin_label = native_entry["origin_label"]
            native_initialized_from = native_entry["initialized_from"]
        if session is None:
            await send_text(update, context, self._t(update, "switch.session_not_found"))
            return

        project_path = resolve_project_path(self.deps.cfg.workspace_root, session["project_folder"])
        if not project_path.exists() or not project_path.is_dir():
            await send_text(
                update,
                context,
                self._t(update, "common.project_folder_missing", project_folder=session["project_folder"]),
            )
            return
        if not self.deps.store.switch_session(self.deps.bot_id, chat_id, session_id):
            await send_text(update, context, self._t(update, "switch.session_not_found"))
            return
        logger.info(
            "Switched chat %s to session '%s' (%s) in project '%s'.",
            chat_id,
            session["name"],
            session_id,
            session["project_folder"],
        )
        await send_html_text(
            update,
            context,
            (
                f"{self._t(update, 'switch.switched_to_session')}: {html.escape(session['name'])}\n"
                f"{self._t(update, 'switch.project_label')}: <code>{html.escape(session['project_folder'])}</code>\n"
                f"{self._t(update, 'switch.provider_label')}: {html.escape(session.get('provider', 'codex'))}\n"
                f"{self._t(update, 'switch.branch_label')}: {html.escape((session.get('branch_name') or '(current branch)'))}"
                + (
                    f"\n{self._t(update, 'switch.source_label')}: {html.escape(self._switch_origin_label(chat_id, 'native'))}"
                    f"\n{self._t(update, 'switch.initialized_label')}: {html.escape(native_initialized_from)}"
                    f"\n{self._t(update, 'switch.imported_into_state_json')}"
                    if imported_from_native
                    else (
                        f"\n{self._t(update, 'switch.source_label')}: {html.escape(self._switch_origin_label(chat_id, str(session.get('origin') or 'bot')))}\n"
                        f"{self._t(update, 'switch.initialized_label')}: {html.escape(str(session.get('initialized_from') or 'Bot-managed session from state.json'))}"
                    )
                )
            ),
        )

    @require_allowed_chat(answer_callback=True)
    async def handle_switch_page_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if query is None:
            return

        await query.answer()
        data = (query.data or "").strip()
        if not data.startswith("switchpage:"):
            return
        try:
            page = int(data.partition(":")[2])
        except ValueError:
            return
        if page < 1:
            return

        chat_id = update.effective_chat.id
        entries, current_project_folder = self._switch_listing_entries(chat_id)
        if not entries:
            await query.edit_message_text(self._t(update, "switch.no_sessions_found"))
            return
        text, reply_markup = self._build_switch_page_from_entries(chat_id, entries, current_project_folder, page)
        await query.edit_message_text(
            text=text,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )
