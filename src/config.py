import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    DAILY_REPLY_CAP = 10
    MIN_FOLLOWERS = 1000
    MAX_FOLLOWERS = 100000
    CRON_INTERVAL_HOURS = 2

    def __init__(self):
        self.twitter_auth_token = os.environ["TWITTER_AUTH_TOKEN"]
        self.twitter_ct0 = os.environ["TWITTER_CT0"]
        self.anthropic_api_key = os.environ["ANTHROPIC_API_KEY"]
        self.supabase_url = os.environ["SUPABASE_URL"]
        self.supabase_key = os.environ["SUPABASE_KEY"]
        self.telegram_bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
        self.telegram_chat_id = os.environ["TELEGRAM_CHAT_ID"]

    @property
    def twitter_env(self) -> dict[str, str]:
        return {
            "TWITTER_AUTH_TOKEN": self.twitter_auth_token,
            "TWITTER_CT0": self.twitter_ct0,
        }
