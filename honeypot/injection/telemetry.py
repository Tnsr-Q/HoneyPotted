"""Injection telemetry store: immutable evidence capsules + actor aggregates.

Every routed injection produces a replayable evidence capsule and updates a
per-actor profile. The event log is append-only (the application never updates
or deletes rows in ``injection_events``); the ``injection_actors`` table holds
rolled-up state the router reads to make history-based decisions and the
challenge subsystem reads to bias difficulty.

This turns the honeypot into a labeled dataset generator, consistent with the
project's benchmark goal.
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional


@dataclass
class EvidenceCapsule:
    actor_key: str
    timestamp: float
    method: str
    path: str
    risk: float
    action: str
    route_state: str
    families: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    samples: List[str] = field(default_factory=list)
    decoy_session_id: Optional[str] = None
    challenge_id: Optional[str] = None
    canary: Optional[str] = None
    detector_version: str = "layer-a/1"

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS injection_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    actor_key TEXT NOT NULL,
    method TEXT,
    path TEXT,
    risk REAL NOT NULL,
    action TEXT NOT NULL,
    route_state TEXT NOT NULL,
    families TEXT NOT NULL,
    evidence TEXT NOT NULL,
    capsule TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_injection_events_actor ON injection_events(actor_key);
CREATE INDEX IF NOT EXISTS idx_injection_events_ts ON injection_events(ts);

CREATE TABLE IF NOT EXISTS injection_actors (
    actor_key TEXT PRIMARY KEY,
    first_seen REAL NOT NULL,
    last_seen REAL NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    cumulative_score REAL NOT NULL DEFAULT 0,
    max_risk REAL NOT NULL DEFAULT 0,
    decoy_count INTEGER NOT NULL DEFAULT 0,
    families TEXT NOT NULL DEFAULT '[]',
    last_route_state TEXT,
    last_injection_at REAL
);
"""

# route states that count as a genuine injection "attempt" for the profile
_ATTEMPT_STATES = {"DECOY", "DECOY_PLUS_CHALLENGE", "QUARANTINE", "TARPIT"}
_DECOY_STATES = _ATTEMPT_STATES


class InjectionTelemetryStore:
    """SQLite-backed telemetry. Safe to share across threads (per-call conn)."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        conn = self._connect()
        try:
            conn.executescript(_SCHEMA)
            conn.commit()
        finally:
            conn.close()

    def record_capsule(self, capsule: EvidenceCapsule) -> None:
        """Append an immutable event and update the actor's rolled-up profile."""
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT INTO injection_events
                    (ts, actor_key, method, path, risk, action, route_state,
                     families, evidence, capsule)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    capsule.timestamp,
                    capsule.actor_key,
                    capsule.method,
                    capsule.path,
                    capsule.risk,
                    capsule.action,
                    capsule.route_state,
                    json.dumps(capsule.families),
                    json.dumps(capsule.evidence),
                    json.dumps(capsule.to_dict()),
                ),
            )
            self._upsert_actor(conn, capsule)
            conn.commit()
        finally:
            conn.close()

    def _upsert_actor(self, conn: sqlite3.Connection, capsule: EvidenceCapsule) -> None:
        is_attempt = capsule.route_state in _ATTEMPT_STATES
        is_decoy = capsule.route_state in _DECOY_STATES
        row = conn.execute(
            "SELECT * FROM injection_actors WHERE actor_key = ?", (capsule.actor_key,)
        ).fetchone()

        if row is None:
            conn.execute(
                """
                INSERT INTO injection_actors
                    (actor_key, first_seen, last_seen, attempts, cumulative_score,
                     max_risk, decoy_count, families, last_route_state, last_injection_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    capsule.actor_key,
                    capsule.timestamp,
                    capsule.timestamp,
                    1 if is_attempt else 0,
                    capsule.risk,
                    capsule.risk,
                    1 if is_decoy else 0,
                    json.dumps(sorted(set(capsule.families))),
                    capsule.route_state,
                    capsule.timestamp if is_attempt else None,
                ),
            )
            return

        families = sorted(set(json.loads(row["families"]) + capsule.families))
        conn.execute(
            """
            UPDATE injection_actors SET
                last_seen = ?,
                attempts = attempts + ?,
                cumulative_score = cumulative_score + ?,
                max_risk = MAX(max_risk, ?),
                decoy_count = decoy_count + ?,
                families = ?,
                last_route_state = ?,
                last_injection_at = CASE WHEN ? THEN ? ELSE last_injection_at END
            WHERE actor_key = ?
            """,
            (
                capsule.timestamp,
                1 if is_attempt else 0,
                capsule.risk,
                capsule.risk,
                1 if is_decoy else 0,
                json.dumps(families),
                capsule.route_state,
                1 if is_attempt else 0,
                capsule.timestamp,
                capsule.actor_key,
            ),
        )

    def get_profile(self, actor_key: str) -> Dict[str, object]:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM injection_actors WHERE actor_key = ?", (actor_key,)
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return {
                "actor_key": actor_key,
                "attempts": 0,
                "cumulative_score": 0.0,
                "max_risk": 0.0,
                "decoy_count": 0,
                "families": [],
                "last_route_state": None,
                "last_injection_at": None,
            }
        profile = dict(row)
        profile["families"] = json.loads(profile.get("families") or "[]")
        return profile

    def recent_events(self, actor_key: Optional[str] = None, limit: int = 50) -> List[Dict]:
        conn = self._connect()
        try:
            if actor_key:
                rows = conn.execute(
                    "SELECT capsule FROM injection_events WHERE actor_key = ? "
                    "ORDER BY ts DESC LIMIT ?",
                    (actor_key, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT capsule FROM injection_events ORDER BY ts DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        finally:
            conn.close()
        return [json.loads(r["capsule"]) for r in rows]

    @staticmethod
    def now() -> float:
        return time.time()
