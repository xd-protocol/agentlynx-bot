import pytest
from unittest.mock import AsyncMock, MagicMock
from src.telegram_bot import format_review_message, TelegramReviewBot


def test_format_review_message():
    msg = format_review_message(
        tweet_content="AI agents are the future of DeFi",
        author_username="cryptodegen",
        author_followers=15000,
        draft_reply="totally agree — the coordination layer between agents is what makes this real",
        reply_id="abc-123",
    )
    assert "@cryptodegen" in msg
    assert "15,000" in msg
    assert "AI agents are the future of DeFi" in msg
    assert "totally agree" in msg


def test_format_review_message_truncates_long_tweet():
    long_tweet = "x" * 500
    msg = format_review_message(
        tweet_content=long_tweet,
        author_username="user",
        author_followers=5000,
        draft_reply="reply",
        reply_id="abc",
    )
    assert len(msg) < 2000


def test_format_review_message_includes_char_count():
    msg = format_review_message(
        tweet_content="test",
        author_username="user",
        author_followers=0,
        draft_reply="Short reply",
        reply_id="x",
    )
    assert "11" in msg  # len("Short reply") == 11


def test_telegram_review_bot_init():
    mock_db = MagicMock()
    mock_poster = MagicMock()
    bot = TelegramReviewBot(
        token="fake_token",
        chat_id="12345",
        db=mock_db,
        poster=mock_poster,
    )
    assert bot.chat_id == "12345"
    assert bot.db is mock_db
    assert bot.poster is mock_poster


@pytest.mark.asyncio
async def test_send_review_sends_message():
    mock_db = MagicMock()
    mock_db.get_cached_account.return_value = {"followers": 8000}
    mock_poster = MagicMock()
    bot = TelegramReviewBot(token="fake_token", chat_id="12345", db=mock_db, poster=mock_poster)

    mock_bot = AsyncMock()
    mock_message = AsyncMock()
    mock_message.message_id = 999
    mock_bot.send_message.return_value = mock_message
    bot._bot = mock_bot

    tweet = {"tweet_id": "t1", "content": "DeFi agents rock", "author_username": "alice"}
    draft = "Indeed, agent-driven AMMs are the future."
    reply_id = "r1"

    await bot.send_review(tweet, draft, reply_id)

    mock_bot.send_message.assert_called_once()
    call_kwargs = mock_bot.send_message.call_args.kwargs
    assert call_kwargs["chat_id"] == "12345"
    assert "reply_markup" in call_kwargs


@pytest.mark.asyncio
async def test_handle_callback_approve():
    mock_db = MagicMock()
    mock_poster = MagicMock()
    mock_poster.post_reply.return_value = True
    bot = TelegramReviewBot(token="fake_token", chat_id="12345", db=mock_db, poster=mock_poster)

    bot._pending["r1"] = {
        "tweet_id": "t1",
        "draft": "Great insight on AI agents.",
        "message_id": 999,
    }

    update = MagicMock()
    update.callback_query = AsyncMock()
    update.callback_query.data = "approve:r1"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    context = MagicMock()

    await bot.handle_callback(update, context)

    mock_poster.post_reply.assert_called_once_with("t1", "Great insight on AI agents.")
    mock_db.update_reply.assert_called_once()
    update.callback_query.edit_message_text.assert_called_once()


@pytest.mark.asyncio
async def test_handle_callback_reject():
    mock_db = MagicMock()
    mock_poster = MagicMock()
    bot = TelegramReviewBot(token="fake_token", chat_id="12345", db=mock_db, poster=mock_poster)

    bot._pending["r2"] = {
        "tweet_id": "t2",
        "draft": "Some reply.",
        "message_id": 888,
    }

    update = MagicMock()
    update.callback_query = AsyncMock()
    update.callback_query.data = "reject:r2"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    context = MagicMock()

    await bot.handle_callback(update, context)

    mock_poster.post_reply.assert_not_called()
    mock_db.update_reply.assert_called_once()
    args = mock_db.update_reply.call_args
    assert args[0][1]["status"] == "rejected"


@pytest.mark.asyncio
async def test_handle_edit_text_valid():
    mock_db = MagicMock()
    mock_poster = MagicMock()
    mock_poster.post_reply.return_value = True
    bot = TelegramReviewBot(token="fake_token", chat_id="12345", db=mock_db, poster=mock_poster)

    bot._pending["r3"] = {
        "tweet_id": "t3",
        "draft": "Old draft",
        "message_id": 777,
    }
    bot._awaiting_edit = "r3"

    update = MagicMock()
    update.message = AsyncMock()
    update.message.text = "New edited reply under 280 chars."
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    await bot.handle_edit_text(update, context)

    mock_poster.post_reply.assert_called_once_with("t3", "New edited reply under 280 chars.")
    mock_db.update_reply.assert_called_once()
    update.message.reply_text.assert_called_once()
    assert bot._awaiting_edit is None


@pytest.mark.asyncio
async def test_handle_edit_text_too_long():
    mock_db = MagicMock()
    mock_poster = MagicMock()
    bot = TelegramReviewBot(token="fake_token", chat_id="12345", db=mock_db, poster=mock_poster)

    bot._pending["r4"] = {"tweet_id": "t4", "draft": "Old draft", "message_id": 666}
    bot._awaiting_edit = "r4"

    update = MagicMock()
    update.message = AsyncMock()
    update.message.text = "x" * 281
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    await bot.handle_edit_text(update, context)

    mock_poster.post_reply.assert_not_called()
    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args[0][0]
    assert "280" in call_args
    assert bot._awaiting_edit == "r4"
