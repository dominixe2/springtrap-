"""Regression tests for the persistent local-authentication rate limiter."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

import micro_helper.api as api


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def isolated_rate_limit_database(tmp_path, monkeypatch):
    database_path = tmp_path / "auth-rate-limit.sqlite3"
    monkeypatch.setattr(api, "DATABASE_PATH", database_path)
    with api.database() as db:
        db.execute("DELETE FROM local_auth_failures")
        db.commit()
    return database_path


def reserve_attempt_in_fresh_process(database_path: Path) -> subprocess.CompletedProcess[str]:
    """Run the real limiter in a new interpreter against the same SQLite file."""
    environment = os.environ.copy()
    source_root = str(REPOSITORY_ROOT / "src")
    existing_python_path = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = os.pathsep.join(
        value for value in (source_root, existing_python_path) if value
    )
    environment["MICRO_HELPER_DB"] = str(database_path)

    script = (
        "from micro_helper.api import _reserve_auth_attempt\n"
        "raise SystemExit(0 if _reserve_auth_attempt('loopback') else 23)\n"
    )
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPOSITORY_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


def test_login_lockout_survives_a_fresh_python_process(isolated_rate_limit_database):
    # Four reservations in this process leave exactly one permitted attempt.
    for _ in range(api.AUTH_FAILURE_LIMIT - 1):
        assert api._reserve_auth_attempt("loopback") is True

    # A new interpreter can consume the fifth attempt from the same SQLite DB.
    allowed = reserve_attempt_in_fresh_process(isolated_rate_limit_database)
    assert allowed.returncode == 0, allowed.stderr

    # Another new interpreter must observe the persisted lockout.
    blocked = reserve_attempt_in_fresh_process(isolated_rate_limit_database)
    assert blocked.returncode == 23, blocked.stderr

    with api.database() as db:
        row = db.execute(
            "SELECT attempts FROM local_auth_failures WHERE client_key='loopback'"
        ).fetchone()
    assert row is not None
    assert row["attempts"] == api.AUTH_FAILURE_LIMIT


def test_rate_limit_window_expires_without_weakening_clock_rollback(
    isolated_rate_limit_database, monkeypatch
):
    clock = [1_000.0]
    monkeypatch.setattr(api.time, "time", lambda: clock[0])

    for _ in range(api.AUTH_FAILURE_LIMIT):
        assert api._reserve_auth_attempt("loopback") is True
    assert api._reserve_auth_attempt("loopback") is False

    # A backwards wall-clock adjustment must not reset the active lockout.
    clock[0] -= 1
    assert api._reserve_auth_attempt("loopback") is False

    # At the exact end of the 15-minute window a new window starts atomically.
    clock[0] = 1_000.0 + api.AUTH_FAILURE_WINDOW_SECONDS
    assert api._reserve_auth_attempt("loopback") is True

    with api.database() as db:
        row = db.execute(
            "SELECT window_started_at, attempts "
            "FROM local_auth_failures WHERE client_key='loopback'"
        ).fetchone()
    assert row is not None
    assert row["window_started_at"] == clock[0]
    assert row["attempts"] == 1
