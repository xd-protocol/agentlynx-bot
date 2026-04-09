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
