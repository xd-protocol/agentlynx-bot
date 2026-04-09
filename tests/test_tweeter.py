import json
from unittest.mock import MagicMock, patch
from src.tweeter import StatsCollector, Tweeter


SAMPLE_FILTER_OPTIONS = {"chains": [{"chain": "base", "count": 25000}], "serviceTypes": [{"type": "DeFi", "count": 5000}]}
SAMPLE_SUGGESTIONS = [{"agent_id": "1", "name": "TopAgent", "activity_score": 95}]
SAMPLE_TOP_AGENTS = [{"agent_id": "2", "name": "BestAgent", "score": 98}]


@patch("src.tweeter.requests.get")
def test_fetch_ecosystem_stats(mock_get):
    mock_get.return_value = MagicMock(status_code=200)
    mock_get.return_value.json.return_value = SAMPLE_FILTER_OPTIONS
    mock_get.return_value.raise_for_status = MagicMock()
    collector = StatsCollector("https://agentlynx.org")
    result = collector.fetch_ecosystem_stats()
    assert result == SAMPLE_FILTER_OPTIONS
    mock_get.assert_called_once_with("https://agentlynx.org/api/agents/filter-options", timeout=15)


@patch("src.tweeter.requests.get")
def test_fetch_trending_agents(mock_get):
    mock_get.return_value = MagicMock(status_code=200)
    mock_get.return_value.json.return_value = SAMPLE_SUGGESTIONS
    mock_get.return_value.raise_for_status = MagicMock()
    collector = StatsCollector("https://agentlynx.org")
    result = collector.fetch_trending_agents()
    assert result == SAMPLE_SUGGESTIONS


@patch("src.tweeter.requests.get")
def test_collect_all(mock_get):
    mock_get.return_value = MagicMock(status_code=200)
    mock_get.return_value.json.return_value = SAMPLE_FILTER_OPTIONS
    mock_get.return_value.raise_for_status = MagicMock()
    collector = StatsCollector("https://agentlynx.org")
    result = collector.collect_all()
    assert "ecosystem" in result
    assert "trending" in result
    assert "top_agents" in result


@patch("src.tweeter.subprocess.run")
def test_generate_tweet(mock_run):
    mock_run.return_value = MagicMock(stdout="AI agents on Base just crossed 25K registrations. DeFi automation is eating the chain", returncode=0)
    tweeter = Tweeter(stats_collector=MagicMock(), poster=MagicMock(), telegram=MagicMock(), db=MagicMock())
    result = tweeter.generate_tweet({"ecosystem": SAMPLE_FILTER_OPTIONS})
    assert result is not None
    assert len(result) <= 280


@patch("src.tweeter.subprocess.run")
def test_generate_tweet_truncates(mock_run):
    mock_run.return_value = MagicMock(stdout="x" * 300, returncode=0)
    tweeter = Tweeter(stats_collector=MagicMock(), poster=MagicMock(), telegram=MagicMock(), db=MagicMock())
    result = tweeter.generate_tweet({"data": "test"})
    assert len(result) <= 280


def test_run_stops_at_daily_cap():
    mock_db = MagicMock()
    mock_db.client.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.execute.return_value.data = [{"id": "1"}, {"id": "2"}]
    tweeter = Tweeter(stats_collector=MagicMock(), poster=MagicMock(), telegram=MagicMock(), db=mock_db)
    result = tweeter.run()
    assert result["skipped_reason"] == "daily_tweet_cap_reached"
