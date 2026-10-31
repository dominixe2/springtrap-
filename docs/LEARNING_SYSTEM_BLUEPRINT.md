# Micro Helper: Learning system blueprint

Status: design blueprint; this document does not claim that the learning system is implemented.

## Product idea

Micro Helper grows through small, optional, versioned learning packs. The owner can add a new goal or topic at any time. The assistant can propose a learning plan and prepare starter materials, while the owner can import their own datasets. Later, the assistant may propose additional packs based on gaps it can demonstrate. Nothing is silently installed or treated as trusted instructions.

The system learns the owner's domain knowledge and preferences; it does not retrain model weights by default. The first implementation should use retrieval (searching approved notes and documents at answer time), structured preferences, and tested tool/skill definitions. This is cheaper, reversible, inspectable, and compatible with local models.

## Core building blocks

1. **Learning plan** — a user-visible goal with scope, milestones, prerequisites, acceptance tests, and status. Plans can be added, paused, reordered, edited, or removed at any time.
2. **Knowledge pack** — versioned material for one subject: documents, examples, glossary, FAQs, structured records, source URLs, and metadata. Every item records its origin, owner, license/usage notes, import date, and content hash.
3. **Skill pack** — a separate, explicit capability definition: what the skill can do, required tools, input/output schema, risk level, permissions, and tests. Knowledge alone never grants a skill permission to act.
4. **Retrieval index** — local index over approved packs, with source references so answers can show which material they used. User data stays local by default.
5. **Evaluation suite** — sample questions and expected behaviors used to check whether a pack improves answers without causing regressions.
6. **Proposal queue** — assistant suggestions for missing topics, datasets, integrations, or skills. Suggestions are drafts until the owner approves them.
7. **Version and rollback manager** — every pack has versions; the owner can compare, disable, export, or roll back a version.

## Owner workflow

1. Owner adds a plan in plain Czech, for example: "Nauč se pracovat s mými servisními poznámkami k autu."
2. Micro Helper converts it into a proposed plan: goal, questions, milestones, needed files, and acceptance tests.
3. Owner edits or approves the plan and supplies documents/data, or asks Micro Helper to prepare a starter dataset.
4. Importer validates file types, size, encoding, duplicates, and metadata. Untrusted content is treated as data, never as system instructions.
5. Micro Helper builds a draft knowledge pack and a small evaluation set.
6. Owner reviews sources and approves activation. Only approved packs enter normal retrieval.
7. After use, Micro Helper can suggest gaps or a next pack, explaining the evidence for the suggestion. Owner decides whether to add it.
8. The owner can inspect, correct, export, disable, or delete the plan and its data.

## Assistant-provided starter datasets

The assistant may prepare starter material such as a Czech glossary, learning outline, synthetic examples clearly labeled as synthetic, public reference links, or templates. It must:
- distinguish sourced facts from generated examples;
- record source URLs, retrieval date, and license/usage notes where applicable;
- avoid copying restricted datasets or assuming that public access means reuse is permitted;
- flag uncertain or stale material for review;
- never invent that a dataset has been downloaded, imported, or verified.

The owner can then add their own files or records. A pack can combine assistant-prepared public references with owner-provided data, but provenance remains attached to each item.

## Safe self-improvement boundary

Micro Helper may autonomously:
- inspect approved knowledge packs and identify unanswered test questions;
- run read-only evaluations in a sandbox;
- draft a proposed plan, dataset, prompt, adapter, or code patch;
- report test results and explain what changed.

It must not autonomously:
- grant itself new permissions or broaden a tool's scope;
- execute arbitrary generated code on the phone or notebook;
- send messages, spend money, publish, delete, share private data, or modify external accounts;
- install a new skill or replace a working version without owner approval.

Code changes should be proposed as reviewable patches, tested in an isolated environment, and activated only after approval. High-impact tool calls require per-operation confirmation.

## Suggested data model

- `learning_plans`: id, title, goal, scope, milestones_json, status, created_at, updated_at.
- `knowledge_packs`: id, plan_id, name, version, status (draft/approved/disabled), description, created_at.
- `knowledge_items`: id, pack_id, kind, content_location, source, license_note, content_hash, imported_at.
- `skill_packs`: id, name, version, manifest_json, status, created_at.
- `evaluations`: id, pack_id, suite_version, results_json, passed, created_at.
- `improvement_proposals`: id, proposal_type, title, rationale, evidence_json, draft_location, status, created_at.
- `approval_events`: id, actor, action, target, decision, timestamp.

Large files should live in a local managed data directory; SQLite stores metadata and references. Do not put passwords, API keys, or other secrets in knowledge packs.

## Delivery order

### Phase 1 — plans and inventory
- Add CRUD for learning plans.
- Show plan milestones and status in the UI.
- Add a proposal queue with approve/reject actions.
- Keep all changes local and exportable.

### Phase 2 — importable knowledge packs
- Support plain text, Markdown, PDF text extraction, CSV, and JSON with size limits.
- Preserve source and content hashes.
- Add local full-text search first; introduce embeddings only as an optional local enhancement.
- Add inspect, export, disable, and delete controls.

### Phase 3 — learning loop
- Generate draft tests from a plan and pack.
- Run evaluations against the configured model.
- Compare before/after results and show citations to the relevant pack items.
- Suggest missing material, but require owner approval before activation.

### Phase 4 — skill packs
- Define a strict manifest and typed tool interfaces.
- Add sandboxed test execution and a risk/permission review screen.
- Start with read-only capabilities. Add write capabilities one by one with explicit approvals.
- Keep skills separate from knowledge packs.

### Phase 5 — background execution and devices
- Run queued import/evaluation jobs in the existing worker.
- Persist progress, logs, retries, and cancellation.
- Later pair Android and Windows with authenticated, encrypted sync.
- Keep local-only operation useful when no cloud service is available.

## Acceptance criteria

- The owner can add a learning plan in Czech and edit it later.
- The owner can attach/import a dataset and see its source, type, and import status.
- No unapproved pack influences normal answers.
- Answers using a pack can identify the supporting source items.
- A proposed improvement never activates itself.
- Evaluations are repeatable and show pass/fail evidence.
- Disabling or deleting a pack removes it from retrieval.
- No model-generated content can grant permissions or run arbitrary commands.
- Plans, pack metadata, and approved user data can be exported and restored.

## Relationship to the current branch

The existing `micro-helper` branch already has a local SQLite foundation, editable memories/preferences, a constrained tool registry, and a persistent worker for text-draft tasks. Those are useful foundations, but the learning plans, knowledge-pack importer/index, evaluation loop, approval UI, and safe skill-pack runtime described here are **not implemented yet**. The current worker's `agent.draft` task is not a general autonomous learning agent.
