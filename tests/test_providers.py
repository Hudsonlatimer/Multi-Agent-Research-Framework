import pytest

from research_team.errors import ResearchError, classify_provider_error
from research_team.llm import DEFAULT_MODELS, get_chat_model, resolve_model, resolve_provider


@pytest.fixture
def quiet_env(monkeypatch):
    monkeypatch.setattr("research_team.llm.load_dotenv", lambda *args, **kwargs: None)
    for name in (
        "LLM_PROVIDER",
        "GROQ_API_KEY",
        "GROQ_MODEL",
        "TOGETHER_API_KEY",
        "TOGETHER_MODEL",
        "GEMINI_API_KEY",
        "GEMINI_MODEL",
        "OLLAMA_MODEL",
        "PLANNER_MODEL",
        "RESEARCHER_MODEL",
        "CRITIC_MODEL",
        "WRITER_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)


def test_default_provider_is_groq(quiet_env):
    assert resolve_provider(None) == "groq"


def test_unknown_provider_is_named(quiet_env):
    with pytest.raises(ResearchError) as caught:
        resolve_provider("openai")
    assert caught.value.kind == "provider_error"
    assert caught.value.provider == "openai"


@pytest.mark.parametrize("provider", ["groq", "together", "gemini", "ollama"])
def test_default_models(quiet_env, provider):
    assert resolve_model(provider) == DEFAULT_MODELS[provider]


def test_role_override_wins(quiet_env, monkeypatch):
    monkeypatch.setenv("PLANNER_MODEL", "small-model")
    monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-120b")
    assert resolve_model("groq", role="planner") == "small-model"
    assert resolve_model("groq", role="writer") == "openai/gpt-oss-120b"


def test_missing_groq_key(quiet_env):
    with pytest.raises(ResearchError) as caught:
        get_chat_model("groq")
    assert caught.value.kind == "missing_key"
    assert caught.value.provider == "groq"
    assert "GROQ_API_KEY" in str(caught.value)


def test_factory_passes_the_selected_model(quiet_env, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    captured = {}

    def fake_build(provider, model, api_key):
        captured.update(provider=provider, model=model, api_key=api_key)
        return object()

    monkeypatch.setattr("research_team.llm.build_chat_model", fake_build)
    handle = get_chat_model("groq", role="writer")
    assert captured == {"provider": "groq", "model": "openai/gpt-oss-120b", "api_key": "test-key"}
    assert handle.provider == "groq"
    assert handle.model == "openai/gpt-oss-120b"


def test_ollama_does_not_need_a_key(quiet_env, monkeypatch):
    monkeypatch.setattr(
        "research_team.llm.build_chat_model", lambda provider, model, api_key: object()
    )
    handle = get_chat_model("ollama")
    assert handle.provider == "ollama"
    assert handle.model == "qwen2.5:7b"


def test_rate_limit_classification():
    error = classify_provider_error("groq", RuntimeError("429 too many requests"))
    assert error.kind == "rate_limit"
    assert error.provider == "groq"


def test_clients_construct_without_a_network_call():
    from research_team.llm import build_chat_model

    groq = build_chat_model("groq", "openai/gpt-oss-120b", "test-key")
    together = build_chat_model("together", "openai/gpt-oss-120b", "test-key")
    gemini = build_chat_model("gemini", "gemini-3.8-flash", "test-key")
    ollama = build_chat_model("ollama", "qwen2.5:7b", None)
    assert groq is not None
    assert together is not None
    assert gemini is not None
    assert ollama is not None
