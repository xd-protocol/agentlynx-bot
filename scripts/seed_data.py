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
