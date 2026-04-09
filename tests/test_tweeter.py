import json
from unittest.mock import MagicMock, patch
from src.tweeter import StatsCollector, Tweeter


SAMPLE_FILTER_OPTIONS = {"chains": [{"id": 8453, "count": 25000}], "serviceTypes": [{"type": "DeFi", "count": 5000}]}
SAMPLE_SUGGESTIONS = [{"agent_id": "1", "chain_id": 8453, "name": "TopAgent", "activity_score": 95}]
SAMPLE_TOP_AGENTS = [{"agent_id": "2", "chain_id": 1, "name": "BestAgent", "score": 98}]


@patch("src.tweeter.requests.get")
def test_fetch_ecosystem_stats(mock_get):
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = SAMPLE_FILTER_OPTIONS
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp
    collector = StatsCollector("https://agentlynx.org")
    result = collector.fetch_ecosystem_stats()
    assert result == SAMPLE_FILTER_OPTIONS


@patch("src.tweeter.requests.get")
def test_fetch_trending_agents(mock_get):
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = SAMPLE_SUGGESTIONS
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp
    collector = StatsCollector("https://agentlynx.org")
    result = collector.fetch_trending_agents()
    assert result == SAMPLE_SUGGESTIONS


@patch("src.tweeter.subprocess.run")
def test_generate_tweet(mock_run):
    mock_run.return_value = MagicMock(stdout="Agent TopAgent on Base just crossed 25K volume", returncode=0)
    tweeter = Tweeter(stats_collector=MagicMock(), poster=MagicMock(), telegram=MagicMock(), db=MagicMock())
    result = tweeter.generate_tweet("agent_highlight", {"name": "TopAgent", "chain": "Base"})
    assert result is not None
    assert len(result) <= 280


@patch("src.tweeter.subprocess.run")
def test_generate_tweet_truncates(mock_run):
    mock_run.return_value = MagicMock(stdout="x" * 300, returncode=0)
    tweeter = Tweeter(stats_collector=MagicMock(), poster=MagicMock(), telegram=MagicMock(), db=MagicMock())
    result = tweeter.generate_tweet("anomaly", {"data": "test"})
    assert len(result) <= 280


def test_run_stops_at_daily_cap():
    mock_db = MagicMock()
    mock_db.client.table.return_value.select.return_value.eq.return_value.in_.return_value.gte.return_value.execute.return_value.data = [
        {"id": "1"}, {"id": "2"}, {"id": "3"}
    ]
    tweeter = Tweeter(stats_collector=MagicMock(), poster=MagicMock(), telegram=MagicMock(), db=mock_db)
    result = tweeter.run()
    assert result["skipped_reason"] == "daily_tweet_cap_reached"


def test_get_next_tweet_type_rotation():
    mock_db = MagicMock()
    # 0 tweets today -> agent_highlight
    mock_db.client.table.return_value.select.return_value.eq.return_value.in_.return_value.gte.return_value.execute.return_value.data = []
    tweeter = Tweeter(stats_collector=MagicMock(), poster=MagicMock(), telegram=MagicMock(), db=mock_db)
    assert tweeter._get_next_tweet_type() == "agent_highlight"

    # 1 tweet today -> anomaly
    mock_db.client.table.return_value.select.return_value.eq.return_value.in_.return_value.gte.return_value.execute.return_value.data = [{"tweet_id": "1"}]
    assert tweeter._get_next_tweet_type() == "anomaly"

    # 2 tweets today -> comparison
    mock_db.client.table.return_value.select.return_value.eq.return_value.in_.return_value.gte.return_value.execute.return_value.data = [{"tweet_id": "1"}, {"tweet_id": "2"}]
    assert tweeter._get_next_tweet_type() == "comparison"
