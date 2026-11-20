"""Runtime proof that every direct REST mutation fails closed without a fresh token.

The route matrix is compared with the actual FastAPI router so a newly added
state-changing endpoint cannot silently escape this test suite.
"""
import json

from fastapi.testclient import TestClient
import pytest

import micro_helper.api as api


raw_client = TestClient(
    api.app,
    base_url="http://127.0.0.1:8000",
    client=("127.0.0.1", 8000),
)

STAMP = "2026-11-20T00:00:00+00:00"
PRIVATE_MARKER = "PRIVATE-REST-GUARD-MUST-NOT-ENTER-AUDIT"


# (method, route template, concrete request path, valid request body)
MUTATIONS = [
    (
        "POST", "/v1/tasks", "/v1/tasks",
        {"title": PRIVATE_MARKER, "input_text": "draft", "confirmed": True},
    ),
    (
        "POST", "/v1/tasks/{task_id}/cancel", "/v1/tasks/guard-task/cancel",
        {"confirmed": True},
    ),
    (
        "POST", "/v1/learning-plans", "/v1/learning-plans",
        {"title": PRIVATE_MARKER, "goal": "goal", "steps": ["step"], "confirmed": True},
    ),
    (
        "PATCH", "/v1/learning-plans/{plan_id}/status", "/v1/learning-plans/guard-plan/status",
        {"status": "paused", "confirmed": True},
    ),
    (
        "DELETE", "/v1/learning-plans/{plan_id}", "/v1/learning-plans/guard-plan",
        {"confirmed": True},
    ),
    (
        "PUT", "/v1/profile", "/v1/profile",
        {"agent_name": PRIVATE_MARKER, "language": "cs-CZ", "style": "friendly", "confirmed": True},
    ),
    (
        "POST", "/v1/memories", "/v1/memories",
        {"content": PRIVATE_MARKER, "category": "context", "confirmed": True},
    ),
    (
        "PUT", "/v1/memories/{memory_id}", "/v1/memories/1",
        {"content": PRIVATE_MARKER, "category": "context", "confirmed": True},
    ),
    (
        "DELETE", "/v1/memories/{memory_id}", "/v1/memories/1",
        {"confirmed": True},
    ),
    (
        "POST", "/v1/preferences", "/v1/preferences",
        {"category": "security", "preference": "keep", "value": PRIVATE_MARKER, "confirmed": True},
    ),
    (
        "DELETE", "/v1/preferences/{preference_id}", "/v1/preferences/1",
        {"confirmed": True},
    ),
    (
        "DELETE", "/v1/conversations", "/v1/conversations",
        {"confirmed": True},
    ),
    (
        "POST", "/v1/backup/restore", "/v1/backup/restore",
        {"backup": {}, "confirm_replace": True, "confirmed": True},
    ),
]


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "DATABASE_PATH", tmp_path / "rest-guard-tests.sqlite3")
    with api.database() as db:
        db.execute(
            "UPDATE profile SET agent_name='Protected profile', language='cs-CZ', style='friendly' WHERE id=1"
        )
        db.execute(
            "INSERT INTO memories(id, content, category, created_at) VALUES (1, 'Protected memory', 'context', ?)",
            (STAMP,),
        )
        db.execute(
            """INSERT INTO messages(id, role, content, created_at)
               VALUES (1, 'user', 'Protected conversation', ?)""",
            (STAMP,),
        )
        db.execute(
            """INSERT INTO tasks(id, kind, title, input_text, status, created_at, updated_at)
               VALUES ('guard-task', 'agent.draft', 'Protected task', 'Keep', 'queued', ?, ?)""",
            (STAMP, STAMP),
        )
        db.execute(
            """INSERT INTO learning_plans(id, title, goal, steps_json, status, created_at, updated_at)
               VALUES ('guard-plan', 'Protected plan', 'Keep', '["step"]', 'active', ?, ?)""",
            (STAMP, STAMP),
        )
        db.execute(
            """INSERT INTO preferences(id, category, preference, value, source, updated_at)
               VALUES (1, 'security', 'keep', 'Protected preference', 'user', ?)""",
            (STAMP,),
        )
        db.commit()


def snapshot_user_state():
    tables = ("profile", "memories", "messages", "tasks", "learning_plans", "preferences")
    with api.database() as db:
        return {
            table: [
                tuple(row)
                for row in db.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
            ]
            for table in tables
        }


def test_runtime_matrix_covers_every_direct_state_changing_route():
    separately_gated = {
        ("POST", "/v1/chat"),  # Explicit Send is the sole built-in low-risk grant.
        ("POST", "/v1/actions/confirm"),
        ("POST", "/v1/tools/{tool_id}/confirm"),
        ("POST", "/v1/tools/{tool_id}/execute"),
    }
    actual = set()
    for route in api.app.routes:
        if not getattr(route, "path", "").startswith("/v1/"):
            continue
        for method in (getattr(route, "methods", set()) or set()) & {"POST", "PUT", "PATCH", "DELETE"}:
            key = (method, route.path)
            if key not in separately_gated:
                actual.add(key)

    covered = {(method, template) for method, template, _, _ in MUTATIONS}
    assert covered == actual, (
        f"Runtime confirmation matrix mismatch; missing={sorted(actual - covered)}, "
        f"stale={sorted(covered - actual)}"
    )


@pytest.mark.parametrize(
    "method,route_template,request_path,payload",
    MUTATIONS,
    ids=[f"{method.lower()}-{template}" for method, template, _, _ in MUTATIONS],
)
def test_direct_rest_mutation_rejects_forged_boolean_and_preserves_data(
    method, route_template, request_path, payload
):
    before = snapshot_user_state()

    response = raw_client.request(method, request_path, json=payload)

    assert response.status_code == 403, (
        f"{method} {route_template} must require a server-issued, action-bound token; "
        f"received {response.status_code}: {response.text}"
    )
    assert snapshot_user_state() == before, f"{method} {route_template} changed persisted user data"

    with api.database() as db:
        audit = [
            dict(row)
            for row in db.execute(
                "SELECT tool_id, capability, operation, target, decision, reason, outcome "
                "FROM tool_audit ORDER BY id"
            ).fetchall()
        ]
    assert audit, "a rejected mutation must leave an audit event"
    assert audit[-1]["outcome"] == "confirmation_rejected"
    assert PRIVATE_MARKER not in json.dumps(audit, ensure_ascii=False)
