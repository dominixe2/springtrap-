from fastapi.testclient import TestClient
import pytest

import micro_helper.api as api
from micro_helper import providers


client = TestClient(api.app)


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "DATABASE_PATH", tmp_path / "providers.sqlite3")


def test_provider_catalog_never_exposes_secrets(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "secret-test-value")
    response = client.get("/v1/providers")
    assert response.status_code == 200
    body = response.json()
    gemini = next(item for item in body["providers"] if item["id"] == "gemini")
    assert gemini["configured"] is True
    assert "secret-test-value" not in response.text


@pytest.mark.anyio
async def test_gemini_adapter_uses_server_side_key(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"candidates": [{"content": {"parts": [{"text": "Ahoj z Gemini"}]}}]}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, params, json):
            captured.update(url=url, params=params, json=json)
            return FakeResponse()

    monkeypatch.setenv("GEMINI_API_KEY", "server-secret")
    monkeypatch.setattr(providers.httpx, "AsyncClient", FakeClient)
    answer = await providers.generate_chat(
        "gemini", "gemini-test", [{"role": "system", "content": "Piš česky"}, {"role": "user", "content": "Ahoj"}]
    )
    assert answer == "Ahoj z Gemini"
    assert captured["params"]["key"] == "server-secret"
    assert captured["json"]["systemInstruction"]["parts"][0]["text"] == "Piš česky"


def test_unknown_provider_is_rejected():
    response = client.post("/v1/chat", json={"message": "Ahoj", "provider": "unknown"})
    assert response.status_code == 422


def test_unconfigured_gemini_returns_actionable_error(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    response = client.post("/v1/chat", json={"message": "Ahoj", "provider": "gemini"})
    assert response.status_code == 200
    assert "GEMINI_API_KEY" in response.json()["error"]
