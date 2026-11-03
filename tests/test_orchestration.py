import asyncio

import pytest

from micro_helper.orchestration import AgentTask, run_agent_team


class FakeProvider:
    def __init__(self, name, fail=False):
        self.name = name
        self.fail = fail
        self.seen_context = []

    async def complete(self, task, shared_context):
        self.seen_context.append(shared_context)
        if self.fail:
            raise RuntimeError("provider offline")
        await asyncio.sleep(0)
        return f"{self.name}: {task.title}"


@pytest.mark.asyncio
async def test_team_runs_all_tasks_and_synthesizes_shared_context():
    first = FakeProvider("local")
    second = FakeProvider("cloud")
    tasks = [
        AgentTask("a", "Rozbor", "Analyzuj požadavek"),
        AgentTask("b", "Návrh", "Navrhni řešení"),
        AgentTask("c", "Kontrola", "Zkontroluj výsledek"),
    ]
    captured = {}

    async def synthesize(context, results):
        captured["context"] = context
        captured["results"] = results
        return "sjednocený výsledek"

    answer = await run_agent_team(
        tasks=tasks,
        providers=[first, second],
        shared_context="Jedna identita a společná paměť.",
        synthesizer=synthesize,
        max_parallel=2,
    )

    assert answer == "sjednocený výsledek"
    assert captured["context"] == "Jedna identita a společná paměť."
    assert [item.task_id for item in captured["results"]] == ["a", "b", "c"]
    assert [item.provider for item in captured["results"]] == ["local", "cloud", "local"]
    assert first.seen_context == ["Jedna identita a společná paměť.", "Jedna identita a společná paměť."]


@pytest.mark.asyncio
async def test_failed_agent_is_reported_to_synthesizer():
    provider = FakeProvider("offline", fail=True)
    captured = {}

    async def synthesize(context, results):
        captured["result"] = results[0]
        return "výsledek s upozorněním"

    answer = await run_agent_team(
        tasks=[AgentTask("a", "Úkol", "Proveď úkol")],
        providers=[provider],
        shared_context="kontext",
        synthesizer=synthesize,
    )

    assert answer == "výsledek s upozorněním"
    assert captured["result"].error == "provider offline"
    assert captured["result"].content == ""


@pytest.mark.asyncio
async def test_rejects_empty_tasks_or_provider_list():
    async def synthesize(context, results):
        return "unused"

    with pytest.raises(ValueError):
        await run_agent_team(tasks=[], providers=[FakeProvider("x")], shared_context="", synthesizer=synthesize)
    with pytest.raises(ValueError):
        await run_agent_team(tasks=[AgentTask("a", "x", "y")], providers=[], shared_context="", synthesizer=synthesize)
