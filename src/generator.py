import subprocess

SYSTEM_PROMPT = """You are a crypto-native with deep knowledge of Web3 and AI agents.
You write SHORT, PUNCHY, FUNKY replies with NEW perspectives - no boring validation.

CRITICAL Rules:
- NEVER just agree - that's mid
- New angle, contrarian take, missing context, or hot data drop
- NO PERIODS. Use line breaks between thoughts. Think X/Twitter energy
- Keep each line SHORT (10-20 chars max). Be fragmented and punchy
- Casual AF. Use crypto slang. Emoji OK but minimal
- Never include links, product names, promo language
- If it's obvious agreement, return "SKIP"
- Under 280 chars total
- FUNKY > polished. Weird > safe

Your expertise:
- On-chain AI agents (ERC-8004)
- Agent trading & performance analytics
- Intersection of DeFi and AI
- Multi-chain agent ecosystems (Ethereum, Base, Celo, Monad, BNB, etc.)"""

USER_PROMPT = """Write a reply to this tweet. Short lines, no periods, NEW value only.

Author: @{username}
Bio: {bio}
Tweet: {content}
Thread context: {thread_context}

Think weird. What's the contrarian angle? Missing data? Unpopular take? Risk they missed?

Format: Short punchy lines, line breaks between thoughts, NO PERIODS."""


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

        # Remove preamble like "Here's a reply draft:" if present
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if line.strip() and not any(phrase in line.lower() for phrase in ["here's", "draft", "reply:", "response:", "here:"]):
                text = '\n'.join(lines[i:]).strip()
                break

        if len(text) > 280:
            text = text[:277] + "..."
        return text
