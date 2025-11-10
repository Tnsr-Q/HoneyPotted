"""Verification routines for the Quantum Deception Nexus honeypot."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Dict, Any

DEFAULT_DB_PATH = Path("quantum_nexus.db")

# Sandbox scoring constants
BASE_SCORE_SUCCESS = 0.7  # Base score for successful sandbox execution
BASE_SCORE_FAILURE = 0.1  # Base score for failed sandbox execution
MAX_CPU_TIME_SECONDS = 30.0  # Maximum expected CPU time before penalty applies
MAX_CPU_PENALTY = 0.4  # Maximum penalty for excessive CPU time
MAX_MEMORY_KB = 51200.0  # Maximum expected memory usage (50 MB) before penalty applies
MAX_MEMORY_PENALTY = 0.3  # Maximum penalty for excessive memory usage


class VerificationAPI:
    """Aggregates evidence from multiple subsystems to verify a bot."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path or DEFAULT_DB_PATH)
        self._ensure_tables()

    def verify_bot(self, fingerprint_hash: str, evidence: Dict[str, Any]) -> Dict[str, Any]:
        fingerprint = self._load_fingerprint(fingerprint_hash)
        challenge_result = self._load_latest_challenge(fingerprint_hash)
        sandbox_result = self._load_latest_sandbox(fingerprint_hash)

        components = {
            "fingerprint": fingerprint.get("detection_score", 0.0),
            "challenge": challenge_result.get("score", 0.0),
            "sandbox": sandbox_result.get("score", 0.0),
            "behaviour": float(evidence.get("behaviour_score", 0.0)),
        }

        confidence = self._calculate_confidence(components)
        verified = confidence >= 0.6

        result = {
            "fingerprint_hash": fingerprint_hash,
            "verified": verified,
            "confidence": round(confidence, 4),
            "components": components,
        }

        self._persist_verification(fingerprint_hash, result)
        return result

    # ------------------------------------------------------------------
    def _ensure_tables(self) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS verification_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fingerprint_hash TEXT NOT NULL,
                    result TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def _load_fingerprint(self, fingerprint_hash: str) -> Dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT detection_score FROM bot_tracking WHERE fingerprint_hash = ?",
                (fingerprint_hash,),
            )
            row = cursor.fetchone()
            return {"detection_score": float(row["detection_score"]) if row else 0.0}
        finally:
            conn.close()

    def _load_latest_challenge(self, fingerprint_hash: str) -> Dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT score FROM challenge_responses
                WHERE fingerprint_hash = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (fingerprint_hash,),
            )
            row = cursor.fetchone()
            return {"score": float(row["score"]) if row else 0.0}
        finally:
            conn.close()

    def _load_latest_sandbox(self, fingerprint_hash: str) -> Dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT success, cpu_time, memory_kb
                FROM sandbox_runs
                WHERE fingerprint_hash = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (fingerprint_hash,),
            )
            row = cursor.fetchone()
            if not row:
                return {"score": 0.0}
            base = BASE_SCORE_SUCCESS if row["success"] else BASE_SCORE_FAILURE
            resource_penalty = min((row["cpu_time"] or 0) / MAX_CPU_TIME_SECONDS, MAX_CPU_PENALTY)
            memory_penalty = min((row["memory_kb"] or 0) / MAX_MEMORY_KB, MAX_MEMORY_PENALTY)
            return {"score": max(0.0, base - resource_penalty - memory_penalty)}
        finally:
            conn.close()

    def _calculate_confidence(self, components: Dict[str, float]) -> float:
        weights = {
            "fingerprint": 0.45,
            "challenge": 0.25,
            "sandbox": 0.2,
            "behaviour": 0.1,
        }
        return sum(components.get(key, 0.0) * weight for key, weight in weights.items())

    def _persist_verification(self, fingerprint_hash: str, result: Dict[str, Any]) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO verification_results (fingerprint_hash, result)
                VALUES (?, ?)
                """,
                (fingerprint_hash, json.dumps(result)),
            )
            conn.commit()
        finally:
            conn.close()


__all__ = ["VerificationAPI"]
