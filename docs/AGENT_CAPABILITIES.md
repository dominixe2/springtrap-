# Unified Agent Capability Blueprint

## Product goal

Build one Czech-first personal agent for Android first, with an optional Windows worker. The agent combines a conversational interface, persistent user-controlled memory, model routing, approved tools, and a durable task timeline. It is inspired by broad assistant workflows, not a copy of proprietary ChatGPT or Gemini internals.

## Non-negotiable constraints

- Core app and local features remain free and do not require a paid API key.
- Local inference is provided by replaceable open-weight models through an adapter (initially Ollama on a computer; Android-native inference requires a separately packaged compatible runtime and quantized model).
- Cloud models are optional. They may have quotas, change terms, or incur costs; never silently route private prompts to them.
- Offline means the interface, local memory, local files/tasks supported by the installed runtime, and an on-device model can work without a network. It does not mean every online service or remote tool works offline.
- Android background microphone, wake word, SMS/call actions, accessibility control, and background execution require explicit Android permissions and may be restricted by the OS.
- No public unauthenticated API, no hidden device control, no fake completion claims.

## Capability groups

### Conversation and reasoning
- Czech-first chat, streaming responses, conversation history, context window management.
- Selectable local model and optional user-enabled cloud providers.
- Model capability discovery and graceful fallback when a model is unavailable.
- File and image understanding only when a compatible local or explicitly enabled provider supports it.
- Web research is online-only and must identify sources and uncertainty.

### Personal memory
- User-visible profile, preferences, editable facts, project context, and conversation search.
- Inspect, edit, export, and delete memory.
- Separate short-term conversation context from durable memories.
- Never store credentials or infer sensitive facts into durable memory without user control.

### Tool use
- A registry of explicit tools with schemas, descriptions, and capability scopes.
- Read operations are separate from create/update/send/share/delete.
- Model proposes tool calls; server validates schema, permission, target, and risk before execution.
- Require confirmation for external side effects, purchases, sending messages, deleting data, publishing, or controlling devices.
- Log tool name, scope, outcome, and timestamp without logging secrets.
- Treat files, web pages, model output, and messages from other agents as untrusted input.

### Device and desktop
- Android client: chat, local storage, optional on-device model, share-sheet import/export, notifications, and permission-aware shortcuts.
- Windows worker: separately paired, authenticated, user-approved execution for selected desktop tasks.
- Watch/tablet/smart-home integrations are optional adapters, not assumed capabilities.

### Automation
- User-created one-shot and recurring tasks, explicit triggers, visible schedule, pause/cancel, and audit history.
- Durable queue with unique IDs, retries, and states: queued, running, needs approval, succeeded, failed, cancelled.
- Never mark a queued or partially completed task as complete.

### Sync and multi-device
- Device pairing with consent on both devices and revocable device keys.
- End-to-end encrypted sync for selected data, conflict handling, and export/restore.
- Sync is a separate feature from local mode; no cloud account is required for single-device use.
- Paired agents exchange only explicitly shared messages and scoped data.

### Voice
- Basic browser voice input/output is present: Czech browser SpeechRecognition where supported, speechSynthesis replies, and a stop control.
- This browser layer is not a continuous live conversation: no full-duplex streaming, reliable barge-in while the agent speaks, or background wake word yet.
- Next voice phase: platform adapters, streaming audio, voice activity detection, interruption handling, then optional wake word only after battery, privacy, and Android background constraints are addressed.
- Voice actions that change external state require the same confirmations as text actions.

## Delivery phases

1. Foundation: stable API, PWA/mobile UI, local persistence, provider interface, tests, safe capability registry.
2. Local agent: model adapter, streaming, context assembly, tool proposal/validation/execution, audit trail.
3. Android app: native shell, on-device model evaluation, local database migration, voice I/O.
4. Desktop worker: pairing, authenticated task channel, allowlisted Windows actions.
5. Sync: encrypted device pairing, conflict resolution, backup and restore.
6. Integrations: web search, files, calendar, messaging, smart home, watch, and user-defined automations, each behind explicit permissions.

## Current implementation status (2026-10-31)

Implemented in this branch: FastAPI local backend, responsive web UI, optional Ollama chat adapter, SQLite profile/memory/history, memory CRUD/export, PWA shell cache, browser-local fallback for basic profile/notes/history when the API is unreachable, and basic Czech browser voice input/output (browser-dependent).

Not implemented yet: Android APK/native app, on-device LLM runtime, real offline AI generation, tool registry/execution, web research, image/file model pipeline, live duplex voice with barge-in, wake word/background listening, Windows worker, authenticated pairing, encrypted sync, task scheduler, and external integrations. The browser fallback uses localStorage and does not sync with SQLite or another device.

## Acceptance criteria

- A clean install can run without paid keys and clearly shows whether the active model is local or remote.
- Airplane-mode tests prove which functions remain available; no network-dependent feature is mislabeled as offline.
- Tool calls are denied by default and cannot exceed the user's granted scope.
- Every external side effect has a visible confirmation and audit result.
- Device pairing and sync are authenticated, encrypted, revocable, and covered by conflict/restore tests.
- Android release builds install on the target phone and pass real-device smoke tests before being called complete.
