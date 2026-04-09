#!/usr/bin/env python3
"""Entry point for cron: runs the tweet collection + reply generation pipeline."""
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from src.config import Config
from src.db import Database
from src.fetcher import Fetcher
from src.filters import Filters
from src.generator import ReplyGenerator
from src.poster import Poster
from src.telegram_bot import TelegramReviewBot
from src.pipeline import Pipeline
from src.tweeter import StatsCollector, Tweeter


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    config = Config()
    db = Database(config.supabase_url, config.supabase_key)
    fetcher = Fetcher(twitter_env=config.twitter_env)
    filters = Filters(db=db, fetcher=fetcher)
    generator = ReplyGenerator()
    poster = Poster(twitter_env=config.twitter_env)
    telegram = TelegramReviewBot(config.telegram_bot_token, config.telegram_chat_id, db, poster)

    stats_collector = StatsCollector(Config.AGENTLYNX_API_URL)
    tweeter = Tweeter(stats_collector=stats_collector, poster=poster, telegram=telegram, db=db)

    pipeline = Pipeline(
        db=db, fetcher=fetcher, filters=filters,
        generator=generator, telegram=telegram, tweeter=tweeter,
    )
    stats = pipeline.run()
    print(f"Pipeline complete: {stats}")


if __name__ == "__main__":
    main()
