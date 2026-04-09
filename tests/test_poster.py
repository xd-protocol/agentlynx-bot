import json
from unittest.mock import MagicMock, patch
from src.poster import Poster


@patch("src.poster.subprocess.run")
def test_post_reply_success(mock_run):
    mock_run.return_value = MagicMock(stdout=json.dumps({"ok": True, "data": {"id": "reply_999"}}), returncode=0)
    poster = Poster(twitter_env={"TWITTER_AUTH_TOKEN": "t", "TWITTER_CT0": "c"})
    result = poster.post_reply("tweet_123", "great insight!")
    assert result is True


@patch("src.poster.subprocess.run")
def test_post_reply_failure(mock_run):
    mock_run.return_value = MagicMock(stdout="", returncode=1)
    poster = Poster(twitter_env={"TWITTER_AUTH_TOKEN": "t", "TWITTER_CT0": "c"})
    result = poster.post_reply("tweet_123", "text")
    assert result is False


@patch("src.poster.subprocess.run")
def test_check_auth_success(mock_run):
    mock_run.return_value = MagicMock(stdout=json.dumps({"ok": True, "data": {"authenticated": True}}), returncode=0)
    poster = Poster(twitter_env={"TWITTER_AUTH_TOKEN": "t", "TWITTER_CT0": "c"})
    assert poster.check_auth() is True
