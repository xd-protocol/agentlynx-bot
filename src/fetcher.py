import json
import logging
import os
import subprocess
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class Fetcher:
    def __init__(self, twitter_env: dict[str, str]):
        self.env = {**os.environ, **twitter_env}

    def _run_twitter(self, args: list[str]) -> dict | None:
        try:
            result = subprocess.run(
                ["twitter"] + args + ["--json"],
                capture_output=True,
                text=True,
                env=self.env,
                timeout=30,
            )
            if result.returncode != 0:
                return None
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                return None
        except subprocess.TimeoutExpired:
            return None

    def _parse_tweet(self, raw: dict, source_type: str, source_value: str) -> dict:
        author = raw.get("author", {})
        return {
            "tweet_id": raw["id"],
            "content": raw.get("text", ""),
            "author_username": author.get("screenName", ""),
            "author_bio": "",
            "thread_context": None,
            "source_type": source_type,
            "source_value": source_value,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "metrics": raw.get("metrics", {}),
        }

    def search_keyword(self, keyword: str, max_results: int = 20) -> list[dict]:
        print(f"Searching keyword: {keyword}")
        data = self._run_twitter(["search", keyword, "--lang", "en", "-n", str(max_results)])
        if not data or not data.get("ok"):
            logger.error("Search failed for keyword: %s", keyword)
            return []
        tweets = [self._parse_tweet(t, "keyword", keyword) for t in data.get("data", [])]
        print(f"Found {len(tweets)} tweets for keyword {keyword}")
        return tweets

    def fetch_account_tweets(self, username: str, max_results: int = 10) -> list[dict]:
        data = self._run_twitter(["user-posts", username, "-n", str(max_results)])
        if not data or not data.get("ok"):
            return []
        return [self._parse_tweet(t, "account", username) for t in data.get("data", [])]

    def fetch_user_profile(self, username: str) -> dict | None:
        data = self._run_twitter(["user", username])
        if not data or not data.get("ok") or not data.get("data"):
            return None
        d = data["data"]
        return {
            "username": d.get("screenName", ""),
            "name": d.get("name", ""),
            "bio": d.get("bio", ""),
            "followers": d.get("followers", 0),
            "verified": d.get("verified", False),
        }

    def check_auth(self) -> bool:
        data = self._run_twitter(["status"])
        return bool(data and data.get("ok") and data.get("data", {}).get("authenticated"))
