# Product specification

Micro Helper is a personal AI agent platform, not a character app.

## Onboarding
Each user configures an independent agent: name, wake phrase, language, voice, communication style, memory preferences, optional mascot and device permissions. The mascot is optional visual presentation, never the agent's identity or intelligence.

## Memory and identity
Profiles, preferences, conversations and memories are isolated by account. Nothing is shared with another person by default. Users can inspect, correct, export and delete their memories.

## Free-first operation
Core local features must not require a paid API key or subscription. Local inference through a replaceable provider such as Ollama is preferred. Cloud inference, hosting and remote access are optional and may cost money.

## Permissions
Permissions are scoped by user, device, tool and operation. Reading is separate from writing, sending, sharing and deleting. Sensitive actions require confirmation. Every tool action is auditable and grants are revocable.

## Offline behavior
Local tasks work offline where the operating system permits. Online tasks enter a durable queue with unique IDs, retry policy and visible status. Never report queued work as completed.

## Platforms
Android is the primary interface. Windows is an optional compute and automation worker. Future integrations may include watches, tablets, headphones and smart-home devices.

## Paired agents
Pairing requires consent from both owners. Each owner controls narrowly scoped permissions. Messages are explicitly labeled as AI-agent-mediated.

## Mascots
Mascots are optional, selectable and replaceable. Springtrap is removed from the product and must not appear as a default identity or required feature.

## Cross-device synchronization (Android + Windows)

The same account must work in Android Chrome/PWA and Windows Edge/Chrome. Synchronize conversations, user-approved memories, profile preferences, and task metadata through an authenticated account-scoped API. Device-local secrets, provider API keys, local files, and Windows execution permissions must never sync as ordinary chat data.

### Sync behavior
- Assign stable UUIDs to conversations, messages, memories, and tasks; keep server timestamps and per-record revisions.
- Persist locally first, then enqueue sync operations with unique idempotency keys.
- Show explicit states: Local only, Syncing, Synced, Conflict, and Offline/Queued.
- Retry transient failures with bounded exponential backoff; never duplicate a message on retry.
- Resolve concurrent edits deterministically: append-only messages retain both entries; conflicting edits to the same memory/profile field show a conflict resolution UI rather than silently overwriting.
- Deletion uses account-scoped tombstones so deleted records do not reappear after another device reconnects.
- Provide manual sync/retry and last successful sync time.
- Encrypt transport with HTTPS. Do not claim end-to-end encryption unless client-side key management and encrypted payload storage are implemented and tested.
- A device must be explicitly signed out/revoked; revocation invalidates its refresh tokens.

## Czech voice interaction

Provide a persistent microphone/voice control in the chat composer and a user-configurable voice activation option.

### Button-initiated voice
- A clearly labeled microphone button starts a session after browser/device permission.
- Show listening, processing, speaking, muted, and error states.
- Allow the user to stop listening, cancel generation, and interrupt speech playback.
- Display the recognized Czech transcript before sending when confirmation mode is enabled; provide push-to-talk as the reliable fallback.
- Use Czech locale (cs-CZ) for speech recognition and speech synthesis where supported, with a voice selector and a text-only fallback.

### Voice activation
- A wake phrase may be offered only in an explicitly enabled local companion/native runtime that can legally and reliably keep a microphone session active.
- A normal browser tab/PWA must not promise always-listening wake-word behavior: browsers and mobile operating systems suspend background tabs and restrict microphone access.
- Require clear opt-in, visible microphone indicator, local wake-word processing where feasible, immediate mute/disable, and no audio retention by default.
- If wake-word support is unavailable, explain why and offer the microphone button or push-to-talk instead.

### Realtime limits
- Stream partial transcripts and audio only when the selected provider and client support it.
- Support barge-in by stopping current playback immediately when the user starts speaking.
- Expose provider/model, quota state, fallback mode, and errors. Never silently switch to a paid service.
- Do not claim parity with ChatGPT Voice or Gemini Live unless latency, interruption, turn-taking, and Czech speech quality have passed explicit device tests.

## Desktop and Windows companion

The web client must remain usable on a Windows PC without installing the companion. The companion is an optional, separately paired local executor for user-approved workspace operations. Pairing is per account and device, uses revocable scoped permissions, and does not expose one user's PC to other users.

## Release acceptance additions
- A message created offline on Android appears exactly once on Windows after reconnect, and vice versa.
- Concurrent profile/memory edits produce a visible conflict instead of silent data loss.
- Revoking a device prevents subsequent sync and companion commands from that device.
- Czech voice button works on supported Android and Windows browsers; stop/interruption controls work.
- Wake-word operation is tested only in the supported local companion runtime; the PWA clearly reports when background activation is unavailable.
