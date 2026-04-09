# AgentLynx X Reply Bot — Design Spec

## Overview

X(Twitter) bot that monitors relevant crypto/AI agent tweets and posts contextually valuable replies to organically drive traffic to AgentLynx (agentlynx.org) — an on-chain AI agent directory and analytics platform tracking 71,000+ ERC-8004 agents.

**Strategy:** Replies contain no links or service mentions. Value-first information replies build credibility; traffic comes from the bot account's profile/bio.

## Architecture

Single-script cron pipeline, running every 2 hours on the current server.

```
[Cron] → [Fetcher] → [Dedup] → [Account Classifier] → [Follower Filter]
       → [Relevance Filter] → [Daily Cap Check] → [Reply Generator]
       → [Telegram Review] → [Poster]
```

## Pipeline Steps

### 1. Fetcher (Tweet Collection)

**Tool:** Agent Reach (twitter-cli) with cookie-based auth.

Two collection paths run in parallel:

- **Keyword search:** Query X for tweets matching configured keywords.
- **Target account monitoring:** Fetch recent tweets from registered individual accounts.

Initial keywords:
- `AI agent trading`, `on-chain agent`, `ERC-8004`, `agent economy crypto`
- `autonomous agent DeFi`, `AI agent wallet`, `crypto AI agents`
- `x402 payments`, `DeFi automation agent`, `onchain AI`, `agent token trading`

### 2. Dedup (Duplicate Check)

Check each tweet's `tweet_id` against the `tweets` table in Supabase. Skip already-seen tweets.

### 3. Account Classifier (Individual vs Organization)

For each tweet author not yet in `account_cache`:

- Fetch author profile via `twitter user {username}`
- Send profile to **Claude Haiku** for classification:

```
Classify this X account as "individual" or "organization".

Username: @{username}
Display name: {name}
Bio: {bio}
Verified: {verified}
Followers: {followers}

"individual" = real person (influencer, developer, researcher, trader, etc.)
"organization" = company, protocol, DAO, VC fund, exchange, lab, foundation, media outlet, bot

Reply with ONLY "individual" or "organization".
```

- Cache result in `account_cache` table. Skip classification for known accounts.

### 4. Follower Filter

Pass only tweets from **individual** accounts with **1,000 - 100,000 followers**.

- Under 1K: low exposure value
- Over 100K: replies get buried in hundreds of other replies

### 5. Relevance Filter

Send tweet content to **Claude Haiku**:

```
Is this tweet relevant to on-chain AI agents, agent trading,
DeFi automation, or the agent economy?

Tweet: {content}

Reply with ONLY "relevant" or "irrelevant".
```

Skip irrelevant tweets.

### 6. Daily Cap Check

Query `replies` table for today's posted count. Stop if >= 10.

Target: **5-10 replies per day** (conservative, account safety first).

### 7. Reply Generator

Send tweet + context to **Claude Sonnet** (or latest equivalent):

**System prompt:**

```
You are a crypto-native with deep knowledge of Web3 and AI agents.
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
- Multi-chain agent ecosystems (Ethereum, Base, Celo, Monad, BNB, etc.)
```

**User prompt:**

```
Write a reply to this tweet.

Author: @{username}
Bio: {bio}
Tweet: {content}
Thread context: {thread_context or "None"}

Write a useful reply relevant to this tweet's topic.
```

If Claude returns "SKIP", discard the tweet.

### 8. Telegram Review

Send to Telegram bot:

```
📝 Reply Draft

Original tweet by @{username} ({followers} followers):
"{tweet_content}"

Draft reply:
"{draft_reply}"

[Approve ✅] [Reject ❌] [Edit ✏️]
```

- **Approve:** Proceed to posting
- **Reject:** Discard, log as rejected
- **Edit:** User sends replacement text (validated to be under 280 chars), that text is posted instead

### 9. Poster

Post approved reply via Agent Reach: `twitter reply {tweet_id} "{text}"`

Log result and send confirmation to Telegram.

## Data Model (Supabase)

### `monitored_keywords`

| Column | Type | Description |
|---|---|---|
| id | uuid | PK |
| keyword | text | Search keyword |
| is_active | boolean | Active flag |
| created_at | timestamptz | Created at |

### `monitored_accounts`

| Column | Type | Description |
|---|---|---|
| id | uuid | PK |
| username | text | X username (UNIQUE) |
| is_active | boolean | Active flag |
| created_at | timestamptz | Created at |

### `account_cache`

| Column | Type | Description |
|---|---|---|
| username | text | PK |
| account_type | text | 'individual' / 'organization' |
| bio | text | Bio at classification time |
| followers | integer | Follower count |
| classified_at | timestamptz | Classification time |

### `tweets`

| Column | Type | Description |
|---|---|---|
| id | uuid | PK |
| tweet_id | text | X tweet unique ID (UNIQUE) |
| author_username | text | Author |
| author_bio | text | Author bio |
| content | text | Tweet body |
| thread_context | text | Thread context (nullable) |
| relevance_score | text | 'relevant' / 'irrelevant' |
| source_type | text | 'keyword' or 'account' |
| source_value | text | Matched keyword or account |
| fetched_at | timestamptz | Fetch time |

### `replies`

| Column | Type | Description |
|---|---|---|
| id | uuid | PK |
| tweet_id | text | FK -> tweets.tweet_id |
| draft_text | text | Claude-generated draft |
| final_text | text | Final posted text (nullable) |
| status | text | 'pending' / 'approved' / 'rejected' / 'posted' |
| reviewed_at | timestamptz | Review time (nullable) |
| posted_at | timestamptz | Post time (nullable) |
| created_at | timestamptz | Created at |

## Target Policy

### Account Type Filter

Only reply to **individual** accounts. Claude Haiku classifies accounts; results are cached in `account_cache`.

### Follower Range

**1,000 - 100,000 followers only.**

### Initial Target Accounts (Tier 1 — monitored)

| Account | Followers | Focus |
|---|---|---|
| @MoonDevOnYT | 81K | Trading bot builder |
| @0xJeff | 78K | Researcher/investor |
| @y0lloo | 75K | Memecoin deployer |
| @rahul19_rahul | 64K | NFT founder, Web3 marketer |
| @0xPhilanthrop | 59K | Crypto investor |
| @ns123abc | 59K | Tech/AI crypto |
| @alexelorenzo | 48K | CoinPicks Capital CIO |
| @TheMaran | 47K | Quant, Web3/AI |
| @Tanaka_L2 | 46K | KOL manager, DeFi creator |
| @TheGeorgePu | 43K | AI builder |
| @2xnmore | 42K | Crypto education |
| @nirajhodler | 23K | Crypto investor, 10yr |
| @InvestWithD | 21K | Crypto news (Diana) |
| @MillieMarconnni | 19K | AI startup founder |
| @DeFiOracle_ | 18K | DeFi researcher |
| @bittingthembits | 11K | $TAO investor (Andy) |

### Exclusion Rules

- Organization/project/protocol accounts
- Followers < 1,000 or > 100,000
- Already-replied tweets
- Own tweets
- Daily cap (10) reached
- Claude returns "SKIP" (no value to add)
- Claude returns "irrelevant" (off-topic)

### Priority Signals

- Question-style tweets ("anyone know...", "which agent...")
- Active discussion threads
- Topics directly overlapping AgentLynx expertise

## Cost Estimates

| Step | Model | Frequency | Est. Monthly Cost |
|---|---|---|---|
| Account classification | Haiku | ~50 new accounts/month | ~$0.50 |
| Relevance filter | Haiku | ~200 tweets/day | ~$3 |
| Reply generation | Sonnet | ~10/day | ~$5 |
| **Total** | | | **~$8.50/month** |

## Tech Stack

- **Runtime:** Python 3.11+
- **X Access:** Agent Reach (twitter-cli, cookie-based)
- **LLM:** Claude API (Haiku for classification/filtering, Sonnet for generation)
- **Database:** Supabase (PostgreSQL)
- **Notifications:** Telegram Bot API
- **Scheduling:** System cron
- **Environment:** Current server (/home/me/agentlynx-bot)

## Bot Account

- **Username:** @agent_lynx
- **Bio:** "Professional Network for AI Agents"
- **Profile should link to:** agentlynx.org

## Risk Mitigation

- **Account suspension:** Conservative rate (5-10/day), no links in replies, no promotional language
- **Cookie expiration:** Monitor via `twitter status`; alert on Telegram if auth fails
- **Spam detection:** Unique, contextual replies only; Claude SKIP for low-value tweets
- **Quality control:** Human review via Telegram before every post
