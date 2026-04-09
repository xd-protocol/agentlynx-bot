from unittest.mock import MagicMock, patch
from src.pipeline import Pipeline


def _make_tweet(tweet_id="1", username="user1"):
    return {
        "tweet_id": tweet_id,
        "content": "On-chain AI agents are the future of DeFi",
        "author_username": username,
        "author_bio": "DeFi researcher",
        "thread_context": None,
        "source_type": "keyword",
        "source_value": "AI agents",
        "fetched_at": "2026-04-09T00:00:00+00:00",
        "metrics": {},
    }


def _make_pipeline(daily_count=0, keywords=None, accounts=None):
    db = MagicMock()
    db.get_today_reply_count.return_value = daily_count
    db.get_active_keywords.return_value = keywords or ["AI agents"]
    db.get_active_accounts.return_value = accounts or []
    db.is_tweet_seen.return_value = False

    fetcher = MagicMock()
    fetcher.search_keyword.return_value = [_make_tweet()]
    fetcher.fetch_account_tweets.return_value = []

    filters = MagicMock()
    filters.dedup.side_effect = lambda tweets: tweets
    filters.filter_tweet.return_value = True

    generator = MagicMock()
    generator.generate.return_value = "great point on agent interoperability"

    poster = MagicMock()
    poster.post_reply.return_value = True

    telegram = MagicMock()
    telegram.notify_reply.return_value = None

    return Pipeline(db=db, fetcher=fetcher, filters=filters, generator=generator, poster=poster, telegram=telegram)


def test_run_posts_reply_when_under_cap():
    pipeline = _make_pipeline(daily_count=0)
    result = pipeline.run()
    assert result["posted"] >= 1
    pipeline.poster.post_reply.assert_called_once()


def test_run_skips_when_daily_cap_reached():
    pipeline = _make_pipeline(daily_count=10)
    result = pipeline.run()
    assert result["posted"] == 0
    pipeline.poster.post_reply.assert_not_called()


def test_run_skips_filtered_tweets():
    pipeline = _make_pipeline()
    pipeline.filters.filter_tweet.return_value = False
    result = pipeline.run()
    assert result["posted"] == 0
    pipeline.poster.post_reply.assert_not_called()


def test_run_skips_when_generator_returns_none():
    pipeline = _make_pipeline()
    pipeline.generator.generate.return_value = None
    result = pipeline.run()
    assert result["posted"] == 0
    pipeline.poster.post_reply.assert_not_called()


def test_run_saves_tweet_and_reply_to_db():
    pipeline = _make_pipeline()
    pipeline.run()
    pipeline.db.save_tweet.assert_called_once()
    pipeline.db.save_reply.assert_called_once()


def test_run_notifies_telegram_on_success():
    pipeline = _make_pipeline()
    pipeline.run()
    pipeline.telegram.notify_reply.assert_called_once()
