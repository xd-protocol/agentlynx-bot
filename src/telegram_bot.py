import logging
from datetime import datetime, timezone

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes, MessageHandler, filters

from src.db import Database
from src.poster import Poster

logger = logging.getLogger(__name__)


def format_review_message(tweet_content: str, author_username: str, author_followers: int, draft_reply: str, reply_id: str) -> str:
    truncated = tweet_content[:300] + "..." if len(tweet_content) > 300 else tweet_content
    char_count = len(draft_reply)
    return (
        f"Tweet by @{author_username} ({author_followers:,} followers):\n"
        f"{truncated}\n\n"
        f"Draft reply ({char_count}/280):\n"
        f"{draft_reply}\n\n"
        f"ID: {reply_id}"
    )


class TelegramReviewBot:
    def __init__(self, token: str, chat_id: str, db: Database, poster: Poster):
        self.token = token
        self.chat_id = chat_id
        self.db = db
        self.poster = poster
        self._pending: dict[str, dict] = {}
        self._awaiting_edit: str | None = None
        self._bot = Bot(token=token)

    async def send_review(self, tweet: dict, draft: str, reply_id: str) -> None:
        cached = self.db.get_cached_account(tweet["author_username"])
        followers = cached["followers"] if cached else 0
        text = format_review_message(tweet["content"], tweet["author_username"], followers, draft, reply_id)
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Approve", callback_data=f"approve:{reply_id}"),
                InlineKeyboardButton("Reject", callback_data=f"reject:{reply_id}"),
                InlineKeyboardButton("Edit", callback_data=f"edit:{reply_id}"),
            ]
        ])
        message = await self._bot.send_message(
            chat_id=self.chat_id,
            text=text,
            reply_markup=keyboard,
        )
        self._pending[reply_id] = {
            "tweet_id": tweet["tweet_id"],
            "draft": draft,
            "message_id": message.message_id,
        }

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await query.answer()
        action, reply_id = query.data.split(":", 1)
        pending = self._pending.get(reply_id)
        if not pending:
            await query.edit_message_text("This review has expired.")
            return

        if action == "approve":
            success = self.poster.post_reply(pending["tweet_id"], pending["draft"])
            status = "posted" if success else "failed"
            self.db.update_reply(reply_id, {
                "status": status,
                "posted_at": datetime.now(timezone.utc).isoformat(),
            })
            label = "Posted" if success else "Failed to post"
            await query.edit_message_text(f"{label}: {pending['draft']}")
            del self._pending[reply_id]

        elif action == "reject":
            self.db.update_reply(reply_id, {"status": "rejected"})
            await query.edit_message_text("Rejected.")
            del self._pending[reply_id]

        elif action == "edit":
            self._awaiting_edit = reply_id
            await query.edit_message_text(
                f"Send your edited reply (max 280 chars):\n\nCurrent draft:\n{pending['draft']}"
            )

    async def handle_edit_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if self._awaiting_edit is None:
            return
        reply_id = self._awaiting_edit
        new_text = update.message.text
        if len(new_text) > 280:
            await update.message.reply_text(
                f"Too long ({len(new_text)} chars). Max 280. Please try again."
            )
            return
        pending = self._pending.get(reply_id)
        if not pending:
            await update.message.reply_text("Review expired.")
            self._awaiting_edit = None
            return
        success = self.poster.post_reply(pending["tweet_id"], new_text)
        status = "posted" if success else "failed"
        self.db.update_reply(reply_id, {
            "status": status,
            "posted_at": datetime.now(timezone.utc).isoformat(),
        })
        label = "Posted" if success else "Failed to post"
        await update.message.reply_text(f"{label}: {new_text}")
        del self._pending[reply_id]
        self._awaiting_edit = None

    def run(self) -> None:
        app = Application.builder().token(self.token).build()
        app.add_handler(CallbackQueryHandler(self.handle_callback))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_edit_text))
        logger.info("Telegram review bot started")
        app.run_polling()
