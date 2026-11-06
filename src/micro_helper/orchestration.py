"""Multi-agent orchestration primitives for Micro Helper.

Providers are adapters, not separate assistants: every agent receives the same
assistant identity and shared context. This module deliberately performs no
provider discovery, plugin installation, or external side effects by itself.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable, Protocol, Sequence


@dataclass(frozen=True)
class AgentTask:
    """One independently executable part of a larger user request."""

    task_id: str
    title: str
    instructions: str
    expected_output: str = ""


@dataclass(frozen=True)
class AgentResult:
    task_id: str
    provider: str
    content: str
    error: str | None = None


class AgentProvider(Protocol):
    """A model adapter that speaks as the one Micro Helper identity."""

    name: str

    async def complete(self, task: AgentTask, shared_context: str) -> str:
        ...


Synthesizer = Callable[[str, Sequence[AgentResult]], Awaitable[str]]


async def run_agent_team(
    *,
    tasks: Sequence[AgentTask],
    providers: Sequence[AgentProvider],
    shared_context: str,
    synthesizer: Synthesizer,
    max_parallel: int = 5,
) -> str:
    """Run as many task agents as the planner produced, then synthesize once.

    The number of agents is task-driven, not hard-coded to five. max_parallel
    only limits simultaneous network work to protect devices and provider
    quotas. Failed agents are retained in the synthesis input rather than
    silently discarded.
    """
    if not tasks:
        raise ValueError("At least one agent task is required.")
    if not providers:
        raise ValueError("At least one available provider is required.")
    if max_parallel < 1:
        raise ValueError("max_parallel must be positive.")

    semaphore = asyncio.Semaphore(max_parallel)

    async def execute(index: int, task: AgentTask) -> AgentResult:
        provider = providers[index % len(providers)]
        async with semaphore:
            try:
                content = await provider.complete(task, shared_context)
                if not isinstance(content, str) or not content.strip():
                    raise RuntimeError("Provider returned an empty result.")
                return AgentResult(task.task_id, provider.name, content.strip())
            except Exception as exc:
                return AgentResult(task.task_id, provider.name, "", str(exc)[:1000])

    results = await asyncio.gather(
        *(execute(index, task) for index, task in enumerate(tasks))
    )
    return await synthesizer(shared_context, results)
