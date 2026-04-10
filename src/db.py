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

    def get_reply(self, reply_id: str) -> dict | None:
        result = self.client.table("replies").select("*").eq("id", reply_id).execute()
        return result.data[0] if result.data else None
