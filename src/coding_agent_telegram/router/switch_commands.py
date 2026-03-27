from __future__ import annotations
import html

from telegram import Update
from telegram.ext import ContextTypes

from coding_agent_telegram.filters import resolve_project_path
from coding_agent_telegram.native_sessions import discover_native_project_sessions
from coding_agent_telegram.telegram_sender import send_html_text, send_text

from .base import logger, require_allowed_chat


class SwitchCommandMixin:
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
        entries: list[dict[str, str]],
        current_project_folder: str | None,
        page: int,
    ) -> str:
        total_sessions = len(entries)
        total_pages = max(1, (total_sessions + self.SWITCH_PAGE_SIZE - 1) // self.SWITCH_PAGE_SIZE)
        page = min(max(page, 1), total_pages)
        start = (page - 1) * self.SWITCH_PAGE_SIZE
        page_items = entries[start : start + self.SWITCH_PAGE_SIZE]

        project_line = (
            f"Current project filter for native sessions: <code>{html.escape(current_project_folder)}</code>"
            if current_project_folder
            else "Current project filter for native sessions: (none)"
        )
        lines = [
            f"Available sessions (page {page}/{total_pages}):",
            "",
            "🤖 = Bot managed session",
            "💻 = native CLI session",
            project_line,
            "",
        ]
        for idx, entry in enumerate(page_items, start=start + 1):
            branch_name = entry["branch_name"] or "(current branch)"
            marker = "🤖" if entry["origin"] == "bot" else "💻"
            lines.append(
                f"{idx}. {marker} {html.escape(entry['name'])} | <code>{html.escape(entry['project_folder'])}</code> &lt;{html.escape(branch_name)}&gt; | {html.escape(entry['provider'])} | {html.escape(entry['status'])}"
            )
            lines.append(f"session_id: {entry['session_id']}")
            lines.append(f"initialized: {html.escape(entry['initialized_from'])}")
            lines.append("")

        lines.extend(
            [
                "Use:",
                "/switch &lt;session_id&gt;",
                f"/switch page {page}",
                "Selecting a native CLI session imports it into state.json and switches the bot to it.",
            ]
        )
        if total_pages > 1:
            lines.append(f"Pages: /switch page 1 ... /switch page {total_pages}")
        return "\n".join(lines).strip()

    @require_allowed_chat()
    async def handle_switch(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self._notify_if_current_project_busy(update, context):
            return
        chat_id = update.effective_chat.id
        entries, current_project_folder = self._switch_listing_entries(chat_id)

        if not context.args:
            if not entries:
                await send_text(update, context, "No sessions found.")
                return
            logger.info("Listed sessions page 1 for chat %s (%d sessions total).", chat_id, len(entries))
            await send_html_text(update, context, self._build_switch_page_from_entries(entries, current_project_folder, 1))
            return

        if len(context.args) == 2 and context.args[0].lower() == "page":
            if not entries:
                await send_text(update, context, "No sessions found.")
                return
            try:
                page = int(context.args[1])
            except ValueError:
                await send_text(update, context, "Invalid page number.\nUse: /switch page <number>")
                return
            if page < 1:
                await send_text(update, context, "Invalid page number.\nUse: /switch page <number>")
                return
            logger.info("Listed sessions page %d for chat %s (%d sessions total).", page, chat_id, len(entries))
            await send_html_text(update, context, self._build_switch_page_from_entries(entries, current_project_folder, page))
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
            await send_text(update, context, "⚠️ Session not found.\nRun /switch to list available sessions.")
            return

        project_path = resolve_project_path(self.deps.cfg.workspace_root, session["project_folder"])
        if not project_path.exists() or not project_path.is_dir():
            await send_text(
                update,
                context,
                f"⚠️ Project folder no longer exists for this session: {session['project_folder']}",
            )
            return
        if not self.deps.store.switch_session(self.deps.bot_id, chat_id, session_id):
            await send_text(update, context, "⚠️ Session not found.\nRun /switch to list available sessions.")
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
                f"Switched to session: {html.escape(session['name'])}\n"
                f"Project: <code>{html.escape(session['project_folder'])}</code>\n"
                f"Provider: {html.escape(session.get('provider', 'codex'))}\n"
                f"Branch: {html.escape((session.get('branch_name') or '(current branch)'))}"
                + (
                    f"\nSource: {html.escape(native_origin_label)}\nInitialized: {html.escape(native_initialized_from)}\nImported into state.json."
                    if imported_from_native
                    else (
                        f"\nSource: {html.escape(str(session.get('origin_label') or 'Bot managed session'))}\n"
                        f"Initialized: {html.escape(str(session.get('initialized_from') or 'Bot-managed session from state.json'))}"
                    )
                )
            ),
        )
