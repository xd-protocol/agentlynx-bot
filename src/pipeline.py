import asyncio
import logging
import uuid
from datetime import datetime, timezone

from src.config import Config
from src.db import Database
from src.fetcher import Fetcher
from src.filters import Filters
from src.generator import ReplyGenerator
from src.poster import Poster
from src.telegram_bot import TelegramReviewBot
from src.tweeter import Tweeter

logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(self, db: Database, fetcher: Fetcher, filters: Filters, generator: ReplyGenerator, poster: Poster, telegram: TelegramReviewBot, tweeter: Tweeter = None):
        self.db = db
        self.fetcher = fetcher
        self.filters = filters
        self.generator = generator
        self.poster = poster
        self.telegram = telegram
        self.tweeter = tweeter
        self.loop = asyncio.new_event_loop()

    def run(self) -> dict:
        stats = {"fetched": 0, "drafts_created": 0, "skipped": 0}

        reply_count = self.db.get_today_reply_count()
        if reply_count >= Config.DAILY_REPLY_CAP:
            logger.info("Daily cap reached (%d). Skipping.", Config.DAILY_REPLY_CAP)
            stats["skipped_reason"] = "daily_cap_reached"
            return stats

        # Collect tweets
        tweets = []
        for keyword in self.db.get_active_keywords():
            tweets.extend(self.fetcher.search_keyword(keyword))
        for account in self.db.get_active_accounts():
            tweets.extend(self.fetcher.fetch_account_tweets(account))

        # Dedup
        tweets = self.filters.dedup(tweets)
        stats["fetched"] = len(tweets)
        logger.info("Fetched %d new tweets", len(tweets))

        # Filter and generate drafts
        for tweet in tweets:
            if reply_count + stats["drafts_created"] >= Config.DAILY_REPLY_CAP:
                break

            if not self.filters.filter_tweet(tweet):
                stats["skipped"] += 1
                continue

            reply_text = self.generator.generate(
                tweet_content=tweet["content"],
                author_username=tweet["author_username"],
                author_bio=tweet.get("author_bio", ""),
                thread_context=tweet.get("thread_context"),
            )

            if reply_text is None:
                stats["skipped"] += 1
                continue

            # Save tweet
            tweet_to_save = {k: v for k, v in tweet.items() if k != "metrics"}
            self.db.save_tweet(tweet_to_save)

            # Save reply as pending (NOT posting yet)
            reply_id = str(uuid.uuid4())
            self.db.save_reply({
                "id": reply_id,
                "tweet_id": tweet["tweet_id"],
                "draft_text": reply_text,
                "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

            # Send to Telegram for approval
            self.loop.run_until_complete(self.telegram.send_review(tweet, reply_text, reply_id))
            stats["drafts_created"] += 1
            logger.info("Draft created for tweet %s", tweet["tweet_id"])

        # Run tweeter
        stats["tweeter"] = self.run_tweeter()
        logger.info("Pipeline complete: %s", stats)
        return stats

    def run_tweeter(self) -> dict:
        if not self.tweeter:
            return {"skipped_reason": "tweeter_not_configured"}
        return self.tweeter.run()
