"""Versioned, user-controlled learning plans. Plans store intent, not executable authority."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/v1/learning/plans", tags=["learning"])


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PlanInput(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    objective: str = Field(min_length=1, max_length=4000)
    status: Literal["draft", "active", "paused"] = "draft"
    steps: list[str] = Field(default_factory=list, max_length=40)
    sources: list[str] = Field(default_factory=list, max_length=40)


def _db():
    # Import lazily to avoid an API/router import cycle.
    from micro_helper.api import database
    return database()


def _decode(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "objective": row["objective"],
        "status": row["status"],
        "steps": json.loads(row["steps_json"]),
        "sources": json.loads(row["sources_json"]),
        "version": row["version"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


@router.get("")
async def list_plans():
    with _db() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS learning_plans (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, objective TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('draft','active','paused')),
            steps_json TEXT NOT NULL, sources_json TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""")
        rows = db.execute("SELECT * FROM learning_plans ORDER BY updated_at DESC").fetchall()
    return {"plans": [_decode(row) for row in rows]}


@router.post("", status_code=201)
async def create_plan(payload: PlanInput):
    with _db() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS learning_plans (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, objective TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('draft','active','paused')),
            steps_json TEXT NOT NULL, sources_json TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""")
        stamp, plan_id = now(), str(uuid.uuid4())
        db.execute(
            "INSERT INTO learning_plans VALUES (?,?,?,?,?,?,1,?,?)",
            (plan_id, payload.title.strip(), payload.objective.strip(), payload.status,
             json.dumps(payload.steps, ensure_ascii=False), json.dumps(payload.sources, ensure_ascii=False), stamp, stamp),
        )
        row = db.execute("SELECT * FROM learning_plans WHERE id=?", (plan_id,)).fetchone()
        db.commit()
    return _decode(row)


@router.get("/{plan_id}")
async def get_plan(plan_id: str):
    with _db() as db:
        row = db.execute("SELECT * FROM learning_plans WHERE id=?", (plan_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Učební plán nebyl nalezen.")
    return _decode(row)


@router.put("/{plan_id}")
async def update_plan(plan_id: str, payload: PlanInput):
    with _db() as db:
        cursor = db.execute(
            """UPDATE learning_plans SET title=?, objective=?, status=?, steps_json=?,
            sources_json=?, version=version+1, updated_at=? WHERE id=?""",
            (payload.title.strip(), payload.objective.strip(), payload.status,
             json.dumps(payload.steps, ensure_ascii=False), json.dumps(payload.sources, ensure_ascii=False), now(), plan_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Učební plán nebyl nalezen.")
        row = db.execute("SELECT * FROM learning_plans WHERE id=?", (plan_id,)).fetchone()
        db.commit()
    return _decode(row)


@router.delete("/{plan_id}")
async def delete_plan(plan_id: str):
    with _db() as db:
        cursor = db.execute("DELETE FROM learning_plans WHERE id=?", (plan_id,))
        db.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Učební plán nebyl nalezen.")
    return {"deleted": True, "id": plan_id}
