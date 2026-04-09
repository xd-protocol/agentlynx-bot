import json
import logging
import subprocess
import uuid
from datetime import datetime, timezone

import requests

from src.db import Database
from src.poster import Poster
from src.telegram_bot import TelegramReviewBot

logger = logging.getLogger(__name__)

TWEET_PROMPT = """You are the social media voice of a professional AI agent analytics platform.
Write ONE tweet about on-chain AI agent ecosystem stats.

Rules:
- Under 280 characters
- English only
- Crypto-native casual tone
- Include specific numbers from the data
- No links, no hashtags, no emojis
- Make it insightful, not just numbers
- Never mention any product or service name

Data:
{stats_json}

Write the tweet."""


class StatsCollector:
    def __init__(self, api_base_url: str):
        self.api_base_url = api_base_url.rstrip("/")

    def fetch_ecosystem_stats(self) -> dict | None:
        try:
            resp = requests.get(f"{self.api_base_url}/api/agents/filter-options", timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("Failed to fetch ecosystem stats: %s", e)
            return None

    def fetch_trending_agents(self) -> list | None:
        try:
            resp = requests.get(f"{self.api_base_url}/api/agents/suggestions", timeout=15)
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else data.get("data", [])
        except Exception as e:
            logger.error("Failed to fetch trending agents: %s", e)
            return None

    def fetch_top_agents(self) -> list | None:
        try:
            resp = requests.get(f"{self.api_base_url}/api/agents", params={"sort": "score", "pageSize": "5"}, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else data.get("data", [])
        except Exception as e:
            logger.error("Failed to fetch top agents: %s", e)
            return None

    def collect_all(self) -> dict:
        return {
            "ecosystem": self.fetch_ecosystem_stats(),
            "trending": self.fetch_trending_agents(),
            "top_agents": self.fetch_top_agents(),
        }


class Tweeter:
    DAILY_TWEET_CAP = 2

    def __init__(self, stats_collector: StatsCollector, poster: Poster, telegram: TelegramReviewBot, db: Database):
        self.stats = stats_collector
        self.poster = poster
        self.telegram = telegram
        self.db = db

    def _get_today_tweet_count(self) -> int:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00+00:00")
        result = (
            self.db.client.table("replies")
            .select("id")
            .eq("source_type", "original_tweet")
            .eq("status", "posted")
            .gte("posted_at", today)
            .execute()
        )
        return len(result.data)

    def generate_tweet(self, stats: dict) -> str | None:
        prompt = TWEET_PROMPT.format(stats_json=json.dumps(stats, indent=2))
        result = subprocess.run(
            ["claude", "-p", prompt, "--model", "sonnet"],
            capture_output=True, text=True,
        )
        text = result.stdout.strip()
        if not text or len(text) > 280:
            if text and len(text) > 280:
                text = text[:277] + "..."
        return text if text else None

    def run(self) -> dict:
        result = {"tweets_generated": 0}

        if self._get_today_tweet_count() >= self.DAILY_TWEET_CAP:
            result["skipped_reason"] = "daily_tweet_cap_reached"
            return result

        stats = self.stats.collect_all()
        if not any(stats.values()):
            result["skipped_reason"] = "no_stats_available"
            return result

        tweet_text = self.generate_tweet(stats)
        if not tweet_text:
            result["skipped_reason"] = "generation_failed"
            return result

        tweet_id = str(uuid.uuid4())
        self.db.save_reply({
            "id": tweet_id,
            "tweet_id": tweet_id,
            "draft_text": tweet_text,
            "final_text": None,
            "status": "pending",
            "source_type": "original_tweet",
            "reviewed_at": None,
            "posted_at": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

        import asyncio
        asyncio.run(self.telegram.send_review(
            {"content": "[Original Tweet]", "author_username": "agent_lynx"},
            tweet_text, tweet_id,
        ))

        result["tweets_generated"] = 1
        return result
