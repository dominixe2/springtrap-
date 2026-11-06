# Micro Helper 1.0 — unified product contract

**Status:** implementation contract; not a claim that every capability is already implemented.
**Product:** one Czech-first personal AI assistant with full-feature Android and Windows clients.

## Product promise

Micro Helper is its own product and identity. It may learn from the interaction patterns of conversational assistants, desktop agents and automation frameworks, but it must not copy their protected branding, UI assets, source code, prompts, or proprietary internals. The same account, personality, memory, settings, tool catalog and task history must be available on Android and Windows. Platform-specific adapters may expose different hardware capabilities, but neither client is intentionally a reduced edition.

## Requirements carried forward from the user's conversations

- Keep and evolve the existing `dominixe2/springtrap-` project; do not restart from an unrelated template.
- Unify the intended Micro Helper + JARVIS + Hermes workflows into one product and one coherent identity. Reuse proven open-source components where useful; do not require Goose or Hermes as a permanent runtime dependency.
- Czech-first chat and natural voice, conversation history, user-controlled long-term memory, editable preferences, a distinct personality, and an original animated avatar.
- Full-feature Android and Windows clients: chat, voice, avatar, memory, tools, settings, task timeline, automation and device integrations on both. Windows additionally exposes approved desktop capabilities; Android additionally exposes Android platform capabilities.
- Tool capabilities: web research with sources, file and image understanding, image generation when a provider is available, writing, coding, data analysis, planning, task execution, extensible plugins/MCP adapters, and scheduled workflows.
- Adaptive personalization may recommend or remember confirmed preferences. It must never infer or silently expand permissions from habits.
- Default-deny security. Reading is distinct from creating, editing, sending, sharing, purchasing, publishing and deleting. Financial, destructive, identity, credential, private-data export and external-send actions require fresh explicit confirmation. Cookie handling may only reject optional cookies when the user has configured that narrow rule; never auto-accept all.
- One-time device pairing, authenticated and encrypted sync, revocable device keys, conflict handling, export/restore, and an auditable task timeline.
- Smartwatch and smart-home support through optional, permission-scoped adapters. Never claim support until an adapter is implemented and tested.
- Free-first operation. Core shell, local data and local tools must not require a paid API key. Optional model providers must be clearly labeled; no provider, free quota, cloud hosting or unlimited intelligence is guaranteed. A capable local model requires compatible hardware and storage.
- No false claims of continuous background listening, offline AI, successful actions, device tests, deployment or completion.

## Architecture

1. **Shared product core:** versioned capability catalog, task state machine, policy gate, provider router, prompt/context assembly, audit events and health/status reporting.
2. **Clients:** shared responsive UI and design system; Android package and Windows desktop package. Keep the feature matrix in sync and run parity checks.
3. **Agent runtime:** provider-neutral model adapter; optional local inference; optional user-enabled cloud providers; bounded planner/worker; explicit tool schemas. Model output proposes actions but never authorizes them.
4. **Memory:** account/device-scoped profile, conversations, user-approved memories and preferences; inspect/edit/export/delete; no secrets or sensitive inferred traits.
5. **Tools:** isolated adapters with capability scopes, input validation, timeouts, cancellation and visible results. Web content, files and model output are untrusted data.
6. **Device bridge:** independently authenticated Android/Windows agents; allowlisted actions; least privilege; no arbitrary shell by default.
7. **Sync:** explicit pairing, encrypted transport and storage, revocation, conflict resolution and backup.
8. **Avatar and voice:** original replaceable avatar; speech input/output adapters; streaming and interruption support only where implemented; foreground/background restrictions shown honestly.
9. **Automation:** durable jobs with queued/running/needs-approval/succeeded/failed/cancelled states, schedule, pause, cancel, retries and reports.

## Delivery order

- **A — Release foundation:** fix the known hosted deployment/source mismatch; make CI green; secure every API route; define one canonical source and environment configuration.
- **B — Unified identity:** original avatar, personality/profile editor, persistent conversations, memory and preference controls.
- **C — Agent core:** provider adapters, context assembly, planner, tool registry, policy enforcement, task queue, cancellation and audit trail.
- **D — Useful tools:** web search with citations, files/images, writing/code/data tools, image generation adapter, calendar and notifications.
- **E — Voice:** Czech input/output, streaming conversation, interruption, foreground controls; wake word/background operation only with platform permission and battery/privacy tests.
- **F — Android + Windows parity:** release APK and Windows installer, paired device workers, authenticated remote tasks and encrypted sync.
- **G — Extensions:** smartwatch, smart home, third-party plugins/MCP, user automations and optional multi-agent orchestration.
- **H — Release:** clean install, migration/restore, accessibility, security review, dependency/license review, CI, device smoke tests, signed release artifacts and rollback plan.

## Definition of done

A capability counts as complete only when its implementation exists, its permission boundary is tested, errors and cancellation are handled, the UI exposes its state, CI passes, and required platform smoke tests pass. A source mirror passing static CI is not proof of live deployment. A debug APK is not a production Play Store release. Android and Windows feature parity is measured from the same capability matrix, not assumed.

## Current known baseline (verified from repository sources on 2026-11-06)

- The `micro-helper` branch already contains a hosted AppDeploy source mirror with authenticated account state, chat/history, memories/preferences, learning plans, tasks/reports, browser voice, web search and image-related handlers. On 2026-11-06 AppDeploy reported the live deployment as ready, valid and free of frontend/network errors in its latest QA snapshot; the public page returned HTTP 200. Historical syntax-error logs remain, and signed-in end-to-end workflows still need testing. The deployed snapshot and GitHub source mirror must be compared before claiming source parity.
- The root Python/FastAPI edition is separate and supports local SQLite plus an optional Ollama adapter. It is not the backend serving the hosted URL.
- The Android wrapper is a debug-signed WebView package loading the hosted origin; it requires internet for hosted AI/sync and is not a native offline AI release.
- The Windows Companion is a separately paired loopback bridge with a small fixed allowlist (lock, Explorer, Notepad, Calculator), not a full desktop agent.
- The local Python branch documents a small capability registry and browser voice, but not full-duplex voice, background wake word, general tool execution, encrypted sync or a finished desktop worker.
- The current PR #15 feature branch now includes the deterministic trust-policy module and unit tests from PR #14. The policy is not yet wired into every hosted/desktop action adapter. PR #11 remains a separate draft orchestration foundation and PR #13 remains a separate security-hardening PR; neither is represented as fully integrated.
- Earlier checks found test dependencies absent in one environment; never report tests as passed unless a current run proves it.

## Progress reporting

Report verified counts only: implemented capabilities, passing/failing/not-run tests, open blockers, latest commit/PR, and deployment/device validation. Do not invent a single completion percentage from unweighted features. If a percentage is shown, publish the weighted capability list and formula alongside it.
