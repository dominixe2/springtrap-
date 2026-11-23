# Micro Helper 1.0 release checklist

**Version:** 0.1  
**Snapshot date:** 2026-11-23  
**Baseline:** `micro-helper` branch at `02125f6b3d90055243a65bfc40800fdcae6827b8`  
**Related release work:** [PR #61](https://github.com/dominixe2/springtrap-/pull/61), [PR #57](https://github.com/dominixe2/springtrap-/pull/57), [PR #29](https://github.com/dominixe2/springtrap-/pull/29)

## Scoring rules

The release score is the sum of verified points earned divided by 100 weighted points. A partial score is allowed only where working code exists and at least one relevant automated check or repository-level verification supports it. A proposal, mock-up, documentation-only design, open PR, untested code, or passing static build alone does not count as a completed user-facing capability. Open PRs are tracked as work in progress and are not treated as shipped.

A criterion is **complete** only after implementation, relevant automated tests, security review where applicable, and the required platform/user-flow verification. Physical-device checks are called out separately. The score is intentionally conservative and is not a claim of release readiness.

## Weighted acceptance criteria

| Area | Weight | Earned | Status | Evidence and remaining acceptance |
|---|---:|---:|---|---|
| Responsive client, chat, history, settings and installable PWA | 15 | 8 | Partial | `hosted-app/`, `android-wrapper/`, service-worker and hosted-app workflows exist. The published AppDeploy snapshot is older than the GitHub source; Android/desktop real-device acceptance is not complete. See `README.md` and `hosted-app/RELEASE_VALIDATION.md`. |
| Original Micro Helper identity, configurable personality and avatar | 5 | 0 | Missing | `docs/PRODUCT_SPEC.md` defines optional identity/mascot settings, but the original avatar implementation remains in open PR #15 and is not credited as shipped. |
| Czech-first text and honest voice input/output | 8 | 3 | Partial | Browser voice controls and Czech defaults are documented in `README.md` and `docs/SECURITY.md`. Browser support, installed Czech voices, microphone permissions and background limitations still require platform verification. |
| Modular AI providers with local/offline fallback and truthful limits | 10 | 4 | Partial | The local FastAPI/Ollama path and hosted cloud AI path exist. Local inference requires a configured model/runtime; cloud AI and hosted features require network/account/provider quota. Provider switching and fallback behavior still need end-to-end tests. |
| User-controlled memory, preferences, correction and deletion | 10 | 3 | Partial | Account-scoped state and private notes/preferences are present in the hosted source. The browser-local fallback is not encrypted by this app; encrypted offline vault and backup improvements remain in open PRs #48–#55. |
| Tools, file handling, search, analysis and durable task lifecycle | 10 | 4 | Partial | Search/image-related handlers and a durable SQLite task queue exist. The current worker supports only the bounded `agent.draft` task; Windows Companion actions remain a small fixed allowlist. See `docs/ARCHITECTURE.md`. |
| Adaptive Trust Engine, scoped permissions, confirmation and audit | 18 | 4 | Partial | Existing local API/origin protections and restricted Windows action handling provide a baseline. Full mutation-route enforcement, memory/preference mutation coverage and runtime regression proof remain open work (issues #26 and PRs #31–#37, #56). Learned behavior must never grant permission. |
| Authenticated phone–Windows pairing, encrypted transport, revocation and least privilege | 10 | 4 | Partial | Pairing codes, separate tokens, session expiry/revocation and a fixed action allowlist exist in the relay/Windows Companion. The staging relay is in-memory and can lose sessions on restart; browser-origin configuration is still under review in PR #61. Physical Android/Windows pairing is not verified. |
| Safe JARVIS capability reuse through an explicit adapter boundary | 5 | 0 | Missing | JARVIS remains a separate repository and application. No reviewed, tested Micro Helper adapter contract or integrated capability is shipped. Reuse must preserve JARVIS's localhost boundary and write-disabled default. |
| CI, security review, release packaging and supported-platform acceptance | 9 | 4 | Partial | GitHub checks and Android/Windows packaging workflows exist; the active relay PR chain has green hosted CI (run #45192457111). AppDeploy publication is blocked by its usage limit, Android package is debug-signed, Windows EXE is unsigned, and physical-device acceptance is outstanding. |

**Baseline score: 34 / 100 = 34%.**

## Current verification snapshot

- GitHub Actions Micro Helper checks: **PASS** on PR #61 base/head snapshot, run [#45192457111](https://github.com/dominixe2/springtrap-/actions/runs/45192457111) (52 project tests, 45 relay tests, embedded JavaScript syntax and Python compilation).
- Physical Android: **NOT RUN**.
- Physical Windows pairing/automation: **NOT RUN**.
- AppDeploy live publication and post-deploy QA: **BLOCKED** by the previously documented usage limit; source changes are not automatically live.
- Cloudflare Durable Object relay deployment: **NOT RUN**.
- JARVIS-to-Micro-Helper adapter acceptance: **NOT RUN**.

## Open release blockers

1. Complete and test the Adaptive Trust Engine on every state-changing API route, including memory and preference mutations; prove fresh operation-bound confirmation and revocation.
2. Finish encrypted offline memory/backup lifecycle and verify inspect, correct, export and delete behavior.
3. Complete the original configurable Micro Helper identity/avatar and responsive user flows.
4. Verify voice and chat on a physical Android device and Windows browser; keep browser/API limitations visible.
5. Finish secure phone–Windows pairing with explicit origin configuration, authenticated sessions, transport protection and revocation; verify on both physical devices.
6. Define and test a narrow JARVIS adapter contract; do not copy its UI, assets or broad computer-control surface.
7. Publish only through the authorized release path after AppDeploy access is available; produce release-signed packages and complete post-deploy smoke tests.
8. Triage open repository issues separately from defects; do not count every roadmap issue as a bug.

## Known issue accounting

This checklist does not equate open issues with confirmed defects. At this snapshot the repository has open tracked work for branch protection (#51), encrypted offline vault (#44), self-completion (#28), memory/preference mutation authorization (#26), and a broader product integration request (#12). These are tracked blockers/requirements, not five independently verified bugs. New and fixed defects must be recorded by unique root cause in the run report and linked to a regression test or commit.

## Update procedure

For each development run, update this file in the same reviewable PR or a focused release-status PR. Increment the version, snapshot date and baseline commit; change earned points only when new implementation and evidence satisfy the scoring rules. Record each newly fixed defect once, keep open issues separate from bugs, and never mark version 1.0 released until every release gate above is satisfied.
