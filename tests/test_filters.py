from unittest.mock import MagicMock, patch
from src.filters import Filters


def test_is_within_follower_range():
    f = Filters(db=MagicMock(), fetcher=MagicMock())
    assert f.is_within_follower_range(5000) is True
    assert f.is_within_follower_range(500) is False
    assert f.is_within_follower_range(150000) is False
    assert f.is_within_follower_range(1000) is True
    assert f.is_within_follower_range(100000) is True


def test_dedup_filters_seen_tweets():
    mock_db = MagicMock()
    mock_db.is_tweet_seen.side_effect = lambda tid: tid == "seen_1"
    f = Filters(db=mock_db, fetcher=MagicMock())
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
    mock_db.get_cached_account.return_value = {"username": "testuser", "account_type": "individual", "followers": 5000}
    f = Filters(db=mock_db, fetcher=MagicMock())
    result = f.classify_account("testuser")
    assert result == "individual"


@patch("src.filters.subprocess.run")
def test_classify_account_calls_haiku_on_miss(mock_run):
    mock_db = MagicMock()
    mock_db.get_cached_account.return_value = None
    mock_fetcher = MagicMock()
    mock_fetcher.fetch_user_profile.return_value = {"username": "newuser", "name": "New User", "bio": "Crypto trader, DeFi degen", "followers": 8000, "verified": False}
    mock_run.return_value = MagicMock(stdout="individual", returncode=0)
    f = Filters(db=mock_db, fetcher=mock_fetcher)
    result = f.classify_account("newuser")
    assert result == "individual"
    mock_db.cache_account.assert_called_once_with("newuser", "individual", "Crypto trader, DeFi degen", 8000)


@patch("src.filters.subprocess.run")
def test_check_relevance_returns_relevant(mock_run):
    mock_run.return_value = MagicMock(stdout="relevant", returncode=0)
    f = Filters(db=MagicMock(), fetcher=MagicMock())
    assert f.check_relevance("AI agents are reshaping DeFi trading") is True


@patch("src.filters.subprocess.run")
def test_check_relevance_returns_irrelevant(mock_run):
    mock_run.return_value = MagicMock(stdout="irrelevant", returncode=0)
    f = Filters(db=MagicMock(), fetcher=MagicMock())
    assert f.check_relevance("Just had a great lunch") is False
