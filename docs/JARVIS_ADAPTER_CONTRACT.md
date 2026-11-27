# Micro Helper–JARVIS adapter contract (draft)

**Snapshot:** 2026-11-27  
**Status:** Architecture boundary only; no adapter implementation or release credit.

## Why this contract exists

Micro Helper and JARVIS remain separate projects. BuildPilot is an optional local coding worker in JARVIS, not a general remote computer-control API. Micro Helper must not copy JARVIS UI, assets, prompts, or broad control surface, and it must not treat a JARVIS task as an ordinary chat response.

## Verified JARVIS work under review

- [JARVIS PR #13](https://github.com/dominixe2/jarvis/pull/13) — local resumable BuildPilot worker/API foundation; draft, head `2bad1ff4659aa41c3d1a434cdc6572a46d48fca4`.
- [JARVIS PR #14](https://github.com/dominixe2/jarvis/pull/14) — workspace, tool and queue hardening; draft, head `91cef35e91cf4c043648790aa17a6f2feb561482`.
- [JARVIS PR #15](https://github.com/dominixe2/jarvis/pull/15) — exact loopback Origin-to-Host binding; draft, head `f5c5f5239240338b7ea5106a66d0465ed1c4248d`.

All three remain unmerged. The current JARVIS main branch is older than this work, and no CI/status checks are attached to these three heads. This contract therefore does not assume their APIs or security controls are already shipped.

## Proposed adapter boundary

The adapter must run only in a local Micro Helper companion/backend, not in the browser/PWA or a hosted multi-user service.

| Operation | Default | Required gate |
|---|---|---|
| Read worker/job status | Disabled until reviewed | Loopback endpoint, authenticated local session, exact Host/Origin checks |
| List workspaces | Disabled until reviewed | Explicit local workspace allowlist; never infer from path text |
| Submit a task | Deny | Fresh operation-bound user approval, bounded input and a selected workspace |
| Approve a completed job | Deny | Human review in the local UI; never delegated to the model |
| Cancel a job | Deny | Fresh explicit approval and an authenticated request |
| Merge, deploy, publish, delete or run arbitrary commands | Prohibited | Not exposed through this adapter |

The future adapter interface should expose only typed operations, such as `status()`, `listJobs()`, `getJob(id)`, `submitTask(workspaceId, task, approval)` and `cancelJob(id, approval)`. The names are illustrative; no client or endpoint code is implemented yet.

## Security requirements

1. **Loopback only:** connect to a configured exact loopback endpoint. Do not expose BuildPilot through LAN, public hosting, browser CORS or cloud relay.
2. **Secret boundary:** keep the BuildPilot token in a local companion/server environment. Never place it in browser storage, PWA cache, conversation history, telemetry, source files or logs.
3. **Transport and origin:** retain bearer authentication, Fetch Metadata, Host and Origin checks. Require the exact Origin/Host binding before considering the API usable. PR #15 is still draft.
4. **Workspace:** accept only an explicit workspace identifier resolved by the local server. Never allow absolute paths, traversal, symlinks, credential paths or cross-workspace reads.
5. **Command execution:** no arbitrary shell capability. Keep the default read-only command policy; treat enabling repository scripts or additional commands as code execution requiring explicit review.
6. **Fresh consent:** model output, learned habits, prior approvals or task completion markers cannot grant permissions. Consent must be bound to the exact operation, target and parameters, and expire after use.
7. **Human review:** BuildPilot completion means `needs_review`, not approved. Merge, release, deploy, publishing and destructive cleanup remain outside the adapter.
8. **Failure behavior:** report unavailable, rejected, expired, failed and successful results distinctly. Never claim an operation succeeded when the API did not confirm it.
9. **Revocation:** do not persist a long-lived adapter grant. A future integration must expose a local disconnect/revoke action and clear its token/session state.

## Acceptance tests before implementation is enabled

- Reject a missing, invalid or expired local bearer token.
- Reject non-loopback hosts and cross-origin requests, including mismatched loopback aliases.
- Reject workspace traversal, symlinks, credential-file paths and workspace IDs not in the configured allowlist.
- Reject task submission without a fresh, server-validated approval bound to the exact task and workspace.
- Reject approval calls from the AI/worker itself; approval remains a human action.
- Verify default shell restrictions and no arbitrary Bash, recursive secret-reading or credential access.
- Verify completion changes to `needs_review` and cannot become completed without human approval.
- Verify tokens and private task data are absent from browser storage, cache, logs and public job responses.
- Verify disconnect/revoke prevents subsequent adapter calls.
- Exercise failure and timeout paths without retrying sensitive operations automatically.

## Release decision

The adapter is **not implemented** and must not be enabled. PR #13/#14/#15 need independent review, CI, and local-device validation. This document is a guardrail for a future small integration; it adds no Micro Helper 1.0 acceptance points.
