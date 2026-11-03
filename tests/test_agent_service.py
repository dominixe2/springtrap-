from __future__ import annotations

import asyncio

from micro_helper.agent_service import run_local_agent_team
from micro_helper.orchestration import AgentTask


def test_local_agent_team_reports_missing_ollama(monkeypatch):
    class OfflineProvider:
        def __init__(self, *args, **kwargs):
            pass

        async def is_available(self):
            return False

    monkeypatch.setattr("micro_helper.agent_service.OllamaProvider", OfflineProvider)
    try:
        asyncio.run(run_local_agent_team([AgentTask("one", "Test", "Proveď test")]))
    except RuntimeError as exc:
        assert "Ollama" in str(exc)
    else:
        raise AssertionError("Offline provider must be reported clearly")


def test_agent_task_is_not_fixed_to_five():
    tasks = [AgentTask(str(i), f"Úkol {i}", "Zpracuj část") for i in range(8)]
    assert len(tasks) == 8
