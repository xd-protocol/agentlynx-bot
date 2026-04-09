from unittest.mock import MagicMock, patch
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
    mock_db.get_cached_account.return_value = {"username": "testuser", "account_type": "individual", "followers": 5000}
    f = Filters(db=mock_db, fetcher=MagicMock(), anthropic_client=MagicMock())
    result = f.classify_account("testuser")
    assert result == "individual"
    f.anthropic_client.messages.create.assert_not_called()


def test_classify_account_calls_haiku_on_miss():
    mock_db = MagicMock()
    mock_db.get_cached_account.return_value = None
    mock_fetcher = MagicMock()
    mock_fetcher.fetch_user_profile.return_value = {"username": "newuser", "name": "New User", "bio": "Crypto trader, DeFi degen", "followers": 8000, "verified": False}
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
