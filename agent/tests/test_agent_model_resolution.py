import logging

from agent.agent_config_module import agent_config


def _clear_model_env(monkeypatch):
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_BASE_URL", raising=False)
    monkeypatch.delenv("ZHIPUAI_API_KEY", raising=False)
    monkeypatch.delenv("ZHIPUAI_BASE_URL", raising=False)


def test_defaults_to_deepseek_when_llm_model_missing(monkeypatch, caplog):
    _clear_model_env(monkeypatch)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-key")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

    with caplog.at_level(logging.WARNING):
        cfg = agent_config.load_config_from_env()

    assert cfg.llm.model == "deepseek-chat"
    assert cfg.llm.api_key == "deepseek-key"
    assert cfg.llm.base_url == "https://api.deepseek.com"
    assert "LLM_MODEL is not set" in caplog.text


def test_llm_model_glm_uses_zhipu_credentials(monkeypatch):
    _clear_model_env(monkeypatch)
    monkeypatch.setenv("LLM_MODEL", "glm-5")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-key")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    monkeypatch.setenv("ZHIPUAI_API_KEY", "zhipu-key")
    monkeypatch.setenv("ZHIPUAI_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")

    cfg = agent_config.load_config_from_env()

    assert cfg.llm.model == "glm-5"
    assert cfg.llm.api_key == "zhipu-key"
    assert cfg.llm.base_url == "https://open.bigmodel.cn/api/paas/v4"


def test_blank_llm_model_falls_back_to_default(monkeypatch):
    _clear_model_env(monkeypatch)
    monkeypatch.setenv("LLM_MODEL", "   ")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-key")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

    cfg = agent_config.load_config_from_env()

    assert cfg.llm.model == "deepseek-chat"
    assert cfg.llm.api_key == "deepseek-key"
    assert cfg.llm.base_url == "https://api.deepseek.com"
