# Micro Helper 1.0 acceptance checklist

- **Checklist version:** 1.0.0-checklist.12
- **Snapshot date:** 2026-11-09
- **Snapshot source:** Stacked PR #34 trust-gateway + full backup/restore head `3d517d92a5fa3ee885baaa4be6ce89e7ff990f7b` passed CI run #42679331114: 86 project tests, 11 relay tests, embedded browser JavaScript syntax and Python compilation. PR #34 is based on PR #32 → PR #31 → PR #23 and remains unmerged. PR #25 remains a separate backup/restore implementation reference. Separate PR #33 (`security/render-relay-session-guards`) adds protections to the active Render relay source and passed Micro Helper run #42636316961 plus Cloudflare Relay Checks run #42636316955. Merged PRs #18 and #19 provide additional verified Cloudflare-session and local-origin protections.
- **Purpose:** evidence-based release tracking; this file is not a claim that Micro Helper 1.0 is ready.
- **Scoring rule:** `earned points = weight × evidence level`; `completion = sum(earned points) / sum(weights) × 100`.
- **Weights:** total 100 points.
- **No criterion is marked complete.** Source presence or a passing static test alone is not release acceptance.

## Evidence levels

| Level | Meaning |
|---:|---|
| 0.00 | Missing, blocked, or no usable evidence. |
| 0.25 | Partial scaffold or isolated capability; no proven end-to-end integration. |
| 0.50 | Implementation exists and has some automated validation, but integration or target-platform verification is incomplete. |
| 0.75 | Integrated implementation, automated regression coverage, and a successful end-to-end check on at least one target platform. |
| 1.00 | All acceptance tests pass on every supported target platform, with security review and release artifacts verified. |

A level may be raised only when new implementation and evidence are linked in this checklist. Planned work and mock UI do not earn points.

## Weighted criteria

| ID | Acceptance criterion | Weight | State | Evidence level | Earned | Evidence and remaining gap |
|---|---|---:|---|---:|---:|---|
| MH-01 | Responsive, installable web/PWA UX on phone and desktop, with truthful loading/error states | 12 | Partial | 0.50 | 6.00 | `hosted-app/index.html`, `hosted-app/src/main.ts`, `hosted-app/public/manifest.webmanifest`; live page and latest AppDeploy QA were reported healthy on 2026-11-06. Signed-in end-to-end coverage and source-to-deployment parity are not proven by this PR. |
| MH-02 | One identity, persistent chat history, user-controlled memory/preferences, export/import/delete | 12 | Partial | 0.50 | 6.00 | Local API and tests in `src/micro_helper/api.py`, `tests/`; hosted account-backed state is documented in `docs/SECURITY.md`. PR #34 ports full local backup/restore for profile, memories, messages, tasks, learning plans and preferences onto the trust-gateway stack. Restore is a destructive policy action, and the one-time confirmation is bound to the SHA-256 digest of the exact raw request bytes without storing backup contents. The 8 MiB streamed-body cap, payload validation and atomic SQLite rollback are covered by tests. PR #34 CI passed 86 project tests and 11 relay tests. The UI exports compact JSON so the downloaded file stays within the same 8 MiB restore limit. The stack is still unmerged and physical Android acceptance is missing. PR #25 remains a separate implementation reference. Cross-client persistence/sync and full user workflow tests remain unverified. |
| MH-03 | Modular AI provider adapters, optional local inference, visible limits and tested no-charge fallback | 10 | Partial | 0.50 | 5.00 | Local Ollama path is documented in the Python edition and JARVIS PR #5. A unified provider router and tested quota-to-provider-to-local-to-offline fallback are not yet proven. |
| MH-04 | Czech speech input/output, permission/error state, cancellation and honest fallback | 8 | Partial | 0.50 | 4.00 | Browser speech controls are documented in the local UI and JARVIS README. Full-duplex streaming, interruption under real device conditions, and Android/Windows voice acceptance tests are not proven. |
| MH-05 | Capability-based tools, bounded tasks, cancellation, visible results, extensible adapters | 12 | Partial | 0.50 | 6.00 | `src/micro_helper/api.py` now exposes three fixed local tools through the policy gateway (`profile.read`, `memory.list`, `memory.create`) and a bounded `agent.draft` queue with cancellation and persisted success/failure results. `tests/test_api.py` covers the API and worker paths; PR #23 CI passed 61 project tests. Pluggable adapters and web/file/image execution under one runtime remain unintegrated. |
| MH-06 | Adaptive Trust Engine: explicit grants, deny precedence, fresh confirmation for high-impact actions, audit and revocation | 12 | Partial | 0.50 | 6.00 | `src/micro_helper/trust_policy.py`, `tests/test_trust_policy.py`, and the new local API gateway in `src/micro_helper/api.py`. The exact low-risk reads have fixed grants; `memory.create` requires a 60-second one-time token bound to normalized arguments; `/v1/audit` records metadata without payloads. API integration tests cover missing/forged boolean confirmation, argument mismatch, expiry, replay and audit privacy. PR #31 adds the shared policy gate for local REST writes; PR #34 extends it to destructive full-backup restore with exact-body binding. Hosted and Windows/JARVIS adapters and user-managed grant revocation remain unintegrated. |
| MH-07 | Authenticated phone/Windows pairing, encrypted sync, revocation, conflict handling and least privilege | 12 | Partial | 0.50 | 6.00 | Merged PR #18 adds Cloudflare Durable Object relay pairing/session protections in `cloudflare/worker.js`: hashed pairing/session tokens, one-time five-minute pairing claims, 12-hour sessions, revocation, fixed mobile action allowlist, per-IP pairing limits, per-session WebSocket limits (120/minute), 4 KiB message cap and expiry/revocation checks on every message. `cloudflare/worker.test.mjs` contains four regression tests; PR #18 CI #42376109737 passed. PR #19 is merged and adds local API Host/Origin/Fetch-Metadata guards with `tests/test_origin_security.py`. No live Cloudflare deployment, physical phone/Windows pairing, app-data sync, conflict resolution or full encrypted-sync acceptance is verified. |
| MH-08 | Android package/install path, backup/restore and core workflows verified on a physical Android device | 8 | Partial | 0.50 | 4.00 | Android debug APK workflow and backup/restore tests exist. A debug wrapper is not a store release; no physical-device acceptance test is recorded. |
| MH-09 | Windows companion with explicit approval, workspace scope, action log and tested restrictions | 8 | Partial | 0.50 | 4.00 | `windows-companion/tests/test_companion_security.py` and `docs/SECURITY.md` document a fixed allowlist (lock, Explorer, Notepad, Calculator). A general workspace-scoped coding agent and physical Windows acceptance test are not proven. |
| MH-10 | Release security, dependency/config review, clean CI, deployment parity and rollback evidence | 6 | Partial | 0.50 | 3.00 | **PASS:** PR #23 trust-gateway head `e6714c7b94728e6419d66f25dea4c69440a86ff2`, GitHub Actions run #42512554196: 61 project tests and 11 relay tests passed, with embedded JavaScript syntax and Python compilation checks. The workflow uses actions/checkout@v7, setup-python@v7 and setup-node@v7, contents:read permissions and a 15-minute job timeout. **PASS (separate branch):** PR #25 backup/restore head `cf3cce1baa49c9c22f165312ba21aef23e1b27a6`, run #42512220640: 68 project tests and 11 relay tests passed, with embedded JavaScript syntax and Python compilation checks. The two runs validate separate PR heads, not a combined tree. One Starlette/httpx deprecation warning was emitted in each pytest suite. Hosted and Windows/JARVIS adapter coverage, physical-device tests, security review and release checks remain incomplete. |
|  | **Total** | **100** | **Not release-ready** |  | **50.00** | **Evidence-weighted score: 50.00%.** This measures verified acceptance evidence, not a claim that 50% of all possible features exist. |

## Current test evidence

- **PASS:** PR #23 trust-gateway/checklist head `ccf1036b137a4b24947f50accc9042ab86fabb24`, GitHub Actions run [#42512645801](https://github.com/dominixe2/springtrap-/actions/runs/42512645801): 61 project tests and 11 relay tests passed; embedded JavaScript syntax and Python compilation passed. The workflow uses v7 actions, read-only repository permissions and a 15-minute job timeout.
- **PASS (merged relay guards):** PR #18 Cloudflare Relay Checks [#42376109737](https://github.com/dominixe2/springtrap-/actions/runs/42376109737), including JavaScript syntax, four Durable Object WebSocket guard tests and Wrangler dry-run.
- **PASS (merged local API guards):** PR #19 Micro Helper checks [#42385818037](https://github.com/dominixe2/springtrap-/actions/runs/42385818037), including project/relay tests, embedded JavaScript syntax and Python compilation.
- **PASS (separate branch):** PR #25 backup/restore head `cf3cce1baa49c9c22f165312ba21aef23e1b27a6`, run [#42512220640](https://github.com/dominixe2/springtrap-/actions/runs/42512220640): 68 project tests and 11 relay tests passed. The two runs validate separate PR heads, not a combined tree.
- **WARNING:** The two pytest suites each emitted one Starlette/httpx TestClient deprecation warning. No test failures occurred.
- **PASS (historical baseline):** PR #15 head `24a5be5fb8b636818cec8b5245107df48d98e1cd`, checks run [#270](https://github.com/dominixe2/springtrap-/actions/runs/42267396572) and hosted-source run [#19](https://github.com/dominixe2/springtrap-/actions/runs/42267396582).
- **NOT RUN:** Physical Android install/use, physical Windows use, signed-in end-to-end flows for hosted chat/sync/tasks/images/web search/voice, and full trust-policy integration across every action adapter.
- **NOT RUN:** Production signing, store release, security penetration review, and verified rollback drill.

## Known release blockers (not a bug count)

1. The trust policy is not yet enforced through every hosted and desktop tool/action path.
2. JARVIS PR #5's LAN Ollama relay still needs authenticated pairing, request/concurrency limits and regression tests before it is safe for broader LAN use. Keep it chat-only and do not port-forward it.
3. The active `micro-helper` base includes the loopback/Origin/Fetch-Metadata protections from merged PR #19. PR #13 remains open against the older `main` API and should not be confused with the active product-branch fix. These checks are defense in depth, not authentication; the local API must remain loopback-only and they do not secure hosted routes or the JARVIS relay.
4. Android/Windows physical-device acceptance tests are not recorded.
5. The hosted source mirror and AppDeploy live snapshot need explicit parity evidence before a source change can be called deployed.
6. Cross-device encrypted sync, conflict handling and device-session revocation are not yet proven end to end.
7. PR #23 → #31 → #32 → #34 now form a passing stacked trust-gateway/backup-restore branch, but remain unmerged. Compare PR #34 against PR #25, then integrate the stack sequentially and run CI on the resulting `micro-helper` branch.
8. The active Windows Companion endpoint is Render, while the Cloudflare Durable Object relay is a separate replacement. PR #33 hardens the Render source but remains unmerged and undeployed. The Cloudflare Worker is also not deployed; no live WSS pairing or real phone-to-Windows action has been verified, and clients must not be switched between endpoints before a successful staging health check.

## Next development order

1. Review the passing PR #23 → #31 → #32 → #34 stack against PR #25, then integrate the trust gateway and policy-gated backup/restore sequentially into `micro-helper`; run a fresh full suite on the integrated branch.
2. Review PR #33's active Render relay hardening, integrate it separately, then run a staging pairing test before any live endpoint change.
3. Extend the policy gate to the first hosted action adapter only after its authenticated identity, explicit approval UI and audit boundary are covered by integration tests.
4. Secure JARVIS's chat-only Ollama relay with per-launch pairing/authentication, bounded concurrent requests and rate limits.
5. Add a single capability matrix shared by hosted tools, local Python, Android and Windows Companion.
6. Run signed-in hosted end-to-end tests, then physical Android and Windows smoke tests.
7. Recalculate this checklist only after updating the evidence links and levels.

## Change log

- **1.0.0-checklist.12 (2026-11-09):** adds the separate PR #33 hardening of the active Render relay source and its passing Micro Helper/relay CI runs #42636316961 and #42636316955. No live relay deployment or physical pairing credit is added; the evidence-weighted score remains 50.00%.

- **1.0.0-checklist.11 (2026-11-09):** records PR #34's policy-gated full backup/restore port on top of PR #23/#31/#32, the compact export-size correction, and passing CI run #42679331114 (86 project tests, 11 relay tests, embedded JavaScript syntax and Python compilation). The score remains 50.00% because the stack is still unmerged and physical Android/Windows acceptance, hosted/desktop adapter coverage and release verification remain incomplete.

- **1.0.0-checklist.10 (2026-11-08):** raises MH-07 from evidence level 0.25 to 0.50 after verifying merged PR #18's authenticated pairing/session guard code and four regression tests, plus merged PR #19's local API origin/Host protection. Weighted score rises from 47.00% to 50.00%. This does not count live Cloudflare deployment, physical-device tests, app-data sync or conflict resolution.

- **1.0.0-checklist.9 (2026-11-08):** records the hardened PR #23 CI workflow (v7 actions, contents:read and timeout) and passing run #42512554196 on head `e6714c7`. PR #25 remains a separate passing backup/restore branch; score remains 47.00% until both changes are integrated and target-device acceptance is recorded.

- **1.0.0-checklist.8 (2026-11-08):** records the separate PR #25 full backup/restore implementation, database-failure rollback and default-identity regression tests, and passing CI run #42512220640 (68 project tests, 11 relay tests). PR #23 remains a separate trust-gateway branch; score remains 47.00% because no combined PR #23 + PR #25 tree or physical-device acceptance has been verified.

- **1.0.0-checklist.7 (2026-11-07):** updates the checklist snapshot to PR #23 head `c391f77e20e08eecc5c0949eaeeb21a4980d25b2` and records its passing CI run #42400871649. Score remains 47.00%.

- **1.0.0-checklist.6 (2026-11-07):** records passing CI on checklist head `67fdc8f93b55c5e3783ad6f7831e72b04c08b042` (run #42400792683) and keeps the weighted score at 47.00%.

- **1.0.0-checklist.5 (2026-11-07):** raises MH-05 from evidence level 0.25 to 0.50 because the bounded task queue and three policy-gated local tools are now implemented and covered by passing CI. Weighted score increases from 44.00% to 47.00%; no physical-platform credit is added.

- **1.0.0-checklist.4 (2026-11-07):** corrects the snapshot source to the PR #23 implementation head and separates current PR #23 CI evidence from the historical PR #15 baseline. Score remained 44.00%.

- **1.0.0-checklist.3 (2026-11-07):** recorded the first policy-enforced local API tool gateway, argument-bound one-time confirmations, payload-free audit events, and passing implementation CI run #42400456289. Score remained 44.00%.

- **1.0.0-checklist.2 (2026-11-07):** records the first local API tool-gateway integration, one-time argument-bound confirmations and payload-free audit log. Evidence-weighted score remains 44.00% pending current branch CI and target-platform acceptance.

- **1.0.0-checklist.1 (2026-11-06):** established weighted baseline from repository source, PR #15 head and recorded CI results; added high-impact trust-policy confirmation coverage. No platform/device tests are claimed.
