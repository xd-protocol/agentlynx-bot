import asyncio
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

CHAIN_NAMES = {1: "Ethereum", 56: "BNB Chain", 143: "Monad", 8453: "Base", 42220: "Celo"}
CHAIN_SLUGS = {1: "ethereum", 56: "bsc", 8453: "base", 42220: "celo", 143: "monad"}

TWEET_TYPES = ["agent_highlight", "anomaly", "comparison"]

PROMPTS = {
    "agent_highlight": """You are a crypto-native analyst sharing a standout AI agent's on-chain performance.
Write ONE tweet highlighting this agent's activity.

Rules:
- Under 280 characters (URL counts as 23 chars on X)
- English only, crypto-native casual tone
- Start with "Agent [name] on [chain]" format
- Focus on concrete numbers: volume, transactions, P&L
- End the tweet with the agent's URL on its own line
- No hashtags, no emojis
- Never mention any product or service name

Agent data:
{data_json}

Write the tweet.""",

    "anomaly": """You are a crypto-native analyst who spotted something unusual in on-chain AI agent data.
Write ONE tweet about an interesting pattern or anomaly you found.

Rules:
- Under 280 characters (URL counts as 23 chars on X)
- English only, crypto-native casual tone
- Refer to agents as "Agent [name] on [chain]" format
- Highlight what's unusual: sudden spikes, outliers, unexpected behavior
- Be specific with numbers and comparisons
- Include the URL of the most notable agent on its own line at the end
- No hashtags, no emojis
- Never mention any product or service name

Data:
{data_json}

Write the tweet.""",

    "comparison": """You are a crypto-native analyst comparing AI agent activity across chains.
Write ONE tweet with a specific cross-chain or category comparison.

Rules:
- Under 280 characters
- English only, crypto-native casual tone
- Refer to agents as "Agent [name] on [chain]" when mentioning specific agents
- Compare specific metrics between chains or agent categories
- Include concrete numbers, ratios, or percentages
- No links, no hashtags, no emojis
- Never mention any product or service name

Data:
{data_json}

Write the tweet.""",
}


class StatsCollector:
    def __init__(self, api_base_url: str):
        self.api_base_url = api_base_url.rstrip("/")

    def _get(self, path: str, params: dict | None = None) -> dict | list | None:
        try:
            resp = requests.get(f"{self.api_base_url}{path}", params=params, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("API request failed %s: %s", path, e)
            return None

    def fetch_ecosystem_stats(self) -> dict | None:
        return self._get("/api/agents/filter-options")

    def fetch_trending_agents(self) -> list | None:
        data = self._get("/api/agents/suggestions")
        if isinstance(data, list):
            return data
        return data.get("data", []) if data else None

    def fetch_top_agents(self, count: int = 5) -> list | None:
        data = self._get("/api/agents", {"sort": "score", "pageSize": str(count)})
        if isinstance(data, list):
            return data
        return data.get("data", []) if data else None

    def fetch_agent_detail(self, chain_id: int, agent_id: str) -> dict | None:
        return self._get(f"/api/agents/{chain_id}/{agent_id}")

    def collect_for_highlight(self) -> dict | None:
        trending = self.fetch_trending_agents()
        if not trending:
            return None
        agent = trending[0]
        chain_id = agent["chain_id"]
        detail = self.fetch_agent_detail(chain_id, agent["agent_id"])
        if not detail:
            return None
        detail["chain_name"] = CHAIN_NAMES.get(chain_id, f"Chain {chain_id}")
        slug = CHAIN_SLUGS.get(chain_id, str(chain_id))
        detail["url"] = f"{self.api_base_url}/agents/{slug}/{agent['agent_id']}"
        return detail

    def collect_for_anomaly(self) -> dict | None:
        top = self.fetch_top_agents(10)
        trending = self.fetch_trending_agents()
        if not top and not trending:
            return None
        agents = top or trending or []
        for a in agents:
            chain_id = a.get("chain_id") or a.get("chainId")
            agent_id = a.get("agent_id") or a.get("agentId")
            if chain_id and agent_id:
                slug = CHAIN_SLUGS.get(chain_id, str(chain_id))
                a["chain_name"] = CHAIN_NAMES.get(chain_id, f"Chain {chain_id}")
                a["url"] = f"{self.api_base_url}/agents/{slug}/{agent_id}"
        return {"top_agents": top or [], "trending": trending or []}

    def collect_for_comparison(self) -> dict | None:
        ecosystem = self.fetch_ecosystem_stats()
        top = self.fetch_top_agents(10)
        if not ecosystem:
            return None
        chains = ecosystem.get("chains", [])
        for c in chains:
            c["name"] = CHAIN_NAMES.get(c.get("id"), f"Chain {c.get('id')}")
        return {
            "chains": chains,
            "serviceTypes": ecosystem.get("serviceTypes", []),
            "capabilities": ecosystem.get("capabilities", []),
            "top_agents": top or [],
        }


class Tweeter:
    DAILY_TWEET_CAP = 3

    def __init__(self, stats_collector: StatsCollector, poster: Poster, telegram: TelegramReviewBot, db: Database):
        self.stats = stats_collector
        self.poster = poster
        self.telegram = telegram
        self.db = db

    def _get_today_tweet_count(self) -> int:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00+00:00")
        result = (
            self.db.client.table("replies")
            .select("id, draft_text")
            .eq("source_type", "original_tweet")
            .in_("status", ["posted", "pending"])
            .gte("created_at", today)
            .execute()
        )
        return len(result.data)

    def _get_next_tweet_type(self) -> str:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00+00:00")
        result = (
            self.db.client.table("replies")
            .select("tweet_id")
            .eq("source_type", "original_tweet")
            .in_("status", ["posted", "pending"])
            .gte("created_at", today)
            .execute()
        )
        count = len(result.data)
        return TWEET_TYPES[count % len(TWEET_TYPES)]

    def _collect_data(self, tweet_type: str) -> dict | None:
        if tweet_type == "agent_highlight":
            return self.stats.collect_for_highlight()
        elif tweet_type == "anomaly":
            return self.stats.collect_for_anomaly()
        elif tweet_type == "comparison":
            return self.stats.collect_for_comparison()
        return None

    def generate_tweet(self, tweet_type: str, data: dict) -> str | None:
        prompt = PROMPTS[tweet_type].format(data_json=json.dumps(data, indent=2, default=str))
        result = subprocess.run(
            ["claude", "-p", prompt, "--model", "sonnet"],
            capture_output=True, text=True,
        )
        text = result.stdout.strip()
        if not text:
            return None
        if len(text) > 280:
            text = text[:277] + "..."
        return text

    def run(self) -> dict:
        result = {"tweets_generated": 0}

        if self._get_today_tweet_count() >= self.DAILY_TWEET_CAP:
            result["skipped_reason"] = "daily_tweet_cap_reached"
            return result

        tweet_type = self._get_next_tweet_type()
        data = self._collect_data(tweet_type)
        if not data:
            result["skipped_reason"] = "no_data_available"
            return result

        tweet_text = self.generate_tweet(tweet_type, data)
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

        asyncio.run(self.telegram.send_review(
            {"content": f"[Original Tweet — {tweet_type}]", "author_username": "agent_lynx"},
            tweet_text, tweet_id,
        ))

        result["tweets_generated"] = 1
        result["tweet_type"] = tweet_type
        return result
