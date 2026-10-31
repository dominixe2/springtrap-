# Micro Helper: Master Execution Roadmap

Status: living plan. This is the execution order, not a claim that every feature already exists.
Target principle: a useful phone-first assistant that remains free to run, is inspectable, and gains capabilities through reviewed modules rather than self-modifying production code.

## Product definition
Micro Helper should become a personal, Czech-first assistant with durable memory, extensible knowledge, optional local AI, a safe task worker, phone-first access, and later paired-device operation with the Windows notebook. It must remain useful when optional components are offline. No paid API key is a design constraint; local model quality and hardware limits must be stated honestly.

## Non-negotiable engineering rules
1. Keep the current working app usable; ship changes in small branches and reviewable commits.
2. No feature is called complete until implementation, tests, and a real run are verified.
3. Default-deny tools. Knowledge packs never grant permissions.
4. The model may propose plans, data, and code patches; it cannot approve its own permissions or execute arbitrary code.
5. Every imported dataset records source, licence/permission, format, date, checksum, and owner approval.
6. Support inspect, export, pause, rollback, and delete for learning plans and knowledge packs.
7. Keep user data local by default. Remote sync requires authenticated pairing and encryption before any deployment.
8. Do not promise background work, notifications, or synchronization until an actual worker/device path is installed and tested.

## Delivery sequence and acceptance gates

### Phase 0 — Repository baseline and reliability
- Preserve the existing PWA, API, SQLite memory, preferences, Ollama adapter, and bounded task queue.
- Establish repeatable tests, health/status/capability reporting, dependency and configuration checks.
- Fix broken imports, startup failures, and UI/API mismatches before adding more autonomy.
- Gate: clean test run; app starts; status accurately lists available and missing features.

### Phase 1 — Learning-plan manager (first implementation slice)
- CRUD learning plans with title, objective, ordered steps, status (draft/active/paused), sources, timestamps, and version.
- User can inspect/edit/pause/delete plans. Plans are data only, not executable commands.
- Gate: API tests for validation, persistence, version increments, missing IDs, and delete; simple mobile UI.

### Phase 2 — Knowledge-pack ingestion
- Add pack registry and import pipeline for TXT, Markdown, CSV, JSON, and PDF text where feasible.
- Store original file, metadata, checksum, provenance, licence/permission, and chunk/index records.
- Start with local keyword search; add local vector search only if dependencies/hardware justify it.
- Gate: import/export round trip, source attribution, size/type limits, duplicate detection, deletion of all derived chunks.

### Phase 3 — Retrieval-grounded learning
- Retrieve only from enabled, user-approved packs; include source references in answers.
- Separate facts, user memories, assistant-generated suggestions, and unverified claims.
- Let the assistant propose corrections/new pack ideas as drafts. User can approve, reject, or edit.
- Gate: evaluation questions must cite the correct source; no source means disclose uncertainty.

### Phase 4 — Evaluation and adaptation loop
- Each plan has measurable objectives, example questions/tasks, expected criteria, and progress history.
- Run bounded evaluations through the persistent queue. Record model, prompt, pack versions, score, failures, and evidence.
- Adapt study sequence and propose new material; never silently rewrite trusted source data.
- Gate: repeatable evaluations and versioned progress, with pause/rollback.

### Phase 5 — Extensible skill packs
- Define signed/versioned manifests, declared inputs/outputs, permissions, risk level, dependencies, and tests.
- Begin with read-only skills. Add writes only behind per-action confirmation and audit logs.
- Execute skills in a restricted process/container with time, memory, filesystem, and network limits.
- Gate: denied-by-default tests; malicious prompt/data cannot expand permissions; rollback works.

### Phase 6 — Durable worker and notifications
- Make queue jobs restart-safe, cancellable, retry-bounded, idempotent, observable, and resumable.
- Worker runs on a device/server that is actually online. Add Android notification bridge only after native/PWA support is verified.
- Gate: close phone/browser, worker continues on host; completion notification reaches paired phone; failure and cancellation are visible.

### Phase 7 — Phone-first install and notebook pairing
- First make the responsive PWA installable and reliable on Android; document exact start/access steps.
- Then implement authenticated one-time pairing, device identity, encrypted transport, conflict resolution, and revocation.
- Add Windows worker as a separate least-privilege service, not as unrestricted remote shell.
- Gate: sync same approved data both directions, handle offline edits/conflicts, revoke a lost device.

### Phase 8 — Voice, offline resilience, and polish
- Improve Czech voice UX using supported browser/native speech services; do not claim wake-word or always-listening unless actually implemented.
- Cache app shell and safe read-only data; explain that AI inference needs a running local model.
- Accessibility, backup/restore, migration, diagnostics, performance, and security review.
- Gate: documented recovery test and realistic device performance.

## Release definition
A release is installable only when its artifact exists, has a version, is built from a known commit, and passes its declared checks. A phone-ready release additionally needs a tested installation path. A synchronized release additionally needs verified device pairing and conflict tests.

## Immediate next tasks
1. Complete Phase 1 API and tests.
2. Run the full test suite in a real Python environment; fix any failures.
3. Add the mobile learning-plan UI and status/capability entries.
4. Commit a phase report with what passed and what remains.
5. Only then begin Phase 2.

## Explicitly not promised yet
No native APK, no remote/cloud service, no background work after this coding session, no push notifications, no secure multi-device sync, no arbitrary self-installing skills, and no offline LLM inference are claimed by this roadmap.
