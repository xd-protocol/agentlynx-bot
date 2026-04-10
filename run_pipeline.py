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
    # Configure logging: INFO/DEBUG/WARNING to stdout, ERROR/CRITICAL to stderr
    formatter = logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")

    # Handler for non-error logs (stdout)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.addFilter(lambda record: record.levelno < logging.ERROR)

    # Handler for error logs (stderr)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)
    stderr_handler.setLevel(logging.ERROR)

    logging.root.setLevel(logging.INFO)
    logging.root.addHandler(stdout_handler)
    logging.root.addHandler(stderr_handler)

    # Suppress httpx verbose logging
    logging.getLogger("httpx").setLevel(logging.WARNING)

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
        generator=generator, poster=poster, telegram=telegram, tweeter=tweeter,
    )
    stats = pipeline.run()
    print(f"Pipeline complete: {stats}")


if __name__ == "__main__":
    main()
