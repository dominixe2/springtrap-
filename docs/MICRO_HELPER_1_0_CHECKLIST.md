# Micro Helper 1.0 acceptance checklist

- **Checklist version:** 1.0.0-checklist.1
- **Snapshot date:** 2026-11-06
- **Snapshot source:** PR #15 head `24a5be5fb8b636818cec8b5245107df48d98e1cd`
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
| MH-05 | Capability-based tools, bounded tasks, cancellation, visible results, extensible adapters | 12 | Partial | 0.25 | 3.00 | `docs/ARCHITECTURE.md` documents the current `agent.draft` task worker; PR #11 is an orchestration foundation. General tool execution, search/file/image tools under one runtime, and end-to-end task tests are not integrated. |
| MH-06 | Adaptive Trust Engine: explicit grants, deny precedence, fresh confirmation for high-impact actions, audit and revocation | 12 | Partial | 0.50 | 6.00 | `src/micro_helper/trust_policy.py` and `tests/test_trust_policy.py`; PR #15 head CI run #270 passed after high-impact confirmation tests were added. The policy is not yet wired into every hosted and desktop action adapter; end-to-end audit/revocation tests remain. |
| MH-07 | Authenticated phone/Windows pairing, encrypted sync, revocation, conflict handling and least privilege | 12 | Partial | 0.25 | 3.00 | `docs/SECURITY.md` documents a limited loopback Windows Companion with one-time pairing and session token. Full Android/Windows sync, encrypted transport/storage, conflict resolution, and device-level verification remain open. |
| MH-08 | Android package/install path, backup/restore and core workflows verified on a physical Android device | 8 | Partial | 0.50 | 4.00 | Android debug APK workflow and backup/restore tests exist. A debug wrapper is not a store release; no physical-device acceptance test is recorded. |
| MH-09 | Windows companion with explicit approval, workspace scope, action log and tested restrictions | 8 | Partial | 0.50 | 4.00 | `windows-companion/tests/test_companion_security.py` and `docs/SECURITY.md` document a fixed allowlist (lock, Explorer, Notepad, Calculator). A general workspace-scoped coding agent and physical Windows acceptance test are not proven. |
| MH-10 | Release security, dependency/config review, clean CI, deployment parity and rollback evidence | 6 | Partial | 0.50 | 3.00 | PR #15 head CI run #270 and hosted-source check run #17 passed. PR #13 security hardening remains separate, policy integration is incomplete, and signed-in end-to-end/platform/security release checks are not complete. |
|  | **Total** | **100** | **Not release-ready** |  | **44.00** | **Evidence-weighted score: 44.00%.** This measures verified acceptance evidence, not a claim that 44% of all possible features exist. |

## Current test evidence

- **PASS:** Micro Helper checks, PR #15 head `24a5be5fb8b636818cec8b5245107df48d98e1cd`, GitHub Actions run [#270](https://github.com/dominixe2/springtrap-/actions/runs/42267396572). Dependency install, embedded browser JavaScript syntax, Python compilation and pytest completed successfully.
- **PASS:** Hosted-source checks on the same head, GitHub Actions run [#19](https://github.com/dominixe2/springtrap-/actions/runs/42267396582).
- **PASS:** Isolated trust-policy suite copied from the exact branch files: 7 tests passed. This is supplementary; GitHub Actions is the repository-level result.
- **NOT RUN:** Physical Android install/use, physical Windows use, signed-in end-to-end flows for hosted chat/sync/tasks/images/web search/voice, and full trust-policy integration across every action adapter.
- **NOT RUN:** Production signing, store release, security penetration review, and verified rollback drill.

## Known release blockers (not a bug count)

1. The trust policy is not yet enforced through every hosted and desktop tool/action path.
2. JARVIS PR #5's LAN Ollama relay still needs authenticated pairing, request/concurrency limits and regression tests before it is safe for broader LAN use. Keep it chat-only and do not port-forward it.
3. PR #13 local API origin/host hardening is a separate open PR and is not equivalent to securing every hosted route or the JARVIS relay.
4. Android/Windows physical-device acceptance tests are not recorded.
5. The hosted source mirror and AppDeploy live snapshot need explicit parity evidence before a source change can be called deployed.
6. Cross-device encrypted sync, conflict handling and device-session revocation are not yet proven end to end.

## Next development order

1. Wire the trust-policy gate into the first real tool/action adapter and add request-to-policy integration tests.
2. Secure JARVIS's chat-only Ollama relay with per-launch pairing/authentication, bounded concurrent requests and rate limits.
3. Add a single capability matrix shared by hosted tools, local Python, Android and Windows Companion.
4. Run signed-in hosted end-to-end tests, then physical Android and Windows smoke tests.
5. Recalculate this checklist only after updating the evidence links and levels.

## Change log

- **1.0.0-checklist.1 (2026-11-06):** established weighted baseline from repository source, PR #15 head and recorded CI results; added high-impact trust-policy confirmation coverage. No platform/device tests are claimed.
