from pathlib import Path


def test_summarize_uses_nvidia_nim_openai_client(monkeypatch):
    from digest import summarizer

    calls = {}

    class FakeCompletions:
        def create(self, **kwargs):
            calls["create_kwargs"] = kwargs

            class Message:
                content = '{"entity_summaries": [], "macro_note": "x"}'

            class Choice:
                message = Message()

            class Response:
                choices = [Choice()]

            return Response()

    class FakeChat:
        completions = FakeCompletions()

    class FakeOpenAI:
        def __init__(self, *, base_url, api_key):
            calls["base_url"] = base_url
            calls["api_key"] = api_key
            self.chat = FakeChat()

    monkeypatch.setattr(summarizer, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(summarizer, "NVIDIA_API_KEY", "test-nvidia-key")

    enriched = {"trades": [], "institutional": [], "crypto": []}
    result = summarizer.summarize(enriched, {}, "2026-01-01", "2026-01-07")

    assert calls["base_url"] == "https://integrate.api.nvidia.com/v1"
    assert calls["api_key"] == "test-nvidia-key"
    assert calls["create_kwargs"]["model"] == "mistralai/mistral-medium-3.5-128b"
    assert calls["create_kwargs"]["response_format"] == {"type": "json_object"}
    assert set(result) >= {"entity_summaries", "macro_note"}


def test_summarize_raises_clear_error_on_empty_completion(monkeypatch):
    import pytest

    from digest import summarizer

    class FakeCompletions:
        def create(self, **kwargs):
            class Message:
                content = None

            class Choice:
                message = Message()
                finish_reason = "stop"

            class Response:
                choices = [Choice()]

            return Response()

    class FakeChat:
        completions = FakeCompletions()

    class FakeOpenAI:
        def __init__(self, *, base_url, api_key):
            self.chat = FakeChat()

    monkeypatch.setattr(summarizer, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(summarizer, "NVIDIA_API_KEY", "test-nvidia-key")

    enriched = {"trades": [], "institutional": [], "crypto": []}

    with pytest.raises(RuntimeError, match="Empty completion"):
        summarizer.summarize(enriched, {}, "2026-01-01", "2026-01-07")


def test_summarizer_source_uses_nvidia_endpoint():
    source = Path("digest/summarizer.py").read_text()
    assert "https://integrate.api.nvidia.com/v1" in source
