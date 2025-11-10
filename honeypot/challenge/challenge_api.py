"""Challenge coordination for the Quantum Deception Nexus honeypot."""

from __future__ import annotations

import json
import secrets
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any

DEFAULT_DB_PATH = Path("quantum_nexus.db")


@dataclass
class Challenge:
    challenge_id: str
    fingerprint_hash: str
    challenge_type: str
    payload: Dict[str, Any]
    difficulty: int

    def as_dict(self) -> Dict[str, Any]:
        return {
            "id": self.challenge_id,
            "fingerprint_hash": self.fingerprint_hash,
            "type": self.challenge_type,
            "payload": self.payload,
            "difficulty": self.difficulty,
            "timeout": self.payload.get("timeout", 180),
        }


class ChallengeAPI:
    """Creates and verifies adaptive challenges for suspected bots."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path or DEFAULT_DB_PATH)
        self._ensure_tables()

    # ------------------------------------------------------------------
    def create_challenge(self, fingerprint_hash: str, challenge_type: str = "adaptive") -> Dict[str, Any]:
        difficulty = self._estimate_difficulty(fingerprint_hash)
        payload = self._build_payload(challenge_type, difficulty)
        challenge = Challenge(
            challenge_id=self._generate_id(),
            fingerprint_hash=fingerprint_hash,
            challenge_type=challenge_type,
            payload=payload,
            difficulty=difficulty,
        )
        self._persist_challenge(challenge)
        return challenge.as_dict()

    def verify_response(self, challenge_id: str, response: Any) -> Dict[str, Any]:
        challenge_row = self._get_challenge(challenge_id)
        if not challenge_row:
            return {"challenge_id": challenge_id, "success": False, "score": 0.0, "reason": "unknown_challenge"}

        expected = challenge_row["payload"]
        success = self._evaluate_response(expected, response)
        score = 1.0 if success else 0.0

        self._persist_response(challenge_row, response, success, score)

        return {
            "challenge_id": challenge_id,
            "success": success,
            "score": score,
            "time_taken": response.get("time_taken", None) if isinstance(response, dict) else None,
        }

    # ------------------------------------------------------------------
    def _ensure_tables(self) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS challenges (
                    id TEXT PRIMARY KEY,
                    fingerprint_hash TEXT NOT NULL,
                    type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    difficulty INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS challenge_responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    challenge_id TEXT NOT NULL,
                    fingerprint_hash TEXT NOT NULL,
                    response TEXT,
                    success INTEGER,
                    score REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def _persist_challenge(self, challenge: Challenge) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO challenges (id, fingerprint_hash, type, payload, difficulty)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    challenge.challenge_id,
                    challenge.fingerprint_hash,
                    challenge.challenge_type,
                    json.dumps(challenge.payload),
                    challenge.difficulty,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def _persist_response(self, challenge_row: sqlite3.Row, response: Any, success: bool, score: float) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO challenge_responses (challenge_id, fingerprint_hash, response, success, score)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    challenge_row["id"],
                    challenge_row["fingerprint_hash"],
                    json.dumps(response, default=str),
                    1 if success else 0,
                    score,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def _generate_id(self) -> str:
        return secrets.token_hex(8)

    def _estimate_difficulty(self, fingerprint_hash: str) -> int:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT detection_score FROM bot_tracking WHERE fingerprint_hash = ?
                """,
                (fingerprint_hash,),
            )
            row = cursor.fetchone()
            if not row:
                return 3
            score = float(row["detection_score"] or 0.5)
            return max(1, min(int(round(score * 5)), 5))
        finally:
            conn.close()

    def _build_payload(self, challenge_type: str, difficulty: int) -> Dict[str, Any]:
        base_timeout = 120 + (difficulty * 30)
        if challenge_type == "math":
            numbers = [secrets.randbelow(50) + 1 for _ in range(3 + difficulty)]
            return {"operation": "sum", "numbers": numbers, "answer": sum(numbers), "timeout": base_timeout}
        if challenge_type == "logic":
            return {
                "operation": "sequence",
                "sequence": [difficulty, difficulty * 2, difficulty * 3],
                "answer": difficulty * 4,
                "timeout": base_timeout,
            }
        # adaptive fallback
        numbers = [secrets.randbelow(20) + 1 for _ in range(4)]
        return {
            "operation": "checksum",
            "numbers": numbers,
            "answer": sum(numbers) % 7,
            "timeout": base_timeout,
        }

    def _get_challenge(self, challenge_id: str) -> sqlite3.Row | None:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM challenges WHERE id = ?", (challenge_id,))
            return cursor.fetchone()
        finally:
            conn.close()

    def _evaluate_response(self, challenge_payload: str, response: Any) -> bool:
        if isinstance(challenge_payload, str):
            payload = json.loads(challenge_payload)
        else:
            payload = challenge_payload

        if not isinstance(response, dict):
            return False

        if payload.get("operation") == "sum":
            return int(response.get("answer", -1)) == int(payload.get("answer", -2))
        if payload.get("operation") == "sequence":
            return int(response.get("answer", -1)) == int(payload.get("answer", -2))
        if payload.get("operation") == "checksum":
            return int(response.get("checksum", -1)) == int(payload.get("answer", -2))
        return False


__all__ = ["ChallengeAPI", "Challenge"]
