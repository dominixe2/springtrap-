"""Bounded background worker for Micro Helper's non-side-effecting AI draft tasks."""
from __future__ import annotations

import argparse
import os
import time

import httpx

from micro_helper.api import OLLAMA_URL, database, utc_now


def run_once() -> bool:
    """Claim and process at most one queued task. Returns whether work was found."""
    with database() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT * FROM tasks WHERE status='queued' ORDER BY created_at LIMIT 1"
        ).fetchone()
        if row is None:
            db.commit()
            return False
        now = utc_now()
        db.execute(
            "UPDATE tasks SET status='running', started_at=?, updated_at=? WHERE id=? AND status='queued'",
            (now, now, row["id"]),
        )
        db.commit()

    try:
        if row["kind"] != "agent.draft":
            raise ValueError("Unsupported task kind.")
        response = httpx.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": os.getenv("MICRO_HELPER_MODEL", "llama3.2"),
                "stream": False,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Jsi Micro Helper. Vytvoř užitečný návrh v češtině. "
                            "Pouze připrav textový návrh. Neprováděj externí akce, "
                            "nepředstírej přístup k souborům, internetu ani zařízením."
                        ),
                    },
                    {"role": "user", "content": row["input_text"]},
                ],
            },
            timeout=180,
        )
        response.raise_for_status()
        result = response.json().get("message", {}).get("content", "")
        if not isinstance(result, str) or not result.strip():
            raise RuntimeError("Model returned an empty result.")
        with database() as db:
            now = utc_now()
            db.execute(
                "UPDATE tasks SET status='completed', result=?, error=NULL, updated_at=?, finished_at=? "
                "WHERE id=? AND status='running'",
                (result.strip(), now, now, row["id"]),
            )
            db.commit()
    except Exception as exc:
        with database() as db:
            now = utc_now()
            db.execute(
                "UPDATE tasks SET status='failed', error=?, updated_at=?, finished_at=? "
                "WHERE id=? AND status='running'",
                (str(exc)[:1000], now, now, row["id"]),
            )
            db.commit()
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Micro Helper bounded task worker")
    parser.add_argument("--interval", type=float, default=5.0, help="Polling interval in seconds")
    parser.add_argument("--once", action="store_true", help="Process at most one task and exit")
    args = parser.parse_args()
    if args.once:
        run_once()
        return
    try:
        while True:
            if not run_once():
                time.sleep(max(1.0, args.interval))
    except KeyboardInterrupt:
        print("Micro Helper worker stopped.")


if __name__ == "__main__":
    main()
