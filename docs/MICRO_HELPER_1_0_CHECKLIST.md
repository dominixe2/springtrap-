# Micro Helper 1.0 acceptance checklist

- **Checklist version:** 1.0.0-checklist.39
- **Snapshot date:** 2026-11-24
- **Snapshot source:** PR #63 offline private workspace head `f17641d0d3942aa2f8170e052b47d274ed6dfd72` passed run [#45459803377](https://github.com/dominixe2/springtrap-/actions/runs/45459803377): 49 Node tests, 123 Python project tests and 11 relay tests — **183 total, 0 failures**. Draft PR #64 auth-bootstrap hardening head `4da6369d5f1bb19c0189bed4b477f68941053a7f` passed run [#45461398382](https://github.com/dominixe2/springtrap-/actions/runs/45461398382): 50 Node tests, 123 Python project tests and 11 relay tests — **184 total, 0 failures**. Embedded JavaScript syntax and Python compilation passed; two non-blocking Starlette/httpx TestClient deprecation warnings remain. PR #64 is stacked on PR #63; all release PRs remain unmerged and the hosted PWA / physical-device acceptance gaps remain open.
- **Purpose:** evidence-based release tracking; this file is not a claim that Micro Helper 1.0 is ready.
- **Integration snapshot:** PR #37 is the consolidated superset candidate targeting the active `micro-helper` branch. It modifies 12 files and contains the trust/backup/export/worker stack, handler-level REST route enforcement, a negative regression that exercises the checker against an unprotected route, and the versioned release checklist. The consolidated head `a0db3ac3dcf347873b185b8b55ba53155068bd15` passed run #43285515333: install, embedded browser JavaScript, Python compilation, project tests and relay tests all completed successfully. Earlier route-checker runs #43283674964 and #43283893085 also passed. PR #36 remains open as the subset reference; neither PR is merged. PR #38 adds PR-triggered Android/Windows builds and workflow hardening; all five checks passed on head `171d8426d660a097fb37f2dfc8ea15a249bcf76e` (Micro Helper checks, hosted source checks, Cloudflare dry-run, Windows Companion build, Android debug APK build). Artifacts were produced: Windows Companion 9,976,699 bytes and Android debug APK 3,693,569 bytes. These are build artifacts, not physical-device acceptance.
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
| MH-02 | One identity, persistent chat history, user-controlled memory/preferences, export/import/delete | 12 | Partial | 0.50 | 6.00 | Local API and tests in `src/micro_helper/api.py`, `tests/`; hosted account-backed state is documented in `docs/SECURITY.md`. PR #34 ports full local backup/restore for profile, memories, messages, tasks, learning plans and preferences onto the trust-gateway stack. Restore is a destructive policy action, and the one-time confirmation is bound to the SHA-256 digest of the exact raw request bytes without storing backup contents. The 8 MiB streamed-body cap, payload validation and atomic SQLite rollback are covered by tests. PR #34 CI passed 86 project tests and 11 relay tests. The UI exports compact JSON so the downloaded file stays within the same 8 MiB restore limit. PR #35 warns before downloading unencrypted full-backup and memory JSON exports and applies `Cache-Control: no-store` plus `Pragma: no-cache` to private API responses. Its regression test also verifies both headers on the early chunked-body 413 response. The stack is still unmerged and physical Android acceptance is missing. PR #25 remains a separate implementation reference. Cross-client persistence/sync and full user workflow tests remain unverified. |
| MH-03 | Modular AI provider adapters, optional local inference, visible limits and tested no-charge fallback | 10 | Partial | 0.50 | 5.00 | Local Ollama path is documented in the Python edition and JARVIS PR #5. A unified provider router and tested quota-to-provider-to-local-to-offline fallback are not yet proven. |
| MH-04 | Czech speech input/output, permission/error state, cancellation and honest fallback | 8 | Partial | 0.50 | 4.00 | Browser speech controls are documented in the local UI and JARVIS README. Full-duplex streaming, interruption under real device conditions, and Android/Windows voice acceptance tests are not proven. |
| MH-05 | Capability-based tools, bounded tasks, cancellation, visible results, extensible adapters | 12 | Partial | 0.50 | 6.00 | `src/micro_helper/api.py` now exposes three fixed local tools through the policy gateway (`profile.read`, `memory.list`, `memory.create`) and a bounded `agent.draft` queue with cancellation and persisted success/failure results. `tests/test_api.py` covers the API and worker paths; PR #23 CI passed 61 project tests.  PR #36 fixes literal `\\n` separators in the worker's preference context and persists only safe error categories for connection, timeout, HTTP-status and unexpected failures; its regression coverage is included in the 94-test project run #43079790199. This remains a text-draft worker, not a full execution agent. Pluggable adapters and web/file/image execution under one runtime remain unintegrated. |
| MH-06 | Adaptive Trust Engine: explicit grants, deny precedence, fresh confirmation for high-impact actions, audit and revocation | 12 | Partial | 0.50 | 6.00 | `src/micro_helper/trust_policy.py`, `tests/test_trust_policy.py`, and the new local API gateway in `src/micro_helper/api.py`. The exact low-risk reads have fixed grants; `memory.create` requires a 60-second one-time token bound to normalized arguments; `/v1/audit` records metadata without payloads. API integration tests cover missing/forged boolean confirmation, argument mismatch, expiry, replay and audit privacy. PR #31 adds the shared policy gate for local REST writes; PR #34 extends it to destructive full-backup restore with exact-body binding. Hosted and Windows/JARVIS adapters and user-managed grant revocation remain unintegrated. |
| MH-07 | Authenticated phone/Windows pairing, encrypted sync, revocation, conflict handling and least privilege | 12 | Partial | 0.50 | 6.00 | Merged PR #18 adds Cloudflare Durable Object pairing/session protections in `cloudflare/worker.js`: hashed pairing/session tokens, one-time five-minute pairing claims, 12-hour sessions, revocation, fixed mobile action allowlist, per-IP pairing limits, per-session WebSocket limits (120/minute), 4 KiB message cap and expiry/revocation checks on every message. `cloudflare/worker.test.mjs` contains four regression tests; PR #18 CI #42376109737 passed. PR #19 is merged and adds local API Host/Origin/Fetch-Metadata guards with `tests/test_origin_security.py`. The active Windows Companion uses the separate Render relay; draft PR #33 hardens that source with per-IP registration/claim limits, per-message session revalidation, a bounded/expiring pending-command queue, duplicate-ID rejection, a 30/minute command limit and matched desktop results. PR #33 Micro Helper run #42636316961 and relay run #42636316955 passed, but the PR is unmerged and no live Render deployment or physical phone/Windows pairing is verified. App-data sync, conflict resolution and full encrypted-sync acceptance also remain unverified. |
| MH-08 | Android package/install path, backup/restore and core workflows verified on a physical Android device | 8 | Partial | 0.50 | 4.00 | PR #38 Android debug build run #43227608984 passed and produced artifact [micro-helper-android-debug-apk](https://github.com/dominixe2/springtrap-/actions/runs/43227608984) (3,693,569 bytes). Backup/restore tests exist. This is a debug artifact, not a store release; physical installation and core-flow acceptance remain NOT RUN. |
| MH-09 | Windows companion with explicit approval, workspace scope, action log and tested restrictions | 8 | Partial | 0.50 | 4.00 | `windows-companion/tests/test_companion_security.py` and `docs/SECURITY.md` document a fixed allowlist (lock, Explorer, Notepad, Calculator). PR #38 Windows Companion build run #43227608891 passed and produced artifact [micro-helper-windows-companion](https://github.com/dominixe2/springtrap-/actions/runs/43227608891) (9,976,699 bytes). A general workspace-scoped coding agent and physical Windows acceptance test are not proven. |
| MH-10 | Release security, dependency/config review, clean CI, deployment parity and rollback evidence | 6 | Partial | 0.50 | 3.00 | **PASS:** PR #23 trust-gateway head `e6714c7b94728e6419d66f25dea4c69440a86ff2`, GitHub Actions run #42512554196: 61 project tests and 11 relay tests passed, with embedded JavaScript syntax and Python compilation checks. The workflow uses actions/checkout@v7, setup-python@v7 and setup-node@v7, contents:read permissions and a 15-minute job timeout. **PASS (separate branch):** PR #25 backup/restore head `cf3cce1baa49c9c22f165312ba21aef23e1b27a6`, run #42512220640: 68 project tests and 11 relay tests passed, with embedded JavaScript syntax and Python compilation checks. The two runs validate separate PR heads, not a combined tree. One Starlette/httpx deprecation warning was emitted in each pytest suite. Hosted and Windows/JARVIS adapter coverage, physical-device tests, security review and release checks remain incomplete. PR #35 adds the latest passing security/UI CI run #42885578401 (91 project tests, 11 relay tests) but remains unmerged. |
|  | **Total** | **100** | **Not release-ready** |  | **50.00** | **Evidence-weighted score: 50.00%.** This measures verified acceptance evidence, not a claim that 50% of all possible features exist. |

## Current test evidence

- **PASS (PR #37 actual socket-peer loopback enforcement):** head `6870f3556694b1fc22c5de31b6161998a8e671bc`, GitHub Actions run [#43485502280](https://github.com/dominixe2/springtrap-/actions/runs/43485502280): 103 project tests and 11 relay tests passed; embedded browser JavaScript syntax and Python compilation passed. A simulated remote peer (`192.0.2.44`) spoofing `Host: localhost` is rejected with non-cacheable 403 responses. IPv4, IPv6 and IPv4-mapped IPv6 loopback peers are accepted; remote, mapped-remote and unresolved peers are rejected. One Starlette/httpx deprecation warning remains in each pytest suite.

- **PASS:** PR #23 trust-gateway/checklist head `ccf1036b137a4b24947f50accc9042ab86fabb24`, GitHub Actions run [#42512645801](https://github.com/dominixe2/springtrap-/actions/runs/42512645801): 61 project tests and 11 relay tests passed; embedded JavaScript syntax and Python compilation passed. The workflow uses v7 actions, read-only repository permissions and a 15-minute job timeout.
- **PASS (merged relay guards):** PR #18 Cloudflare Relay Checks [#42376109737](https://github.com/dominixe2/springtrap-/actions/runs/42376109737), including JavaScript syntax, four Durable Object WebSocket guard tests and Wrangler dry-run.
- **PASS (merged local API guards):** PR #19 Micro Helper checks [#42385818037](https://github.com/dominixe2/springtrap-/actions/runs/42385818037), including project/relay tests, embedded JavaScript syntax and Python compilation.
- **PASS (separate branch):** PR #25 backup/restore head `cf3cce1baa49c9c22f165312ba21aef23e1b27a6`, run [#42512220640](https://github.com/dominixe2/springtrap-/actions/runs/42512220640): 68 project tests and 11 relay tests passed. The two runs validate separate PR heads, not a combined tree.
- **PASS (PR #35 security/UI follow-up):** head `d90e2cb632070ddfca41cd222301045bd112997a`, run [#42885578401](https://github.com/dominixe2/springtrap-/actions/runs/42885578401): 91 project tests and 11 relay tests passed; embedded browser JavaScript syntax and Python compilation passed. The chunked oversized-restore regression now asserts both `Cache-Control: no-store` and `Pragma: no-cache`.
- **PASS (PR #36 worker hardening):** head `8e898fe493d7a901bb3c38e2f3da2df803973a01`, run [#43079790199](https://github.com/dominixe2/springtrap-/actions/runs/43079790199): 94 project tests and 11 relay tests passed; embedded browser JavaScript syntax and Python compilation passed. New cases cover safe persistence for timeout, HTTP 502 and unexpected worker exceptions without URL/credential fragments.
- **PASS (PR #37 route-checker regression):** head `1dd4fa72ac9ee252f961aba597fef94d24493e7a`, run [#43283674964](https://github.com/dominixe2/springtrap-/actions/runs/43283674964): the Python-checks job completed successfully; install, embedded browser JavaScript, Python compile, project tests and relay tests all passed. The regression now executes the checker against a synthetic unprotected route and asserts both the missing policy mapping and missing handler gate are reported. Test count was not extracted from the run log.
- **PASS (PR #38 platform build workflows):** on head `171d8426d660a097fb37f2dfc8ea15a249bcf76`, Micro Helper checks [#43227608986](https://github.com/dominixe2/springtrap-/actions/runs/43227608986), hosted-source checks [#43227609023](https://github.com/dominixe2/springtrap-/actions/runs/43227609023), Cloudflare dry-run [#43227609124](https://github.com/dominixe2/springtrap-/actions/runs/43227609124), Windows Companion build [#43227608891](https://github.com/dominixe2/springtrap-/actions/runs/43227608891), and Android debug APK build [#43227608984](https://github.com/dominixe2/springtrap-/actions/runs/43227608984) all completed successfully. Windows and Android debug artifacts were uploaded; no physical-device acceptance is implied.
- **WARNING:** The two pytest suites each emitted one Starlette/httpx TestClient deprecation warning. No test failures occurred.
- **PASS (historical baseline):** PR #15 head `24a5be5fb8b636818cec8b5245107df48d98e1cd`, checks run [#270](https://github.com/dominixe2/springtrap-/actions/runs/42267396572) and hosted-source run [#19](https://github.com/dominixe2/springtrap-/actions/runs/42267396582).
- **NOT RUN:** Physical Android install/use, physical Windows use, signed-in end-to-end flows for hosted chat/sync/tasks/images/web search/voice, and full trust-policy integration across every action adapter.
- **NOT RUN:** Production signing, store release, security penetration review, and verified rollback drill.

## Known release blockers (not a bug count)

1. The trust policy is not yet enforced through every hosted and desktop tool/action path.
2. JARVIS PR #5 remains the original unauthenticated LAN Ollama implementation and must not be merged. Draft PR #9 (`security/ollama-relay-auth-20261110`) adds per-launch pairing, an HttpOnly session, HTTPS-only phone token use, rate/concurrency limits, redacted upstream errors and a chat-only relay; it also carries the loopback-only Windows bridge restriction. Draft PR #12 is six commits ahead of #9 and applies loopback-by-default Vite networking, permitting LAN binding only when both HTTPS certificate and key paths are configured. PR #11 is a parallel copy of that Vite hardening stacked on PR #10, so avoid treating #11 and #12 as two independent features. **No GitHub Actions run was observed** for current heads #9 (`0ae636d`), #10 (`01202ec`), #11 (`e421bda`) or #12 (`b5ac575`); do not count their local-only test claims as CI evidence. PR #10 adds explicit security-branch and ready-for-review triggers but is itself unvalidated. Keep the relay and Vite development server off the public internet; no real phone/Windows pairing is verified.
3. The active `micro-helper` base includes the loopback/Origin/Fetch-Metadata protections from merged PR #19. PR #37 now also verifies the actual ASGI socket peer IP, so a non-loopback client cannot bypass the Host check by spoofing `Host: localhost`. PR #13 remains open against the older `main` API and should not be confused with the active product-branch fix. These checks are defense in depth, not authentication; the local API must remain loopback-only and they do not secure hosted routes or the JARVIS relay.
4. Android/Windows physical-device acceptance tests are not recorded.
5. The hosted source mirror and AppDeploy live snapshot need explicit parity evidence before a source change can be called deployed.
6. Cross-device encrypted sync, conflict handling and device-session revocation are not yet proven end to end.
7. PR #23 → #31 → #32 → #34 → #35 now form a passing stacked trust-gateway/backup/restore/export-safety branch, but remain unmerged. Compare PR #34 against PR #25, then integrate the stack sequentially and run CI on the resulting `micro-helper` branch.
8. The active Windows Companion endpoint is Render, while the Cloudflare Durable Object relay is a separate replacement. PR #33 hardens the Render source but remains unmerged and undeployed. The Cloudflare Worker is also not deployed; no live WSS pairing or real phone-to-Windows action has been verified, and clients must not be switched between endpoints before a successful staging health check.
9. The active `micro-helper` integration branch is **diverged** from default `main`: comparison reports 210 commits ahead and 48 behind (merge base `a05bbae1755214fd6c329b1f5322b58c31a32620`). PR #37/#38 and the newer security/offline-vault stack target this non-default integration line. Do not merge the large divergence blindly; reconcile and test the complete stack on a dedicated integration candidate before any release merge.

## Next development order

1. Review the passing PR #23 → #31 → #32 → #34 stack against PR #25, then integrate the trust gateway and policy-gated backup/restore sequentially into `micro-helper`; run a fresh full suite on the integrated branch.
2. Review PR #33's active Render relay hardening, integrate it separately, then run a staging pairing test before any live endpoint change.
3. Extend the policy gate to the first hosted action adapter only after its authenticated identity, explicit approval UI and audit boundary are covered by integration tests.
4. Obtain real CI for JARVIS PR #10/#9/#12 (and resolve the duplicate #11 path) before considering the Windows bridge or phone relay reusable. Keep the phone path chat-only; perform physical pairing only after a trusted HTTPS certificate is installed on Android and the notebook.
5. Add a single capability matrix shared by hosted tools, local Python, Android and Windows Companion.
6. Run signed-in hosted end-to-end tests, then physical Android and Windows smoke tests.
7. Recalculate this checklist only after updating the evidence links and levels.

## Change log

- **1.0.0-checklist.22 (2026-11-13):** PR #37 enforces the actual ASGI socket peer IP for every private `/v1` request, accepts IPv4/IPv6 and IPv4-mapped loopback addresses, and rejects remote or unresolved peers even when Host is spoofed as localhost. CI run #43485502280 passed 103 project tests and 11 relay tests, embedded JavaScript syntax and Python compilation. Score remains 50.00%; this is local security hardening, not physical-device or release acceptance.


- **1.0.0-checklist.20 (2026-11-12):** records PR #37 as the consolidated superset candidate targeting `micro-helper`, with 12 changed files and the full trust/backup/export/worker stack plus handler-level route enforcement. Its latest documented head passed run #43285515333 (Python-checks job, embedded JavaScript, Python compilation, project and relay tests). Evidence levels and weighted score remain 50.00%; physical installation, signed-in cross-device flows, hosted/desktop policy integration and release acceptance remain unverified.

- **1.0.0-checklist.15 (2026-11-11):** records the consolidation of PR #23/#31/#32/#34/#35/#36 into a single review candidate targeting `micro-helper` (47 commits ahead, 0 behind, 12 changed files). A fresh CI run after the base retarget is pending; the 50.00% score is unchanged.

- **1.0.0-checklist.14 (2026-11-11):** records PR #36 worker prompt-format and exception-redaction fixes plus passing CI run #43079790199 (94 project tests, 11 relay tests, JavaScript syntax and Python compilation). The evidence-weighted score remains 50.00%; worker improvements do not substitute for integrated user workflows or physical platform acceptance.

- **1.0.0-checklist.13 (2026-11-10):** records PR #35's plaintext-export warnings, private-response cache controls, and regression coverage for the body-limit middleware's early 413 response. GitHub Actions run #42885578401 passed 91 project tests and 11 relay tests. The score remains 50.00% because the stacked PRs are unmerged and platform, hosted-sync and live pairing acceptance remain incomplete.

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


## Verified update — 2026-11-16 (checklist v23)

- **PR #40 — local API authentication:** adds first-run single-user password setup, scrypt password hashing, 12-hour HttpOnly/SameSite=Strict session cookies, server-side hashed session tokens, same-origin write checks and session revocation. This is local loopback authentication, not multi-user cloud authentication.
- **PR #43 — offline fail-closed:** removes the plaintext browser-local fallback for private memories/history/preferences/plans and locks private UI when the local API cannot verify the session. Existing legacy browser data is preserved untouched. Private data is unavailable offline until an encrypted vault is implemented; tracked by issue #44.
- **PR #45 — accessible auth gate:** setup/login now use dialog semantics and isolate the private page from assistive technology while the gate is active. Browser-auth UI regression tests were added.
- **PR #42/#46 — persistent login throttling:** replaces process-local counters with an atomic SQLite bucket, five attempts per 15-minute window, shared across loopback forms, cleared after successful login, without persisting client IP addresses. PR #46 carries the change into the newer accessible-auth stack.
- **PASS — PR #46 head:** `c85bd24d7ed5d9b49fd9b8602be8c02b4e10b5cd`, Actions run [#43887209373](https://github.com/dominixe2/springtrap-/actions/runs/43887209373): 121 project tests, 11 relay tests, two browser-auth UI tests, embedded browser JavaScript syntax and Python compilation passed. One Starlette/httpx TestClient deprecation warning remains in each pytest suite.
- **PASS — PR #47 new regression tests:** head `43e69ac5eb9029709cfb1c46953069cdb7ae90a7`, Actions run [#43927582477](https://github.com/dominixe2/springtrap-/actions/runs/43927582477): 123 project tests and 11 relay tests passed; two browser-auth UI tests, embedded JavaScript syntax and Python compilation passed. The new tests verify the lockout in a fresh Python interpreter using the same SQLite database, the exact 15-minute expiry boundary, and fail-closed behavior after a backwards wall-clock adjustment. One Starlette/httpx TestClient deprecation warning remains in each pytest suite.
- **Open security follow-up — issue #44:** encrypted offline vault remains unimplemented. Do not restore the old plaintext localStorage fallback as a shortcut.
- **JARVIS integration status:** PR #9 is the security-hardened chat-only Ollama phone path; PR #11 restricts Vite LAN access to trusted HTTPS; both remain draft/unmerged. PR #5 remains an unsafe historical feature branch and must not be merged as-is. Physical phone/Windows acceptance is still NOT RUN.

### Score and release decision

- **Evidence-weighted score remains 50.00/100.** The existing ten weighted criteria remain at evidence level 0.50 each. This update records additional auth/security implementation and passing CI, but no criterion has yet met the checklist's 0.75 threshold (integrated implementation, automated regression coverage and an end-to-end check on at least one target platform).
- **Change this run:** 0.00 percentage points in the release score; PR #47 adds stronger verified auth regressions, but physical platform acceptance and an end-to-end target-platform check remain absent.
- **Release decision:** NOT READY. No merge, production deployment, signed release, encrypted offline vault, or physical Android/Windows acceptance is claimed.


## Verified update — 2026-11-17 (checklist v25)

- **PR #48 — encrypted offline vault cryptographic core:** adds versioned AES-256-GCM envelopes, 128-bit random per-vault salt, fresh 96-bit IV per seal, PBKDF2-HMAC-SHA-256 at 600,000 iterations, non-extractable CryptoKey, authenticated metadata, strict envelope validation and an 8 MiB plaintext limit. Oversized base64url input is rejected before decoding/allocation.
- **In-memory session behavior:** read/write/reseal, explicit lock and configurable inactivity lock (default five minutes; accepted range 1 second to 24 hours). JavaScript cannot guarantee physical memory zeroization.
- **PASS — PR #48 head:** `935fe45ec3aeac87a8474109623567eb1c3df3a4`, Actions run [#44098616360](https://github.com/dominixe2/springtrap-/actions/runs/44098616360): 123 project tests, 11 relay tests, two browser-auth UI tests, nine vault crypto tests, embedded JavaScript syntax and Python compilation passed. Two non-blocking Starlette/httpx TestClient deprecation warnings remain.
- **Not integrated:** the crypto core is not yet connected to IndexedDB or the app UI. It does not enable private offline mode or migrate legacy plaintext records. The fail-closed offline lock remains active; no existing data is read, modified or deleted.
- **Acceptance gap:** Node Web Crypto tests are not browser-level acceptance. Android and Windows physical-device checks remain NOT RUN.

### Score and release decision

- **Evidence-weighted score remains 50.00/100.** The cryptographic primitive and regression coverage are now present, but the vault is not integrated with persistence/UI and has no browser or physical-device acceptance.
- **Change this run:** 0.00 percentage points; the feature remains a draft implementation component rather than an integrated user-facing capability.
- **Release decision:** NOT READY. No merge, deployment, legacy-data migration, or physical Android/Windows acceptance is claimed.


## Verified update — 2026-11-17 (checklist v26)

- **PR #49 — IndexedDB persistence adapter:** adds `src/micro_helper/static/offline-vault-storage.js`, a separate storage boundary that accepts only the exact version-1 encrypted vault envelope. It validates fixed PBKDF2-HMAC-SHA-256 (600,000 iterations) and AES-256-GCM metadata, salt/IV/ciphertext encodings and the ciphertext size limit before opening IndexedDB. The adapter writes one fixed record in an atomic read/write transaction, returns only the validated envelope, and fails closed for unavailable, blocked or corrupt storage. It does not accept plaintext records, passphrases or CryptoKey values.
- **Regression coverage:** `tests/offline-vault-storage.test.mjs` covers empty storage, persistence across adapter instances, plaintext absence, malformed/unsupported envelopes, missing IndexedDB and preservation of a corrupt stored record without silently replacing it. The workflow now syntax-checks the adapter and runs this suite.
- **PASS — PR #49 head:** `504e58e196bd92db5a469503cc1a631c553cf4a7`, Actions run [#44153939656](https://github.com/dominixe2/springtrap-/actions/runs/44153939656): 123 project tests, 11 relay tests, two browser-auth UI tests, nine crypto tests and five storage tests passed; embedded JavaScript syntax and Python compilation passed. Two non-blocking Starlette/httpx TestClient deprecation warnings remain.
- **Not integrated:** the adapter is not yet wired to the app UI or service-worker lifecycle. Offline private mode remains disabled; no legacy plaintext data was read, migrated, overwritten or deleted. The five IndexedDB tests use a deterministic Node test double, not a real browser.
- **Acceptance gap:** real-browser IndexedDB behavior, offline unlock/read/write/lock flow, explicit user-controlled migration, Android and Windows physical-device acceptance remain NOT RUN.

### Score and release decision

- **Evidence-weighted score remains 50.00/100.** The new adapter is isolated and CI-tested, but the user-facing offline flow and browser/platform acceptance are not integrated; no weighted criterion reaches the 0.75 evidence threshold.
- **Change this run:** 0.00 percentage points. This is a concrete implementation step toward issue #44, not a complete offline feature.
- **Release decision:** NOT READY. PR #49 remains a draft stacked on PR #48. No merge, deployment, migration or physical-device acceptance is claimed.


## Verified update — 2026-11-18 (checklist v27)

- **PR #50 — canonical encrypted-envelope encoding:** the IndexedDB adapter now rejects base64url strings with non-zero unused trailing bits. This prevents alternate/non-canonical encodings from being accepted at the persistence boundary. Salt and ciphertext regression cases verify rejection happens before IndexedDB is opened.
- **PASS — PR #50 head:** `c831a246ef47760d14bdaae733795db7232a6937`, Actions run [#44315990763](https://github.com/dominixe2/springtrap-/actions/runs/44315990763): 123 Python project tests, 11 relay tests, two browser-auth UI tests, nine vault crypto tests and six IndexedDB storage tests passed. Embedded JavaScript syntax and Python compilation passed. One non-blocking Starlette/httpx TestClient deprecation warning appeared in each Python suite.
- **Not integrated:** the vault core and IndexedDB adapter are still not connected to the app UI or service-worker lifecycle. Private offline mode remains fail-closed. No legacy plaintext data was read, migrated, overwritten or deleted.
- **Acceptance gap:** current IndexedDB tests use a deterministic Node test double. Real-browser IndexedDB, UI unlock/lock, explicit migration, Android and Windows acceptance remain NOT RUN.

### Score and release decision

- **Evidence-weighted score remains 50.00/100.** Canonical encoding validation improves the persistence boundary but does not complete the user-facing offline vault or target-platform acceptance.
- **Change this run:** 0.00 percentage points; the implementation remains a draft security hardening step.
- **Release decision:** NOT READY. No merge, deployment, legacy-data migration or physical-device acceptance is claimed.


## Verified update — 2026-11-18 (checklist v28)

- **PR #52 — service-worker cache boundary regression suite:** adds four Node tests proving that same-origin private `/v1/` reads, writes and deletes are never intercepted by the service worker, that cross-origin resources are not intercepted, and that the existing same-origin static-asset cache path still works. The tests cover auth status, conversations, memories, preferences, backup, tasks, learning plans and confirmation endpoints.
- **PASS — PR #52 head:** `5549360c402edfdfdfc1dd2919ad3f3989e6493c`, Actions run [#44373266894](https://github.com/dominixe2/springtrap-/actions/runs/44373266894). The workflow passed embedded browser JavaScript syntax checks, 2 browser-auth UI tests, 9 vault crypto tests, 6 IndexedDB storage tests, **4 new service-worker cache-boundary tests**, Python compilation, 123 project tests and 11 relay tests. One non-blocking Starlette/httpx TestClient deprecation warning appeared in each Python suite.
- **Scope:** this is regression protection only. It does not wire the encrypted vault into the UI or enable offline private data. The private offline experience remains fail-closed; legacy plaintext data remains untouched.
- **Acceptance gap:** the IndexedDB adapter still uses a deterministic Node test double; real-browser IndexedDB, vault UI unlock/lock, explicit legacy migration, offline reads/writes and physical Android/Windows acceptance remain NOT RUN.

### Score and release decision

- **Evidence-weighted score remains 50.00/100.** The new tests improve confidence in the service-worker privacy boundary but do not satisfy the integrated offline-vault or target-platform acceptance criteria.
- **Change this run:** 0.00 percentage points.
- **Release decision:** NOT READY. PR #52 is a draft stacked on PR #50; no merge, deployment, migration or physical-device acceptance is claimed.


## Verified update — 2026-11-19 (checklist v29)

- **PR #53 — encrypted backup vault UI:** loads the existing WebCrypto vault core and IndexedDB adapter into the app; creates an encrypted copy of the authenticated local backup; requires matching passphrase confirmation for creation/replacement; imports/exports encrypted envelopes only; unlocks in memory; shows counts rather than private contents; and sends restore through the existing body-bound Trust Engine confirmation wrapper. The page-hide lifecycle locks the session and closes the storage adapter.
- **PASS — PR #53 final head:** f9514482c78846aa38abe7fba4853cbcf165c980, Actions run [#44539529981](https://github.com/dominixe2/springtrap-/actions/runs/44539529981). Passed 123 Python project tests, 11 relay tests, 2 browser-auth UI tests, 9 vault crypto tests, 6 IndexedDB adapter tests, 12 encrypted-vault UI controller tests, 4 service-worker cache-boundary tests, embedded JavaScript syntax checks (including the new UI controller), and Python compilation. One non-blocking Starlette/httpx TestClient deprecation warning appeared in each Python suite.
- **Scope:** this is an encrypted backup workflow, not full offline private-data access. The private /v1/ API remains excluded from service-worker caching; memories/history/tasks/preferences still require the authenticated local API. The existing offline lock remains fail-closed. No legacy plaintext browser data is read, migrated, overwritten or deleted.
- **Acceptance gap:** vault UI tests use Node mocks and the IndexedDB adapter uses a deterministic test double. Real-browser IndexedDB, actual WebCrypto behavior in target browsers, offline reads/writes, Android and Windows acceptance remain NOT RUN. No physical device is claimed.
- **Safety:** restore remains an explicit destructive action handled by the shared fetch policy wrapper and the one-time body-bound confirmation. Import accepts encrypted envelopes only. No merge, deployment, data migration or deletion is included.

### Score and release decision

- **Evidence-weighted score remains 50.00/100.** The new user-facing encrypted-backup flow is a meaningful feature step, but it does not yet enable private offline reads/writes or satisfy browser/platform acceptance.
- **Change this run:** 0.00 percentage points; the existing weighted acceptance criteria remain unchanged.
- **Release decision:** NOT READY. PR #53 is a draft stacked on PR #52 → #50 → #49 → #48 → #47. Do not merge it independently of its base. No merge, deployment or legacy-data migration is claimed.


## Verified update — 2026-11-19 (checklist v30)

- **PR #53 follow-up:** after the first successful run, review found that importing an encrypted file performed a second IndexedDB read after the write transaction had already committed. A transient readback failure could therefore have been reported as an import failure even though the new envelope was saved. The UI now uses the validated input envelope after the successful atomic save and does not make success depend on a redundant readback. Added a regression test that simulates a post-save read failure.
- **PASS — PR #53 code head:** 5228d9fbd948188fb7098e0e937c4d8fa2bbebae, Actions run [#44540502219](https://github.com/dominixe2/springtrap-/actions/runs/44540502219).
- **168 test cases passed:** 123 Python project tests, 11 relay tests, 2 browser-auth UI tests, 9 vault crypto tests, 6 IndexedDB adapter tests, 13 encrypted-vault UI controller tests and 4 service-worker cache-boundary tests. Embedded JavaScript syntax checks (including offline-vault-ui.js) and Python compilation passed. One non-blocking Starlette/httpx TestClient deprecation warning appeared in each Python suite.
- **Scope remains unchanged:** the vault is an encrypted backup workflow, not the source of offline private-data reads/writes. The private API remains excluded from service-worker caching and the offline private-data lock remains fail-closed. Legacy plaintext browser data is untouched. Real-browser, Android and Windows acceptance remain NOT RUN.

### Score and release decision

- **Evidence-weighted score remains 50.00/100.** The import reliability fix improves the user-facing encrypted backup workflow but does not satisfy full offline private-data or target-platform acceptance.
- **Change this run:** 0.00 percentage points.
- **Release decision:** NOT READY. PR #53 remains a draft stacked on PR #52 → #50 → #49 → #48 → #47. No merge, deployment, legacy-data migration or deletion is claimed.


## Verified update — 2026-11-19 (checklist v31)

- **PR #54 — background-lock hardening:** the encrypted backup controller now locks the in-memory session immediately when the document becomes hidden, reports the locked state on return, and requires a fresh passphrase. A visibility epoch also prevents a hidden → visible race from completing an in-flight PBKDF2 unlock. Backup creation is aborted before or after encryption if the page was backgrounded during the operation. The visibility listener is removed during controller disposal.
- **Regression coverage:** three new controller tests cover immediate lock and restore denial, a hidden → visible transition during unlock, and backgrounding during encrypted-backup creation. The code and tests are on branch security/offline-vault-lock-on-hidden-20261119; latest code/test commit at checklist update: 0b98a0f0ff1295758e73df83ff518273489d222d.
- **CI:** NOT RUN / no PR-triggered workflow run is currently returned for PR #54's latest head. Do not treat the added tests as passing until GitHub Actions reports success. Real-browser lifecycle behavior, Android, Windows and physical-device acceptance remain NOT RUN.
- **Security scope:** this closes the background-unlock lifecycle gap in the UI only. It does not enable offline private-data access, change the fail-closed service-worker boundary, migrate legacy plaintext data or alter the explicit body-bound restore confirmation. JavaScript cannot guarantee physical zeroization of immutable passphrase strings.
- **Bug accounting:** one unique background-session lifecycle security defect addressed; no additional confirmed defects are introduced by this change. Existing non-blocking Starlette/httpx TestClient deprecation warnings remain outside this UI change.

### Score and release decision

- **Evidence-weighted score remains 50.00/100.** The weighted criteria still require integrated end-to-end evidence and target-platform acceptance; PR #54's CI and browser lifecycle checks are not yet verified. No evidence level is raised.
- **Change this run:** 0.00 percentage points.
- **Release decision:** NOT READY. PR #54 is a draft stacked on PR #53 and its base chain. No merge, deployment, offline private-data migration or physical-device acceptance is claimed.


## Verified update — 2026-11-19 (checklist v32)

- **PR #54 — background-lock hardening CI:** GitHub Actions run [#44592605947](https://github.com/dominixe2/springtrap-/actions/runs/44592605947) completed successfully on head `5a49ce9fd07a851cc51f4e38560f23c671e806db`.
- **PASS — 171 automated tests, 0 failures:** 123 Python project tests; 11 relay tests; 2 browser-auth UI tests; 9 encrypted-vault crypto tests; 6 IndexedDB storage tests; 16 encrypted-vault UI controller tests (including the three new background-lifecycle regressions); and 4 service-worker cache-boundary tests. Embedded browser JavaScript syntax checks and Python compilation passed. The two Python suites each emitted one non-blocking Starlette/httpx TestClient deprecation warning.
- **Scope:** CI verifies the controller's hidden-page lock, restore denial after backgrounding, rejection of the hidden → visible unlock race, and cancellation of encrypted-backup creation during backgrounding. This remains an encrypted backup feature, not full offline private-data access. Real-browser IndexedDB/WebCrypto lifecycle, Android, Windows and physical-device acceptance remain NOT RUN.
- **Release decision:** NOT READY. PR #54 remains a draft stacked on PR #53. No evidence level is raised solely from mocked controller tests and CI; real-browser/platform acceptance and full private offline workflow remain outstanding.

### Score and release decision

- **Evidence-weighted score remains 50.00/100.** The new tests establish the controller regression behavior in CI but do not satisfy the 0.75 end-to-end target-platform evidence threshold. No weighted criterion is raised.
- **Change this run:** 0.00 percentage points.
- **Known warning:** one unique Starlette/httpx TestClient deprecation warning per Python suite (two warning emissions in this run); no failing tests.


## Verified update — 2026-11-19 (checklist v33)

- **JARVIS integration review:** confirmed PR #9, #10, #11 and #12 are still open. PR #12 is a six-commit follow-up directly on PR #9; PR #11 is a parallel Vite-network hardening branch on PR #10. No Actions runs were returned for the current heads of #9, #10, #11 or #12. The PRs are therefore not yet verified integration inputs for Micro Helper's Windows adapter.
- **Safety decision:** keep the JARVIS Windows bridge and phone relay separate from Micro Helper until the authenticated relay and trusted-HTTPS listener have passing CI and a physical phone-to-notebook smoke test. No merge or network exposure was performed.
- **Score:** remains 50.00/100; this repository review changes no weighted acceptance evidence.


## Verified update — 2026-11-19 (checklist v34)

- **Branch integration state:** repository default branch is `main`; the active `micro-helper` branch is 210 commits ahead and 48 behind `main`, with merge base `a05bbae1755214fd6c329b1f5322b58c31a32620`. PR #37 and #38 target `micro-helper`; the encrypted-vault stack ultimately builds on that integration line. This is a material release-integration risk, not a reason to overwrite or reset either branch.
- **Release safety:** keep the PR chain stacked and unmerged. Before release, prepare a reviewed integration branch that reconciles the 48 commits on `main`, then run the full combined CI and platform builds. No merge or branch rewrite was performed in this run.
- **Score:** remains 50.00/100; branch topology is a blocker, not earned acceptance evidence.


## Verified update — 2026-11-19 (checklist v35)

- **PR #54 final CI:** GitHub Actions run [#44593137867](https://github.com/dominixe2/springtrap-/actions/runs/44593137867) completed successfully on latest PR head `f52040e8e183c61034f14972543df7a0b4b734b6`.
- **PASS — 171 automated tests, 0 failures:** 123 Python project tests; 11 relay tests; 2 browser-auth UI tests; 9 encrypted-vault crypto tests; 6 IndexedDB storage tests; 16 encrypted-vault UI controller tests (including background-lock, unlock-race, interrupted-create and pagehide-listener-cleanup coverage); and 4 service-worker cache-boundary tests. Embedded browser JavaScript syntax checks and Python compilation passed. Each Python suite emitted one non-blocking Starlette/httpx TestClient deprecation warning.
- **Platform/build scope:** the Micro Helper checks workflow does not build the Android APK or Windows Companion and does not run a real browser. Android, Windows, real IndexedDB/WebCrypto, physical devices, hosted end-to-end, lint and type-check acceptance remain NOT RUN in this PR.
- **Security scope:** the in-memory encrypted backup now locks when the page becomes hidden; a visibility epoch blocks a hidden → visible unlock race; interrupted backup creation is not persisted; and pagehide removes the listener and closes IndexedDB. Full offline private-data reads/writes remain disabled and the service worker still bypasses private /v1/ responses.

### Score and release decision

- **Evidence-weighted score remains 50.00/100.** CI verifies the controller and regression suites but does not meet the real-browser/target-platform acceptance threshold. No weighted criterion is raised.
- **Change this run:** 0.00 percentage points.
- **Bug accounting:** one unique background-session lifecycle security defect fixed; zero failing tests; two non-blocking warning emissions. Release blockers listed above remain open.
- **Release decision:** NOT READY. PR #54 remains a draft stacked on PR #53; no merge, deployment, legacy-data migration or physical-device acceptance is claimed.


## Verified update — 2026-11-20 (checklist v36)

- **PR #55 — abortable encrypted persistence:** the vault controller now aborts the authenticated backup fetch and an in-flight IndexedDB readwrite transaction when the document becomes hidden or the controller is disposed. A backup cannot start while already hidden. A pre-aborted save is rejected before IndexedDB is opened. If the transaction commits before the visibility event, the UI reports the committed encrypted backup accurately; otherwise the transaction aborts atomically and the previous envelope remains unchanged.
- **Regression coverage:** two storage-adapter tests prove in-flight transaction abort preserves the previous encrypted record and a pre-aborted signal does not open IndexedDB. One controller test proves backgrounding during save aborts the pending operation. Existing encryption, unlock-race, service-worker and authentication regressions remain in the same workflow.
- **CI PASS:** run [#44748932578](https://github.com/dominixe2/springtrap-/actions/runs/44748932578) on PR #55 head `d850c37fbfff9d1e4a652c58574564c3beb55e87`. The job completed successfully: 123 Python project tests, 11 relay tests, 2 browser-auth tests, 9 vault crypto tests, 8 IndexedDB storage tests, 17 vault UI tests and 4 service-worker tests — **174 total, 0 failures**. Embedded JavaScript syntax and Python compilation passed. The two Python suites each emitted one non-blocking Starlette/httpx TestClient deprecation warning.
- **PASS (automated controller scope):** draft PR #63 now supports encrypted offline reads for memories, preferences, history, tasks and learning plans; local edits for memories/preferences; explicit-confirmation deletion and offline-history clearing; rollback on failed persistence; inactivity/background lock and clearing of decrypted UI. Tasks and learning plans remain read-only. The service worker precaches the vault code but still bypasses private `/v1/` routes.
- **NOT RUN:** real-browser IndexedDB/WebCrypto timing, physical Android/Windows acceptance, hosted-PWA offline integration, automatic sync/conflict resolution, and legacy plaintext migration. Offline AI/chat is not provided.
- **Release decision:** NOT READY. PR #55 remains a draft stacked on PR #54 → #53 → #52 → #50 → #49 → #48. No merge, deployment, migration or deletion was performed. Evidence-weighted score remains 50.00/100.


## Verified update — 2026-11-24 (checklist v37)

- **PR #63 — encrypted offline private workspace:** adds a separately scoped offline workspace to the local Python edition. The existing encrypted IndexedDB envelope is now a working local copy for memory and preference inspection/editing, conversation-history review/clearing, and read-only task/learning-plan inspection. No automatic sync or server writes occur while offline.
- **Security lifecycle:** the vault core now notifies UI subscribers on explicit or inactivity lock. The controller clears decrypted workspace text and select options, clears editable fields, and aborts a pending offline save when the page is hidden or the inactivity lock fires. The offline authentication notice keeps the normal chat and server-backed sections inert while leaving only the encrypted-vault section interactive.
- **PWA shell:** cache version advanced to v5 and the three local vault modules are precached. The worker still bypasses every private `/v1/` response.
- **Regression coverage:** added tests for encrypted local memory/preference edits, explicit delete/history confirmation, failed-save rollback, inactivity DOM clearing, background-aborted saves, auth isolation and vault-module precaching.
- **CI PASS:** run [#45458039933](https://github.com/dominixe2/springtrap-/actions/runs/45458039933) on PR #63 head `62ee676a4b0e9aedc8296e7a3c5ea4c373bdfc3b`: 48 Node tests, 123 Python project tests and 11 relay tests — **182 passed, 0 failed**. Embedded browser JavaScript syntax and Python compilation passed. Two non-blocking deprecation warnings remain. The first PR run failed only on a case-sensitive test-message assertion; the assertion was corrected and the subsequent run passed.
- **NOT RUN:** real-browser IndexedDB/WebCrypto behavior, physical Android/Windows use, hosted-PWA integration, sync/conflict handling and legacy plaintext migration.
- **Score:** remains **50.00/100** for this local-edition checklist. The automated implementation is not counted as complete platform acceptance. **Release decision: NOT READY.** PR #63 remains a draft stacked on PR #55; no merge, deployment, migration or destructive server restore was performed.


## Verified update — 2026-11-24 (checklist v38)

- **Offline server-action boundary:** when local authentication cannot be verified, the document is marked as offline-auth-unavailable. Backup creation and server restore are disabled in the vault UI and independently rejected by the controller; encrypted import/export and local vault editing remain available.
- **Regression coverage:** added a test proving offline auth state blocks both server backup creation and server restore without issuing an API request. Existing offline CRUD, confirmation, rollback, auto-lock clearing, background abort and service-worker tests remain green.
- **CI PASS:** latest PR #63 head `375dcefa144aa21c122086c29b25bca1a6627343`, run [#45459534856](https://github.com/dominixe2/springtrap-/actions/runs/45459534856): 49 Node tests, 123 Python project tests and 11 relay tests — **183 passed, 0 failed**. Embedded JavaScript syntax and Python compilation passed; two non-blocking deprecation warnings remain.
- **Security review:** no new dependency, secret, account permission, device-control capability, remote mutation or deployment was added. Offline mutations are confined to the encrypted browser envelope; server restore still requires an authenticated online session and explicit confirmation.
- **NOT RUN:** real-browser IndexedDB/WebCrypto, physical Android/Windows, hosted-PWA offline integration, automatic sync/conflict handling and legacy plaintext migration.
- **Score:** remains **50.00/100** for this local-edition checklist; this does not replace the overall product score in the release checklist. **Release decision: NOT READY.**


## Verified update — 2026-11-24 (checklist v39)

- **Fail-closed local authentication bootstrap:** the local Python app shell is hidden until the auth-status request resolves and the authenticated state, login/setup gate, or isolated offline-vault gate is rendered. If gate initialization or isolation fails, the page remains hidden instead of revealing the private UI.
- **PWA cache refresh:** service-worker cache advanced from v5 to v6 so the updated auth bootstrap HTML and script are not indefinitely shadowed by the previous cached app shell.
- **Regression coverage:** a delayed auth-status test proves the app remains hidden while verification is pending and becomes visible only after an authenticated response. Existing login/setup/offline gate tests now assert the auth-ready marker. The API/PWA test asserts cache v6.
- **CI PASS:** PR #64 head `4da6369d5f1bb19c0189bed4b477f68941053a7f`, GitHub Actions run [#45461398382](https://github.com/dominixe2/springtrap-/actions/runs/45461398382): 3 browser-auth tests, 10 vault-crypto tests, 8 IndexedDB-storage tests, 24 vault-UI tests and 5 service-worker tests — **50 Node tests**; 123 Python project tests and 11 relay tests — **184 total, 0 failures**. Embedded JavaScript syntax and Python compilation passed. Two non-blocking Starlette/httpx TestClient deprecation warnings remain.
- **Security review:** no dependency, secret, account permission, tool grant, remote action, or deployment was added. No private content is rendered before auth verification; the offline vault remains separately scoped.
- **NOT RUN:** real-browser timing/visibility, physical Android/Windows acceptance, hosted-PWA integration, penetration review and release rollback drill.
- **Score:** remains **50.00/100**. This startup hardening adds automated evidence but does not establish target-platform acceptance or complete release security review. **Release decision: NOT READY.** PR #64 is a draft stacked on PR #63; no merge or deployment was performed.
