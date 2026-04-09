import subprocess

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
    def __init__(self):
        pass

    def generate(self, tweet_content: str, author_username: str, author_bio: str, thread_context: str | None) -> str | None:
        user_prompt = USER_PROMPT.format(username=author_username, bio=author_bio, content=tweet_content, thread_context=thread_context or "None")
        full_prompt = f"{SYSTEM_PROMPT}\n\n{user_prompt}"
        result = subprocess.run(
            ["claude", "-p", full_prompt, "--model", "sonnet"],
            capture_output=True, text=True
        )
        text = result.stdout.strip()
        if text.upper() == "SKIP":
            return None
        if len(text) > 280:
            text = text[:277] + "..."
        return text
