from unittest.mock import MagicMock, patch
from src.generator import ReplyGenerator


@patch("src.generator.subprocess.run")
def test_generate_reply_returns_text(mock_run):
    mock_run.return_value = MagicMock(stdout="great point, the multi-chain coordination problem is real — identity layer needs to be chain-agnostic for agents to truly interoperate", returncode=0)
    gen = ReplyGenerator()
    result = gen.generate(tweet_content="Cross-chain agent coordination is the next frontier", author_username="testuser", author_bio="DeFi researcher", thread_context=None)
    assert result is not None
    assert len(result) <= 280
    assert "SKIP" not in result


@patch("src.generator.subprocess.run")
def test_generate_reply_returns_none_on_skip(mock_run):
    mock_run.return_value = MagicMock(stdout="SKIP", returncode=0)
    gen = ReplyGenerator()
    result = gen.generate(tweet_content="Just had lunch", author_username="someone", author_bio="foodie", thread_context=None)
    assert result is None


@patch("src.generator.subprocess.run")
def test_generate_uses_sonnet_model(mock_run):
    mock_run.return_value = MagicMock(stdout="interesting take", returncode=0)
    gen = ReplyGenerator()
    gen.generate(tweet_content="test", author_username="user", author_bio="bio", thread_context=None)
    call_args = mock_run.call_args[0][0]
    assert "--model" in call_args
    assert "sonnet" in call_args
