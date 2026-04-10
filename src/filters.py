import os
from anthropic import Anthropic
from src.config import Config
from src.db import Database
from src.fetcher import Fetcher

CLASSIFY_PROMPT = """Classify this X account as "individual" or "organization".

Username: @{username}
Display name: {name}
Bio: {bio}
Verified: {verified}
Followers: {followers}

"individual" = real person (influencer, developer, researcher, trader, etc.)
"organization" = company, protocol, DAO, VC fund, exchange, lab, foundation, media outlet, bot

Reply with ONLY "individual" or "organization"."""

RELEVANCE_PROMPT = """Is this tweet relevant to on-chain AI agents, agent trading, DeFi automation, or the agent economy?

Tweet: {content}

Reply with ONLY "relevant" or "irrelevant"."""


class Filters:
    def __init__(self, db: Database, fetcher: Fetcher):
        self.db = db
        self.fetcher = fetcher
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        self.client = Anthropic(api_key=api_key)

    def dedup(self, tweets: list[dict]) -> list[dict]:
        return [t for t in tweets if not self.db.is_tweet_seen(t["tweet_id"])]

    def is_within_follower_range(self, followers: int) -> bool:
        return Config.MIN_FOLLOWERS <= followers <= Config.MAX_FOLLOWERS

    def classify_account(self, username: str) -> str:
        cached = self.db.get_cached_account(username)
        if cached:
            return cached["account_type"]
        profile = self.fetcher.fetch_user_profile(username)
        if not profile:
            return "organization"
        prompt = CLASSIFY_PROMPT.format(username=profile["username"], name=profile["name"], bio=profile["bio"], verified=profile["verified"], followers=profile["followers"])
        try:
            message = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=50,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            account_type = message.content[0].text.strip().lower()
        except Exception:
            account_type = "organization"
        if account_type not in ("individual", "organization"):
            account_type = "organization"
        self.db.cache_account(username, account_type, profile["bio"], profile["followers"])
        return account_type

    def check_relevance(self, content: str) -> bool:
        prompt = RELEVANCE_PROMPT.format(content=content)
        try:
            message = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=50,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            response = message.content[0].text.strip().lower()
            return response == "relevant"
        except Exception:
            return False

    def filter_tweet(self, tweet: dict) -> bool:
        username = tweet["author_username"]
        account_type = self.classify_account(username)
        if account_type != "individual":
            return False
        cached = self.db.get_cached_account(username)
        if cached and not self.is_within_follower_range(cached["followers"]):
            return False
        if not self.check_relevance(tweet["content"]):
            return False
        return True
