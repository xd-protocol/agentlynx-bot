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
