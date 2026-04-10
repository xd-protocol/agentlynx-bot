#!/usr/bin/env python3
"""Run the Telegram review bot."""
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from src.config import Config
from src.db import Database
from src.poster import Poster
from src.telegram_bot import TelegramReviewBot


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    # Suppress httpx INFO logs
    logging.getLogger("httpx").setLevel(logging.WARNING)

    config = Config()
    db = Database(config.supabase_url, config.supabase_key)
    poster = Poster(twitter_env=config.twitter_env)
    telegram = TelegramReviewBot(config.telegram_bot_token, config.telegram_chat_id, db, poster)

    telegram.run()


if __name__ == "__main__":
    main()
