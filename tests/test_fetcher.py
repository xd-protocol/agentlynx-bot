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
