# Micro Helper 1.0 acceptance checklist

- **Checklist version:** 1.0.0-checklist.5
- **Snapshot date:** 2026-11-07
- **Snapshot source:** PR #23 implementation head `3f5794837c60506761f9f76ebcd503dd849af701`; latest checklist evidence commit `e3fbaa5fb15850122bfd3b43998841d8a2de6cd7` passed CI run #42400687405.
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
| MH-02 | One identity, persistent chat history, user-controlled memory/preferences, export/import/delete | 12 | Partial | 0.50 | 6.00 | Local API and tests in `src/micro_helper/api.py`, `tests/`; hosted account-backed state is documented in `docs/SECURITY.md`. Cross-client persistence/sync and full user workflow tests remain unverified. |
| MH-03 | Modular AI provider adapters, optional local inference, visible limits and tested no-charge fallback | 10 | Partial | 0.50 | 5.00 | Local Ollama path is documented in the Python edition and JARVIS PR #5. A unified provider router and tested quota-to-provider-to-local-to-offline fallback are not yet proven. |
| MH-04 | Czech speech input/output, permission/error state, cancellation and honest fallback | 8 | Partial | 0.50 | 4.00 | Browser speech controls are documented in the local UI and JARVIS README. Full-duplex streaming, interruption under real device conditions, and Android/Windows voice acceptance tests are not proven. |
| MH-05 | Capability-based tools, bounded tasks, cancellation, visible results, extensible adapters | 12 | Partial | 0.50 | 6.00 | `src/micro_helper/api.py` now exposes three fixed local tools through the policy gateway (`profile.read`, `memory.list`, `memory.create`) and a bounded `agent.draft` queue with cancellation and persisted success/failure results. `tests/test_api.py` covers the API and worker paths; PR #23 CI passed 61 project tests. Pluggable adapters and web/file/image execution under one runtime remain unintegrated. |
| MH-06 | Adaptive Trust Engine: explicit grants, deny precedence, fresh confirmation for high-impact actions, audit and revocation | 12 | Partial | 0.50 | 6.00 | `src/micro_helper/trust_policy.py`, `tests/test_trust_policy.py`, and the new local API gateway in `src/micro_helper/api.py`. The exact low-risk reads have fixed grants; `memory.create` requires a 60-second one-time token bound to normalized arguments; `/v1/audit` records metadata without payloads. API integration tests cover missing/forged boolean confirmation, argument mismatch, expiry, replay and audit privacy. Hosted and Windows/JARVIS adapters and user-managed grant revocation remain unintegrated. |
| MH-07 | Authenticated phone/Windows pairing, encrypted sync, revocation, conflict handling and least privilege | 12 | Partial | 0.25 | 3.00 | `docs/SECURITY.md` documents a limited loopback Windows Companion with one-time pairing and session token. Full Android/Windows sync, encrypted transport/storage, conflict resolution, and device-level verification remain open. |
| MH-08 | Android package/install path, backup/restore and core workflows verified on a physical Android device | 8 | Partial | 0.50 | 4.00 | Android debug APK workflow and backup/restore tests exist. A debug wrapper is not a store release; no physical-device acceptance test is recorded. |
| MH-09 | Windows companion with explicit approval, workspace scope, action log and tested restrictions | 8 | Partial | 0.50 | 4.00 | `windows-companion/tests/test_companion_security.py` and `docs/SECURITY.md` document a fixed allowlist (lock, Explorer, Notepad, Calculator). A general workspace-scoped coding agent and physical Windows acceptance test are not proven. |
| MH-10 | Release security, dependency/config review, clean CI, deployment parity and rollback evidence | 6 | Partial | 0.50 | 3.00 | **PASS:** PR #23 implementation snapshot `3f5794837c60506761f9f76ebcd503dd849af701`, GitHub Actions run #42400456289. Project pytest: 61 passed; cloud-relay pytest: 11 passed; embedded browser JavaScript syntax and Python compilation passed. One Starlette/httpx deprecation warning was emitted in each pytest suite. Hosted and Windows/JARVIS adapter coverage, physical-device tests, security review and release checks remain incomplete. |
|  | **Total** | **100** | **Not release-ready** |  | **47.00** | **Evidence-weighted score: 47.00%.** This measures verified acceptance evidence, not a claim that 44% of all possible features exist. |

## Current test evidence

- **PASS:** PR #23 latest checklist head `e3fbaa5fb15850122bfd3b43998841d8a2de6cd7`, GitHub Actions run [#42400687405](https://github.com/dominixe2/springtrap-/actions/runs/42400687405). Embedded browser JavaScript syntax and Python compilation passed; project pytest reported **61 passed**; cloud-relay pytest reported **11 passed**.
- **WARNING:** The two pytest suites each emitted one Starlette/httpx TestClient deprecation warning. No test failures occurred.
- **PASS (historical baseline):** PR #15 head `24a5be5fb8b636818cec8b5245107df48d98e1cd`, checks run [#270](https://github.com/dominixe2/springtrap-/actions/runs/42267396572) and hosted-source run [#19](https://github.com/dominixe2/springtrap-/actions/runs/42267396582).
- **NOT RUN:** Physical Android install/use, physical Windows use, signed-in end-to-end flows for hosted chat/sync/tasks/images/web search/voice, and full trust-policy integration across every action adapter.
- **NOT RUN:** Production signing, store release, security penetration review, and verified rollback drill.

## Known release blockers (not a bug count)

1. The trust policy is not yet enforced through every hosted and desktop tool/action path.
2. JARVIS PR #5's LAN Ollama relay still needs authenticated pairing, request/concurrency limits and regression tests before it is safe for broader LAN use. Keep it chat-only and do not port-forward it.
3. The current `micro-helper` base contains loopback/Origin/Fetch-Metadata checks for the local Python API; PR #13 remains open as a related hardening change. These checks are defense in depth, not authentication, and do not secure hosted routes or the JARVIS relay.
4. Android/Windows physical-device acceptance tests are not recorded.
5. The hosted source mirror and AppDeploy live snapshot need explicit parity evidence before a source change can be called deployed.
6. Cross-device encrypted sync, conflict handling and device-session revocation are not yet proven end to end.

## Next development order

1. Extend the policy gate to the first hosted action adapter only after its authenticated identity, explicit approval UI and audit boundary are covered by integration tests.
2. Secure JARVIS's chat-only Ollama relay with per-launch pairing/authentication, bounded concurrent requests and rate limits.
3. Add a single capability matrix shared by hosted tools, local Python, Android and Windows Companion.
4. Run signed-in hosted end-to-end tests, then physical Android and Windows smoke tests.
5. Recalculate this checklist only after updating the evidence links and levels.

## Change log

- **1.0.0-checklist.5 (2026-11-07):** raises MH-05 from evidence level 0.25 to 0.50 because the bounded task queue and three policy-gated local tools are now implemented and covered by passing CI. Weighted score increases from 44.00% to 47.00%; no physical-platform credit is added.

- **1.0.0-checklist.4 (2026-11-07):** corrects the snapshot source to the PR #23 implementation head and separates current PR #23 CI evidence from the historical PR #15 baseline. Score remained 44.00%.

- **1.0.0-checklist.2 (2026-11-07):** records the first local API tool-gateway integration, one-time argument-bound confirmations and payload-free audit log. Evidence-weighted score remains 44.00% pending current branch CI and target-platform acceptance.

- **1.0.0-checklist.1 (2026-11-06):** established weighted baseline from repository source, PR #15 head and recorded CI results; added high-impact trust-policy confirmation coverage. No platform/device tests are claimed.
