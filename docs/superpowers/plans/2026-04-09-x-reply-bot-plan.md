# AgentLynx X Reply Bot — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a cron-based pipeline that finds relevant crypto/AI agent tweets, generates contextual replies via Claude, and posts them after human approval via Telegram.

**Architecture:** Single Python package with modular pipeline steps. Each step is a function that takes input from the previous step. A main `run_pipeline()` orchestrates the flow. Cron triggers it every 2 hours.

**Tech Stack:** Python 3.11+, Agent Reach (twitter-cli), Claude API (anthropic SDK), Supabase (supabase-py), python-telegram-bot, system cron.

---

## File Structure

```
agentlynx-bot/
  .env                          # API keys, tokens (not committed)
  .env.example                  # Template for .env
  .gitignore
  requirements.txt
  src/
    __init__.py
    config.py                   # Env vars, constants
    db.py                       # Supabase client + queries
    fetcher.py                  # Tweet collection (keyword + account)
    filters.py                  # Dedup, account classifier, follower filter, relevance
    generator.py                # Claude reply generation
    telegram_bot.py             # Telegram review bot (long-running)
    poster.py                   # Post reply via twitter-cli
    pipeline.py                 # Main pipeline orchestrator
  tests/
    __init__.py
    test_config.py
    test_fetcher.py
    test_filters.py
    test_generator.py
    test_poster.py
    test_pipeline.py
    conftest.py                 # Shared fixtures
  scripts/
    seed_data.py                # Seed initial keywords + accounts
    setup_cron.sh               # Install cron job
  docs/
    superpowers/
      specs/2026-04-09-x-reply-bot-design.md
      plans/2026-04-09-x-reply-bot-plan.md
```

---

### Task 1: Project Setup & Dependencies

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `src/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create requirements.txt**

```txt
anthropic>=0.52.0
supabase>=2.0.0
python-telegram-bot>=21.0
python-dotenv>=1.0.0
```

- [ ] **Step 2: Create .env.example**

```
# Twitter (Agent Reach)
TWITTER_AUTH_TOKEN=
TWITTER_CT0=

# Claude API
ANTHROPIC_API_KEY=

# Supabase
SUPABASE_URL=
SUPABASE_KEY=

# Telegram
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

- [ ] **Step 3: Create package init files and conftest**

`src/__init__.py` — empty file.

`tests/__init__.py` — empty file.

`tests/conftest.py`:

```python
import os
import pytest

os.environ.setdefault("TWITTER_AUTH_TOKEN", "test-token")
os.environ.setdefault("TWITTER_CT0", "test-ct0")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_CHAT_ID", "12345")
```

- [ ] **Step 4: Install dependencies**

Run: `source .venv/bin/activate && pip install -r requirements.txt`
Expected: All packages install successfully.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt .env.example src/__init__.py tests/__init__.py tests/conftest.py
git commit -m "feat: project setup with dependencies and env template"
```

---

### Task 2: Config Module

**Files:**
- Create: `src/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

`tests/test_config.py`:

```python
from src.config import Config


def test_config_loads_from_env(monkeypatch):
    monkeypatch.setenv("TWITTER_AUTH_TOKEN", "abc123")
    monkeypatch.setenv("TWITTER_CT0", "def456")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "sbkey")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tg-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "99999")

    config = Config()
    assert config.twitter_auth_token == "abc123"
    assert config.twitter_ct0 == "def456"
    assert config.anthropic_api_key == "sk-ant-test"
    assert config.supabase_url == "https://x.supabase.co"
    assert config.supabase_key == "sbkey"
    assert config.telegram_bot_token == "tg-token"
    assert config.telegram_chat_id == "99999"


def test_config_constants():
    assert Config.DAILY_REPLY_CAP == 10
    assert Config.MIN_FOLLOWERS == 1000
    assert Config.MAX_FOLLOWERS == 100000
    assert Config.CRON_INTERVAL_HOURS == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.config'`

- [ ] **Step 3: Write implementation**

`src/config.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && python -m pytest tests/test_config.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/config.py tests/test_config.py
git commit -m "feat: add config module with env loading and constants"
```

---

### Task 3: Database Module (Supabase)

**Files:**
- Create: `src/db.py`
- Create: `tests/test_db.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_db.py`:

```python
from unittest.mock import MagicMock, patch
from src.db import Database


@patch("src.db.create_client")
def test_is_tweet_seen_returns_false_for_new(mock_create):
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    mock_create.return_value = mock_client

    db = Database("https://test.supabase.co", "key")
    assert db.is_tweet_seen("123456") is False


@patch("src.db.create_client")
def test_is_tweet_seen_returns_true_for_existing(mock_create):
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"tweet_id": "123456"}]
    mock_create.return_value = mock_client

    db = Database("https://test.supabase.co", "key")
    assert db.is_tweet_seen("123456") is True


@patch("src.db.create_client")
def test_get_cached_account_returns_none_for_unknown(mock_create):
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    mock_create.return_value = mock_client

    db = Database("https://test.supabase.co", "key")
    assert db.get_cached_account("unknown_user") is None


@patch("src.db.create_client")
def test_get_today_reply_count(mock_create):
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value.data = [
        {"id": "1"}, {"id": "2"}, {"id": "3"}
    ]
    mock_create.return_value = mock_client

    db = Database("https://test.supabase.co", "key")
    assert db.get_today_reply_count() == 3


@patch("src.db.create_client")
def test_get_active_keywords(mock_create):
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"keyword": "AI agent trading"},
        {"keyword": "ERC-8004"},
    ]
    mock_create.return_value = mock_client

    db = Database("https://test.supabase.co", "key")
    assert db.get_active_keywords() == ["AI agent trading", "ERC-8004"]


@patch("src.db.create_client")
def test_get_active_accounts(mock_create):
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"username": "0xJeff"},
        {"username": "alexelorenzo"},
    ]
    mock_create.return_value = mock_client

    db = Database("https://test.supabase.co", "key")
    assert db.get_active_accounts() == ["0xJeff", "alexelorenzo"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && python -m pytest tests/test_db.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.db'`

- [ ] **Step 3: Write implementation**

`src/db.py`:

```python
from datetime import datetime, timezone
from supabase import create_client, Client


class Database:
    def __init__(self, url: str, key: str):
        self.client: Client = create_client(url, key)

    def is_tweet_seen(self, tweet_id: str) -> bool:
        result = self.client.table("tweets").select("tweet_id").eq("tweet_id", tweet_id).execute()
        return len(result.data) > 0

    def save_tweet(self, tweet: dict) -> None:
        self.client.table("tweets").upsert(tweet, on_conflict="tweet_id").execute()

    def get_cached_account(self, username: str) -> dict | None:
        result = self.client.table("account_cache").select("*").eq("username", username).execute()
        return result.data[0] if result.data else None

    def cache_account(self, username: str, account_type: str, bio: str, followers: int) -> None:
        self.client.table("account_cache").upsert({
            "username": username,
            "account_type": account_type,
            "bio": bio,
            "followers": followers,
            "classified_at": datetime.now(timezone.utc).isoformat(),
        }, on_conflict="username").execute()

    def get_today_reply_count(self) -> int:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00+00:00")
        result = (
            self.client.table("replies")
            .select("id")
            .eq("status", "posted")
            .gte("posted_at", today)
            .execute()
        )
        return len(result.data)

    def save_reply(self, reply: dict) -> None:
        self.client.table("replies").insert(reply).execute()

    def update_reply(self, reply_id: str, updates: dict) -> None:
        self.client.table("replies").update(updates).eq("id", reply_id).execute()

    def get_active_keywords(self) -> list[str]:
        result = self.client.table("monitored_keywords").select("keyword").eq("is_active", True).execute()
        return [row["keyword"] for row in result.data]

    def get_active_accounts(self) -> list[str]:
        result = self.client.table("monitored_accounts").select("username").eq("is_active", True).execute()
        return [row["username"] for row in result.data]

    def get_pending_replies(self) -> list[dict]:
        result = self.client.table("replies").select("*").eq("status", "pending").execute()
        return result.data
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m pytest tests/test_db.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/db.py tests/test_db.py
git commit -m "feat: add database module with Supabase queries"
```

---

### Task 4: Fetcher Module (Tweet Collection)

**Files:**
- Create: `src/fetcher.py`
- Create: `tests/test_fetcher.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_fetcher.py`:

```python
import json
from unittest.mock import patch, MagicMock
from src.fetcher import Fetcher


SAMPLE_SEARCH_OUTPUT = json.dumps({
    "ok": True,
    "schema_version": "1",
    "data": [
        {
            "id": "111",
            "text": "AI agents are changing DeFi",
            "author": {
                "id": "999",
                "name": "Test User",
                "screenName": "testuser",
                "profileImageUrl": "",
                "verified": False,
            },
            "metrics": {"likes": 10, "retweets": 2, "replies": 1, "views": 500},
            "createdAt": "Wed Apr 09 10:00:00 +0000 2026",
            "lang": "en",
        }
    ],
})

SAMPLE_USER_POSTS_OUTPUT = json.dumps({
    "ok": True,
    "schema_version": "1",
    "data": [
        {
            "id": "222",
            "text": "Just deployed a new trading agent",
            "author": {
                "id": "888",
                "name": "Alpha User",
                "screenName": "alphauser",
                "profileImageUrl": "",
                "verified": True,
            },
            "metrics": {"likes": 50, "retweets": 5, "replies": 3, "views": 2000},
            "createdAt": "Wed Apr 09 08:00:00 +0000 2026",
            "lang": "en",
        }
    ],
})


@patch("src.fetcher.subprocess.run")
def test_search_keyword(mock_run):
    mock_run.return_value = MagicMock(stdout=SAMPLE_SEARCH_OUTPUT, returncode=0)
    fetcher = Fetcher(twitter_env={"TWITTER_AUTH_TOKEN": "t", "TWITTER_CT0": "c"})
    tweets = fetcher.search_keyword("AI agent trading")
    assert len(tweets) == 1
    assert tweets[0]["tweet_id"] == "111"
    assert tweets[0]["content"] == "AI agents are changing DeFi"
    assert tweets[0]["author_username"] == "testuser"
    assert tweets[0]["source_type"] == "keyword"
    assert tweets[0]["source_value"] == "AI agent trading"


@patch("src.fetcher.subprocess.run")
def test_fetch_account_tweets(mock_run):
    mock_run.return_value = MagicMock(stdout=SAMPLE_USER_POSTS_OUTPUT, returncode=0)
    fetcher = Fetcher(twitter_env={"TWITTER_AUTH_TOKEN": "t", "TWITTER_CT0": "c"})
    tweets = fetcher.fetch_account_tweets("alphauser")
    assert len(tweets) == 1
    assert tweets[0]["tweet_id"] == "222"
    assert tweets[0]["source_type"] == "account"
    assert tweets[0]["source_value"] == "alphauser"


@patch("src.fetcher.subprocess.run")
def test_fetch_user_profile(mock_run):
    mock_run.return_value = MagicMock(
        stdout=json.dumps({
            "ok": True,
            "data": {
                "screenName": "testuser",
                "name": "Test User",
                "bio": "Crypto investor",
                "followers": 5000,
                "verified": False,
            },
        }),
        returncode=0,
    )
    fetcher = Fetcher(twitter_env={"TWITTER_AUTH_TOKEN": "t", "TWITTER_CT0": "c"})
    profile = fetcher.fetch_user_profile("testuser")
    assert profile["username"] == "testuser"
    assert profile["bio"] == "Crypto investor"
    assert profile["followers"] == 5000
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && python -m pytest tests/test_fetcher.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.fetcher'`

- [ ] **Step 3: Write implementation**

`src/fetcher.py`:

```python
import json
import os
import subprocess
from datetime import datetime, timezone


class Fetcher:
    def __init__(self, twitter_env: dict[str, str]):
        self.env = {**os.environ, **twitter_env}

    def _run_twitter(self, args: list[str]) -> dict | None:
        result = subprocess.run(
            ["twitter"] + args + ["--json"],
            capture_output=True,
            text=True,
            env=self.env,
        )
        if result.returncode != 0:
            return None
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
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
        data = self._run_twitter(["search", keyword, "--lang", "en", "-n", str(max_results)])
        if not data or not data.get("ok"):
            return []
        return [self._parse_tweet(t, "keyword", keyword) for t in data.get("data", [])]

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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m pytest tests/test_fetcher.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/fetcher.py tests/test_fetcher.py
git commit -m "feat: add fetcher module for tweet collection via twitter-cli"
```

---

### Task 5: Filters Module (Dedup, Classifier, Relevance)

**Files:**
- Create: `src/filters.py`
- Create: `tests/test_filters.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_filters.py`:

```python
from unittest.mock import MagicMock, AsyncMock, patch
from src.filters import Filters


def test_is_within_follower_range():
    f = Filters(db=MagicMock(), fetcher=MagicMock(), anthropic_client=MagicMock())
    assert f.is_within_follower_range(5000) is True
    assert f.is_within_follower_range(500) is False
    assert f.is_within_follower_range(150000) is False
    assert f.is_within_follower_range(1000) is True
    assert f.is_within_follower_range(100000) is True


def test_dedup_filters_seen_tweets():
    mock_db = MagicMock()
    mock_db.is_tweet_seen.side_effect = lambda tid: tid == "seen_1"
    f = Filters(db=mock_db, fetcher=MagicMock(), anthropic_client=MagicMock())

    tweets = [
        {"tweet_id": "seen_1", "content": "old"},
        {"tweet_id": "new_1", "content": "fresh"},
        {"tweet_id": "new_2", "content": "also fresh"},
    ]
    result = f.dedup(tweets)
    assert len(result) == 2
    assert result[0]["tweet_id"] == "new_1"


def test_classify_account_uses_cache():
    mock_db = MagicMock()
    mock_db.get_cached_account.return_value = {
        "username": "testuser",
        "account_type": "individual",
        "followers": 5000,
    }
    f = Filters(db=mock_db, fetcher=MagicMock(), anthropic_client=MagicMock())
    result = f.classify_account("testuser")
    assert result == "individual"
    f.anthropic_client.messages.create.assert_not_called()


def test_classify_account_calls_haiku_on_miss():
    mock_db = MagicMock()
    mock_db.get_cached_account.return_value = None

    mock_fetcher = MagicMock()
    mock_fetcher.fetch_user_profile.return_value = {
        "username": "newuser",
        "name": "New User",
        "bio": "Crypto trader, DeFi degen",
        "followers": 8000,
        "verified": False,
    }

    mock_anthropic = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="individual")]
    mock_anthropic.messages.create.return_value = mock_response

    f = Filters(db=mock_db, fetcher=mock_fetcher, anthropic_client=mock_anthropic)
    result = f.classify_account("newuser")

    assert result == "individual"
    mock_db.cache_account.assert_called_once_with("newuser", "individual", "Crypto trader, DeFi degen", 8000)


def test_check_relevance_returns_relevant():
    mock_anthropic = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="relevant")]
    mock_anthropic.messages.create.return_value = mock_response

    f = Filters(db=MagicMock(), fetcher=MagicMock(), anthropic_client=mock_anthropic)
    assert f.check_relevance("AI agents are reshaping DeFi trading") is True


def test_check_relevance_returns_irrelevant():
    mock_anthropic = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="irrelevant")]
    mock_anthropic.messages.create.return_value = mock_response

    f = Filters(db=MagicMock(), fetcher=MagicMock(), anthropic_client=mock_anthropic)
    assert f.check_relevance("Just had a great lunch") is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && python -m pytest tests/test_filters.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.filters'`

- [ ] **Step 3: Write implementation**

`src/filters.py`:

```python
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
    def __init__(self, db: Database, fetcher: Fetcher, anthropic_client: Anthropic):
        self.db = db
        self.fetcher = fetcher
        self.anthropic_client = anthropic_client

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

        prompt = CLASSIFY_PROMPT.format(
            username=profile["username"],
            name=profile["name"],
            bio=profile["bio"],
            verified=profile["verified"],
            followers=profile["followers"],
        )

        response = self.anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}],
        )
        account_type = response.content[0].text.strip().lower()
        if account_type not in ("individual", "organization"):
            account_type = "organization"

        self.db.cache_account(username, account_type, profile["bio"], profile["followers"])
        return account_type

    def check_relevance(self, content: str) -> bool:
        prompt = RELEVANCE_PROMPT.format(content=content)
        response = self.anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip().lower() == "relevant"

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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m pytest tests/test_filters.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/filters.py tests/test_filters.py
git commit -m "feat: add filters module with dedup, account classifier, relevance check"
```

---

### Task 6: Reply Generator Module

**Files:**
- Create: `src/generator.py`
- Create: `tests/test_generator.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_generator.py`:

```python
from unittest.mock import MagicMock
from src.generator import ReplyGenerator


def test_generate_reply_returns_text():
    mock_anthropic = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="great point, the multi-chain coordination problem is real — identity layer needs to be chain-agnostic for agents to truly interoperate")]
    mock_anthropic.messages.create.return_value = mock_response

    gen = ReplyGenerator(anthropic_client=mock_anthropic)
    result = gen.generate(
        tweet_content="Cross-chain agent coordination is the next frontier",
        author_username="testuser",
        author_bio="DeFi researcher",
        thread_context=None,
    )
    assert result is not None
    assert len(result) <= 280
    assert "SKIP" not in result


def test_generate_reply_returns_none_on_skip():
    mock_anthropic = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="SKIP")]
    mock_anthropic.messages.create.return_value = mock_response

    gen = ReplyGenerator(anthropic_client=mock_anthropic)
    result = gen.generate(
        tweet_content="Just had lunch",
        author_username="someone",
        author_bio="foodie",
        thread_context=None,
    )
    assert result is None


def test_generate_uses_sonnet_model():
    mock_anthropic = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="interesting take")]
    mock_anthropic.messages.create.return_value = mock_response

    gen = ReplyGenerator(anthropic_client=mock_anthropic)
    gen.generate(
        tweet_content="test",
        author_username="user",
        author_bio="bio",
        thread_context=None,
    )

    call_kwargs = mock_anthropic.messages.create.call_args.kwargs
    assert "sonnet" in call_kwargs["model"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && python -m pytest tests/test_generator.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.generator'`

- [ ] **Step 3: Write implementation**

`src/generator.py`:

```python
from anthropic import Anthropic

SYSTEM_PROMPT = """You are a crypto-native with deep knowledge of Web3 and AI agents.
You write helpful, insightful replies to tweets.

Rules:
- Never include links
- Never mention any specific service or product name
- No promotional language
- Provide genuinely useful information or perspectives on the tweet's topic
- Natural, casual tone that fits crypto Twitter culture
- English only
- Under 280 characters
- Only reply if you can add real value — return "SKIP" if not

Your expertise:
- On-chain AI agents (ERC-8004)
- Agent trading & performance analytics
- Intersection of DeFi and AI
- Multi-chain agent ecosystems (Ethereum, Base, Celo, Monad, BNB, etc.)"""

USER_PROMPT = """Write a reply to this tweet.

Author: @{username}
Bio: {bio}
Tweet: {content}
Thread context: {thread_context}

Write a useful reply relevant to this tweet's topic."""


class ReplyGenerator:
    def __init__(self, anthropic_client: Anthropic):
        self.client = anthropic_client

    def generate(
        self,
        tweet_content: str,
        author_username: str,
        author_bio: str,
        thread_context: str | None,
    ) -> str | None:
        prompt = USER_PROMPT.format(
            username=author_username,
            bio=author_bio,
            content=tweet_content,
            thread_context=thread_context or "None",
        )

        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=150,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text.strip()
        if text.upper() == "SKIP":
            return None
        if len(text) > 280:
            text = text[:277] + "..."
        return text
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m pytest tests/test_generator.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/generator.py tests/test_generator.py
git commit -m "feat: add reply generator module with Claude Sonnet"
```

---

### Task 7: Poster Module

**Files:**
- Create: `src/poster.py`
- Create: `tests/test_poster.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_poster.py`:

```python
import json
from unittest.mock import MagicMock, patch
from src.poster import Poster


@patch("src.poster.subprocess.run")
def test_post_reply_success(mock_run):
    mock_run.return_value = MagicMock(
        stdout=json.dumps({"ok": True, "data": {"id": "reply_999"}}),
        returncode=0,
    )
    poster = Poster(twitter_env={"TWITTER_AUTH_TOKEN": "t", "TWITTER_CT0": "c"})
    result = poster.post_reply("tweet_123", "great insight!")
    assert result is True


@patch("src.poster.subprocess.run")
def test_post_reply_failure(mock_run):
    mock_run.return_value = MagicMock(stdout="", returncode=1)
    poster = Poster(twitter_env={"TWITTER_AUTH_TOKEN": "t", "TWITTER_CT0": "c"})
    result = poster.post_reply("tweet_123", "text")
    assert result is False


@patch("src.poster.subprocess.run")
def test_check_auth_success(mock_run):
    mock_run.return_value = MagicMock(
        stdout=json.dumps({"ok": True, "data": {"authenticated": True}}),
        returncode=0,
    )
    poster = Poster(twitter_env={"TWITTER_AUTH_TOKEN": "t", "TWITTER_CT0": "c"})
    assert poster.check_auth() is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && python -m pytest tests/test_poster.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.poster'`

- [ ] **Step 3: Write implementation**

`src/poster.py`:

```python
import json
import logging
import os
import subprocess

logger = logging.getLogger(__name__)


class Poster:
    def __init__(self, twitter_env: dict[str, str]):
        self.env = {**os.environ, **twitter_env}

    def post_reply(self, tweet_id: str, text: str) -> bool:
        try:
            result = subprocess.run(
                ["twitter", "reply", tweet_id, text],
                capture_output=True,
                text=True,
                env=self.env,
            )
            if result.returncode != 0:
                logger.error("Failed to post reply: %s", result.stderr)
                return False
            data = json.loads(result.stdout)
            return data.get("ok", False)
        except Exception as e:
            logger.error("Error posting reply: %s", e)
            return False

    def check_auth(self) -> bool:
        try:
            result = subprocess.run(
                ["twitter", "status", "--json"],
                capture_output=True,
                text=True,
                env=self.env,
            )
            if result.returncode != 0:
                return False
            data = json.loads(result.stdout)
            return data.get("ok", False) and data.get("data", {}).get("authenticated", False)
        except Exception:
            return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m pytest tests/test_poster.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/poster.py tests/test_poster.py
git commit -m "feat: add poster module for reply posting via twitter-cli"
```

---

### Task 8: Telegram Bot Module

**Files:**
- Create: `src/telegram_bot.py`
- Create: `tests/test_telegram_bot.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_telegram_bot.py`:

```python
from src.telegram_bot import format_review_message


def test_format_review_message():
    msg = format_review_message(
        tweet_content="AI agents are the future of DeFi",
        author_username="cryptodegen",
        author_followers=15000,
        draft_reply="totally agree — the coordination layer between agents is what makes this real",
        reply_id="abc-123",
    )
    assert "@cryptodegen" in msg
    assert "15,000" in msg
    assert "AI agents are the future of DeFi" in msg
    assert "totally agree" in msg


def test_format_review_message_truncates_long_tweet():
    long_tweet = "x" * 500
    msg = format_review_message(
        tweet_content=long_tweet,
        author_username="user",
        author_followers=5000,
        draft_reply="reply",
        reply_id="abc",
    )
    assert len(msg) < 2000
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && python -m pytest tests/test_telegram_bot.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.telegram_bot'`

- [ ] **Step 3: Write implementation**

`src/telegram_bot.py`:

```python
import asyncio
import logging
from datetime import datetime, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from src.db import Database
from src.poster import Poster

logger = logging.getLogger(__name__)


def format_review_message(
    tweet_content: str,
    author_username: str,
    author_followers: int,
    draft_reply: str,
    reply_id: str,
) -> str:
    truncated = tweet_content[:300] + "..." if len(tweet_content) > 300 else tweet_content
    return (
        f"📝 Reply Draft\n\n"
        f"Original tweet by @{author_username} ({author_followers:,} followers):\n"
        f'"{truncated}"\n\n'
        f"Draft reply:\n"
        f'"{draft_reply}"\n\n'
        f"ID: {reply_id}"
    )


class TelegramReviewBot:
    def __init__(self, token: str, chat_id: str, db: Database, poster: Poster):
        self.token = token
        self.chat_id = chat_id
        self.db = db
        self.poster = poster
        self._editing: dict[int, str] = {}  # message_id -> reply_id

    async def send_review(self, tweet: dict, draft_reply: str, reply_id: str) -> None:
        app = Application.builder().token(self.token).build()
        async with app:
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Approve ✅", callback_data=f"approve:{reply_id}"),
                    InlineKeyboardButton("Reject ❌", callback_data=f"reject:{reply_id}"),
                    InlineKeyboardButton("Edit ✏️", callback_data=f"edit:{reply_id}"),
                ]
            ])
            cached = self.db.get_cached_account(tweet["author_username"])
            followers = cached["followers"] if cached else 0
            msg = format_review_message(
                tweet_content=tweet["content"],
                author_username=tweet["author_username"],
                author_followers=followers,
                draft_reply=draft_reply,
                reply_id=reply_id,
            )
            await app.bot.send_message(
                chat_id=self.chat_id,
                text=msg,
                reply_markup=keyboard,
            )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await query.answer()
        action, reply_id = query.data.split(":", 1)
        now = datetime.now(timezone.utc).isoformat()

        if action == "approve":
            reply_data = self.db.client.table("replies").select("*").eq("id", reply_id).execute().data
            if not reply_data:
                await query.edit_message_text("Reply not found.")
                return
            reply = reply_data[0]
            text = reply["final_text"] or reply["draft_text"]
            success = self.poster.post_reply(reply["tweet_id"], text)
            if success:
                self.db.update_reply(reply_id, {
                    "status": "posted",
                    "final_text": text,
                    "posted_at": now,
                    "reviewed_at": now,
                })
                await query.edit_message_text(f"✅ Posted reply to tweet {reply['tweet_id']}")
            else:
                await query.edit_message_text("❌ Failed to post reply. Check auth.")

        elif action == "reject":
            self.db.update_reply(reply_id, {"status": "rejected", "reviewed_at": now})
            await query.edit_message_text("❌ Reply rejected.")

        elif action == "edit":
            self._editing[query.message.message_id] = reply_id
            await query.edit_message_text(
                query.message.text + "\n\n✏️ Send your edited reply text:"
            )

    async def handle_edit_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = update.message.text.strip()
        if not self._editing:
            return

        reply_id = list(self._editing.values())[-1]
        del self._editing[list(self._editing.keys())[-1]]

        if len(text) > 280:
            await update.message.reply_text(f"❌ Too long ({len(text)} chars). Must be under 280.")
            return

        self.db.update_reply(reply_id, {"final_text": text})
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Approve ✅", callback_data=f"approve:{reply_id}"),
                InlineKeyboardButton("Reject ❌", callback_data=f"reject:{reply_id}"),
            ]
        ])
        await update.message.reply_text(
            f'Updated reply:\n"{text}"\n\nApprove or reject?',
            reply_markup=keyboard,
        )

    def run(self) -> None:
        app = Application.builder().token(self.token).build()
        app.add_handler(CallbackQueryHandler(self.handle_callback))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_edit_text))
        logger.info("Telegram review bot started")
        app.run_polling()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m pytest tests/test_telegram_bot.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/telegram_bot.py tests/test_telegram_bot.py
git commit -m "feat: add Telegram review bot with approve/reject/edit flow"
```

---

### Task 9: Pipeline Orchestrator

**Files:**
- Create: `src/pipeline.py`
- Create: `tests/test_pipeline.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_pipeline.py`:

```python
from unittest.mock import MagicMock, patch, AsyncMock
from src.pipeline import Pipeline


def make_pipeline(
    daily_count=0,
    keywords=None,
    accounts=None,
):
    mock_db = MagicMock()
    mock_db.get_today_reply_count.return_value = daily_count
    mock_db.get_active_keywords.return_value = keywords or ["AI agent trading"]
    mock_db.get_active_accounts.return_value = accounts or []

    mock_fetcher = MagicMock()
    mock_filters = MagicMock()
    mock_generator = MagicMock()
    mock_telegram = MagicMock()
    mock_telegram.send_review = AsyncMock()

    return Pipeline(
        db=mock_db,
        fetcher=mock_fetcher,
        filters=mock_filters,
        generator=mock_generator,
        telegram=mock_telegram,
    )


def test_pipeline_stops_at_daily_cap():
    p = make_pipeline(daily_count=10)
    result = p.run()
    assert result["skipped_reason"] == "daily_cap_reached"
    p.fetcher.search_keyword.assert_not_called()


def test_pipeline_fetches_and_filters():
    p = make_pipeline(keywords=["AI agent trading"])
    p.fetcher.search_keyword.return_value = [
        {"tweet_id": "1", "content": "AI agents rock", "author_username": "user1"},
    ]
    p.filters.dedup.return_value = [
        {"tweet_id": "1", "content": "AI agents rock", "author_username": "user1"},
    ]
    p.filters.filter_tweet.return_value = True
    p.generator.generate.return_value = "nice take on agent coordination"
    p.db.save_reply.return_value = None
    p.db.get_today_reply_count.return_value = 0

    result = p.run()
    assert result["drafts_created"] >= 1
    p.generator.generate.assert_called_once()


def test_pipeline_skips_when_generator_returns_none():
    p = make_pipeline(keywords=["test"])
    p.fetcher.search_keyword.return_value = [
        {"tweet_id": "1", "content": "lunch", "author_username": "user1"},
    ]
    p.filters.dedup.return_value = [
        {"tweet_id": "1", "content": "lunch", "author_username": "user1"},
    ]
    p.filters.filter_tweet.return_value = True
    p.generator.generate.return_value = None

    result = p.run()
    assert result["drafts_created"] == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && python -m pytest tests/test_pipeline.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.pipeline'`

- [ ] **Step 3: Write implementation**

`src/pipeline.py`:

```python
import asyncio
import logging
import uuid
from datetime import datetime, timezone

from src.config import Config
from src.db import Database
from src.fetcher import Fetcher
from src.filters import Filters
from src.generator import ReplyGenerator
from src.telegram_bot import TelegramReviewBot

logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(
        self,
        db: Database,
        fetcher: Fetcher,
        filters: Filters,
        generator: ReplyGenerator,
        telegram: TelegramReviewBot,
    ):
        self.db = db
        self.fetcher = fetcher
        self.filters = filters
        self.generator = generator
        self.telegram = telegram

    def run(self) -> dict:
        stats = {"tweets_fetched": 0, "tweets_filtered": 0, "drafts_created": 0}

        if self.db.get_today_reply_count() >= Config.DAILY_REPLY_CAP:
            logger.info("Daily cap reached, skipping run")
            stats["skipped_reason"] = "daily_cap_reached"
            return stats

        # Collect tweets from keywords
        all_tweets = []
        for keyword in self.db.get_active_keywords():
            tweets = self.fetcher.search_keyword(keyword)
            all_tweets.extend(tweets)

        # Collect tweets from monitored accounts
        for username in self.db.get_active_accounts():
            tweets = self.fetcher.fetch_account_tweets(username)
            all_tweets.extend(tweets)

        stats["tweets_fetched"] = len(all_tweets)

        # Dedup
        new_tweets = self.filters.dedup(all_tweets)

        # Save all new tweets
        for tweet in new_tweets:
            self.db.save_tweet(tweet)

        # Filter and generate
        for tweet in new_tweets:
            if self.db.get_today_reply_count() >= Config.DAILY_REPLY_CAP:
                logger.info("Daily cap reached mid-run")
                break

            if not self.filters.filter_tweet(tweet):
                stats["tweets_filtered"] += 1
                continue

            reply_text = self.generator.generate(
                tweet_content=tweet["content"],
                author_username=tweet["author_username"],
                author_bio=tweet.get("author_bio", ""),
                thread_context=tweet.get("thread_context"),
            )

            if reply_text is None:
                continue

            reply_id = str(uuid.uuid4())
            self.db.save_reply({
                "id": reply_id,
                "tweet_id": tweet["tweet_id"],
                "draft_text": reply_text,
                "final_text": None,
                "status": "pending",
                "reviewed_at": None,
                "posted_at": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

            asyncio.run(self.telegram.send_review(tweet, reply_text, reply_id))
            stats["drafts_created"] += 1

        logger.info("Pipeline run complete: %s", stats)
        return stats


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    from anthropic import Anthropic

    config = Config()
    db = Database(config.supabase_url, config.supabase_key)
    anthropic_client = Anthropic(api_key=config.anthropic_api_key)
    fetcher = Fetcher(twitter_env=config.twitter_env)
    flt = Filters(db=db, fetcher=fetcher, anthropic_client=anthropic_client)
    generator = ReplyGenerator(anthropic_client=anthropic_client)
    poster = Poster(twitter_env=config.twitter_env)
    telegram = TelegramReviewBot(config.telegram_bot_token, config.telegram_chat_id, db, poster)

    pipeline = Pipeline(db=db, fetcher=fetcher, filters=flt, generator=generator, telegram=telegram)
    pipeline.run()


if __name__ == "__main__":
    from src.poster import Poster
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m pytest tests/test_pipeline.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/pipeline.py tests/test_pipeline.py
git commit -m "feat: add pipeline orchestrator with full flow"
```

---

### Task 10: Seed Data Script & Supabase Schema

**Files:**
- Create: `scripts/seed_data.py`
- Create: `scripts/schema.sql`

- [ ] **Step 1: Create Supabase schema SQL**

`scripts/schema.sql`:

```sql
-- monitored_keywords
create table if not exists monitored_keywords (
  id uuid primary key default gen_random_uuid(),
  keyword text not null,
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

-- monitored_accounts
create table if not exists monitored_accounts (
  id uuid primary key default gen_random_uuid(),
  username text not null unique,
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

-- account_cache
create table if not exists account_cache (
  username text primary key,
  account_type text not null,
  bio text,
  followers integer,
  classified_at timestamptz not null default now()
);

-- tweets
create table if not exists tweets (
  id uuid primary key default gen_random_uuid(),
  tweet_id text not null unique,
  author_username text not null,
  author_bio text,
  content text not null,
  thread_context text,
  relevance_score text,
  source_type text not null,
  source_value text not null,
  fetched_at timestamptz not null default now()
);

-- replies
create table if not exists replies (
  id uuid primary key default gen_random_uuid(),
  tweet_id text not null references tweets(tweet_id),
  draft_text text not null,
  final_text text,
  status text not null default 'pending',
  reviewed_at timestamptz,
  posted_at timestamptz,
  created_at timestamptz not null default now()
);

-- indexes
create index if not exists idx_tweets_tweet_id on tweets(tweet_id);
create index if not exists idx_replies_status on replies(status);
create index if not exists idx_replies_posted_at on replies(posted_at);
```

- [ ] **Step 2: Create seed data script**

`scripts/seed_data.py`:

```python
"""Seed initial keywords and target accounts into Supabase."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from src.config import Config
from src.db import Database

KEYWORDS = [
    "AI agent trading",
    "on-chain agent",
    "ERC-8004",
    "agent economy crypto",
    "autonomous agent DeFi",
    "AI agent wallet",
    "crypto AI agents",
    "x402 payments",
    "DeFi automation agent",
    "onchain AI",
    "agent token trading",
]

ACCOUNTS = [
    "MoonDevOnYT",
    "0xJeff",
    "y0lloo",
    "rahul19_rahul",
    "0xPhilanthrop",
    "ns123abc",
    "alexelorenzo",
    "TheMaran",
    "Tanaka_L2",
    "TheGeorgePu",
    "2xnmore",
    "nirajhodler",
    "InvestWithD",
    "MillieMarconnni",
    "DeFiOracle_",
    "bittingthembits",
]


def main():
    config = Config()
    db = Database(config.supabase_url, config.supabase_key)

    print("Seeding keywords...")
    for kw in KEYWORDS:
        db.client.table("monitored_keywords").upsert(
            {"keyword": kw, "is_active": True},
            on_conflict="keyword",
        ).execute()
        print(f"  + {kw}")

    print("\nSeeding target accounts...")
    for acc in ACCOUNTS:
        db.client.table("monitored_accounts").upsert(
            {"username": acc, "is_active": True},
            on_conflict="username",
        ).execute()
        print(f"  + @{acc}")

    print("\nDone!")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Apply schema to Supabase**

Run the SQL in `scripts/schema.sql` via the Supabase dashboard SQL editor, or via CLI:

```bash
# Via Supabase dashboard: paste schema.sql content into SQL Editor and run
```

- [ ] **Step 4: Seed data**

Run: `source .venv/bin/activate && python scripts/seed_data.py`
Expected: All keywords and accounts seeded successfully.

- [ ] **Step 5: Commit**

```bash
git add scripts/schema.sql scripts/seed_data.py
git commit -m "feat: add Supabase schema and seed data script"
```

---

### Task 11: Cron Setup & Entry Points

**Files:**
- Create: `scripts/setup_cron.sh`
- Create: `run_pipeline.py` (root entry point)
- Create: `run_telegram.py` (root entry point)

- [ ] **Step 1: Create pipeline entry point**

`run_pipeline.py`:

```python
#!/usr/bin/env python3
"""Entry point for cron: runs the tweet collection + reply generation pipeline."""
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from anthropic import Anthropic
from src.config import Config
from src.db import Database
from src.fetcher import Fetcher
from src.filters import Filters
from src.generator import ReplyGenerator
from src.poster import Poster
from src.telegram_bot import TelegramReviewBot
from src.pipeline import Pipeline


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    config = Config()
    db = Database(config.supabase_url, config.supabase_key)
    anthropic_client = Anthropic(api_key=config.anthropic_api_key)
    fetcher = Fetcher(twitter_env=config.twitter_env)
    filters = Filters(db=db, fetcher=fetcher, anthropic_client=anthropic_client)
    generator = ReplyGenerator(anthropic_client=anthropic_client)
    poster = Poster(twitter_env=config.twitter_env)
    telegram = TelegramReviewBot(config.telegram_bot_token, config.telegram_chat_id, db, poster)

    pipeline = Pipeline(
        db=db, fetcher=fetcher, filters=filters,
        generator=generator, telegram=telegram,
    )
    stats = pipeline.run()
    print(f"Pipeline complete: {stats}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Create Telegram bot entry point**

`run_telegram.py`:

```python
#!/usr/bin/env python3
"""Entry point: runs the Telegram review bot (long-running process)."""
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

    config = Config()
    db = Database(config.supabase_url, config.supabase_key)
    poster = Poster(twitter_env=config.twitter_env)
    bot = TelegramReviewBot(config.telegram_bot_token, config.telegram_chat_id, db, poster)
    bot.run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Create cron setup script**

`scripts/setup_cron.sh`:

```bash
#!/bin/bash
# Install cron job for agentlynx-bot pipeline (every 2 hours)

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$SCRIPT_DIR/.venv/bin/python"
PIPELINE="$SCRIPT_DIR/run_pipeline.py"
LOG="$SCRIPT_DIR/logs/pipeline.log"

mkdir -p "$SCRIPT_DIR/logs"

# Add cron entry
CRON_LINE="0 */2 * * * cd $SCRIPT_DIR && $VENV $PIPELINE >> $LOG 2>&1"

(crontab -l 2>/dev/null | grep -v "run_pipeline.py"; echo "$CRON_LINE") | crontab -

echo "Cron job installed:"
echo "  $CRON_LINE"
echo ""
echo "Don't forget to start the Telegram bot as a background service:"
echo "  nohup $VENV $SCRIPT_DIR/run_telegram.py >> $SCRIPT_DIR/logs/telegram.log 2>&1 &"
```

- [ ] **Step 4: Commit**

```bash
git add run_pipeline.py run_telegram.py scripts/setup_cron.sh
git commit -m "feat: add entry points and cron setup"
```

---

### Task 12: Integration Test & Dry Run

- [ ] **Step 1: Run full test suite**

Run: `source .venv/bin/activate && python -m pytest tests/ -v`
Expected: All tests pass.

- [ ] **Step 2: Create .env with real credentials**

```bash
cp .env.example .env
# Edit .env with actual values:
# TWITTER_AUTH_TOKEN, TWITTER_CT0, ANTHROPIC_API_KEY,
# SUPABASE_URL, SUPABASE_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
```

- [ ] **Step 3: Apply Supabase schema**

Run the SQL from `scripts/schema.sql` in Supabase SQL editor.

- [ ] **Step 4: Seed data**

Run: `source .venv/bin/activate && python scripts/seed_data.py`

- [ ] **Step 5: Test pipeline dry run**

Run: `source .venv/bin/activate && python run_pipeline.py`
Expected: Pipeline runs, fetches tweets, filters, generates drafts, sends to Telegram.

- [ ] **Step 6: Test Telegram bot**

Run: `source .venv/bin/activate && python run_telegram.py`
Expected: Bot starts polling. Approve/reject a draft from Telegram.

- [ ] **Step 7: Install cron**

Run: `bash scripts/setup_cron.sh`
Expected: Cron job installed.

- [ ] **Step 8: Final commit**

```bash
git add -A
git commit -m "feat: complete agentlynx-bot v1 with pipeline, telegram review, and cron"
```
