from unittest.mock import MagicMock
from src.generator import ReplyGenerator


def test_generate_reply_returns_text():
    mock_anthropic = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="great point, the multi-chain coordination problem is real — identity layer needs to be chain-agnostic for agents to truly interoperate")]
    mock_anthropic.messages.create.return_value = mock_response
    gen = ReplyGenerator(anthropic_client=mock_anthropic)
    result = gen.generate(tweet_content="Cross-chain agent coordination is the next frontier", author_username="testuser", author_bio="DeFi researcher", thread_context=None)
    assert result is not None
    assert len(result) <= 280
    assert "SKIP" not in result


def test_generate_reply_returns_none_on_skip():
    mock_anthropic = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="SKIP")]
    mock_anthropic.messages.create.return_value = mock_response
    gen = ReplyGenerator(anthropic_client=mock_anthropic)
    result = gen.generate(tweet_content="Just had lunch", author_username="someone", author_bio="foodie", thread_context=None)
    assert result is None


def test_generate_uses_sonnet_model():
    mock_anthropic = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="interesting take")]
    mock_anthropic.messages.create.return_value = mock_response
    gen = ReplyGenerator(anthropic_client=mock_anthropic)
    gen.generate(tweet_content="test", author_username="user", author_bio="bio", thread_context=None)
    call_kwargs = mock_anthropic.messages.create.call_args.kwargs
    assert "sonnet" in call_kwargs["model"]
