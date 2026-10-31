# Architecture

## Components
- Local API and agent runtime: orchestration, task lifecycle and policy checks.
- Client: Android-first chat, onboarding, voice controls and activity timeline.
- Memory: account-scoped local persistence with inspection and deletion controls.
- Tool registry: capability-based adapters for files, apps, calendar and device actions.
- Model adapters: replaceable local or remote LLM backends. Model output never grants permissions.
- Task queue: durable offline jobs with IDs, retries and state transitions.
- Windows worker: separately authenticated executor for explicitly delegated desktop tasks.
- Sync/relay: optional encrypted transport for multi-device sync and paired-agent messages.

## Security
Default deny. Authorize every tool call server-side. Separate read/create/update/send/share/delete capabilities. High-impact actions require short-lived confirmation bound to one operation. Keep an audit trail without leaking credentials. Treat model output, web pages, files and paired-agent messages as untrusted input. Revoke grants immediately.

## Local-first deployment
Development starts on localhost and uses local persistence. Remote sync is optional. Local mode must remain useful without cloud services.

## Android constraints
Background microphone, wake-word detection, SMS, calls and accessibility actions are subject to Android permissions and platform restrictions. A web app cannot promise always-on wake-word behavior.