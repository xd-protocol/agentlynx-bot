import logging
from datetime import datetime, timezone

from src.config import Config
from src.db import Database
from src.fetcher import Fetcher
from src.filters import Filters
from src.generator import ReplyGenerator
from src.poster import Poster

logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(self, db: Database, fetcher: Fetcher, filters: Filters, generator: ReplyGenerator, poster: Poster, telegram):
        self.db = db
        self.fetcher = fetcher
        self.filters = filters
        self.generator = generator
        self.poster = poster
        self.telegram = telegram

    def run(self) -> dict:
        stats = {"fetched": 0, "filtered": 0, "posted": 0, "skipped": 0}

        reply_count = self.db.get_today_reply_count()
        if reply_count >= Config.DAILY_REPLY_CAP:
            logger.info("Daily cap reached (%d). Skipping run.", Config.DAILY_REPLY_CAP)
            return stats

        tweets = []
        for keyword in self.db.get_active_keywords():
            tweets.extend(self.fetcher.search_keyword(keyword))
        for account in self.db.get_active_accounts():
            tweets.extend(self.fetcher.fetch_account_tweets(account))

        tweets = self.filters.dedup(tweets)
        stats["fetched"] = len(tweets)

        for tweet in tweets:
            if reply_count >= Config.DAILY_REPLY_CAP:
                break

            if not self.filters.filter_tweet(tweet):
                stats["skipped"] += 1
                continue

            stats["filtered"] += 1
            reply_text = self.generator.generate(
                tweet_content=tweet["content"],
                author_username=tweet["author_username"],
                author_bio=tweet.get("author_bio", ""),
                thread_context=tweet.get("thread_context"),
            )

            if reply_text is None:
                stats["skipped"] += 1
                continue

            self.db.save_tweet(tweet)

            reply = {
                "tweet_id": tweet["tweet_id"],
                "reply_text": reply_text,
                "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self.db.save_reply(reply)

            success = self.poster.post_reply(tweet["tweet_id"], reply_text)
            if success:
                stats["posted"] += 1
                reply_count += 1
                self.telegram.notify_reply(tweet=tweet, reply_text=reply_text)
            else:
                stats["skipped"] += 1

        logger.info("Pipeline run complete: %s", stats)
        return stats


def main():
    from anthropic import Anthropic
    from src.telegram_bot import TelegramNotifier

    config = Config()
    db = Database(url=config.supabase_url, key=config.supabase_key)
    fetcher = Fetcher(twitter_env=config.twitter_env)
    anthropic_client = Anthropic(api_key=config.anthropic_api_key)
    filters = Filters(db=db, fetcher=fetcher, anthropic_client=anthropic_client)
    generator = ReplyGenerator(anthropic_client=anthropic_client)
    poster = Poster(twitter_env=config.twitter_env)
    telegram = TelegramNotifier(token=config.telegram_bot_token, chat_id=config.telegram_chat_id)

    pipeline = Pipeline(db=db, fetcher=fetcher, filters=filters, generator=generator, poster=poster, telegram=telegram)
    stats = pipeline.run()
    print(stats)


if __name__ == "__main__":
    main()
