"""
Telegram side of the pipeline: sends the lead card and handles the two
buttons on it.

"Copy Username" uses Telegram's native copy-to-clipboard button
(CopyTextButton, Bot API 7.1+ / PTB 21.7+). The username is also sent
in <code> formatting as a fallback, since monospaced text is tap-to-
copy in Telegram clients on its own.
"""

import html
import os

from telegram import CopyTextButton, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import database

TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]


def _esc(value) -> str:
    """Escapes text for safe interpolation into an HTML-formatted message."""
    return html.escape(str(value))


def _build_keyboard(lead_id: int, username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📋 Copy Username", copy_text=CopyTextButton(text=username)
                )
            ],
            [
                InlineKeyboardButton(
                    "✅ Mark Contacted", callback_data=f"contacted:{lead_id}"
                )
            ],
        ]
    )


async def send_lead_notification(bot, lead_id: int, profile: dict, reason: str) -> None:
    """Sends the qualified-lead card to TELEGRAM_CHAT_ID."""
    username = profile.get("username", "unknown")
    platform = profile.get("platform", "unknown")
    followers = profile.get("followers_count") or 0
    bio = profile.get("bio", "")

    text = (
        "🎯 <b>New Qualified Lead</b>\n\n"
        f"👤 <b>Username:</b> <code>{_esc(username)}</code>\n"
        f"🌐 <b>Platform:</b> {_esc(platform)}\n"
        f"👥 <b>Followers:</b> {followers:,}\n"
        f"📝 <b>Bio:</b> {_esc(bio)}\n\n"
        f"🤖 <b>AI Reasoning:</b>\n{_esc(reason)}"
    )

    await bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=_build_keyboard(lead_id, username),
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the 'Mark Contacted' button: updates Supabase, deletes the message."""
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    if not data.startswith("contacted:"):
        return

    lead_id = int(data.split(":", 1)[1])
    database.update_lead_status(lead_id, "contacted")

    if query.message:
        await query.message.delete()
