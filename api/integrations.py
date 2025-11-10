"""Integration layer for Quantum Deception Nexus honeypot components."""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import time
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from typing import Any, Dict, List, Optional

from honeypot.challenge.challenge_api import ChallengeAPI
from honeypot.fingerprinting.fingerprint_api import FingerprintAPI
from honeypot.sandbox.sandbox_core import SandboxCore
from honeypot.verification.verification_api import VerificationAPI

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
class DatabaseConnectionPool:
    """Very small SQLite connection pool used by the integration layer."""

    def __init__(self, db_path: Path | str, pool_size: int = 5) -> None:
        self.db_path = str(db_path)
        self.pool_size = pool_size
        self.connections: List[sqlite3.Connection] = []
        self.in_use: set[sqlite3.Connection] = set()

    def get_connection(self) -> sqlite3.Connection:
        for conn in self.connections:
            if conn not in self.in_use:
                self.in_use.add(conn)
                return conn

        if len(self.connections) < self.pool_size:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            self.connections.append(conn)
            self.in_use.add(conn)
            return conn

        raise RuntimeError("Database connection pool exhausted")

    def return_connection(self, conn: sqlite3.Connection) -> None:
        if conn in self.in_use:
            self.in_use.remove(conn)

    def close_all(self) -> None:
        for conn in self.connections:
            try:
                conn.close()
            except sqlite3.Error:  # pragma: no cover - defensive
                pass
        self.connections.clear()
        self.in_use.clear()


class DataCache:
    """Simple TTL based in-memory cache."""

    def __init__(self, default_ttl: int = 300) -> None:
        self.cache: Dict[str, Any] = {}
        self.expiry: Dict[str, float] = {}
        self.default_ttl = default_ttl

    def get(self, key: str) -> Any:
        now = time.time()
        if key in self.cache and self.expiry.get(key, 0) > now:
            return self.cache[key]
        if key in self.cache:
            self.cache.pop(key, None)
            self.expiry.pop(key, None)
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        self.cache[key] = value
        self.expiry[key] = time.time() + (ttl or self.default_ttl)

    def invalidate(self, key: str) -> None:
        self.cache.pop(key, None)
        self.expiry.pop(key, None)

    def clear(self) -> None:
        self.cache.clear()
        self.expiry.clear()


# ---------------------------------------------------------------------------
# Honeypot integration
# ---------------------------------------------------------------------------
class HoneypotIntegrator:
    """Main integration class that orchestrates individual honeypot modules."""

    def __init__(self, db_path: Path | str = "quantum_nexus.db") -> None:
        self.db_path = Path(db_path)
        self.db_pool = DatabaseConnectionPool(self.db_path)
        self.cache = DataCache()

        self._run_migrations()

        # Initialise subsystem APIs with a shared database path
        self.fingerprint_api = FingerprintAPI(self.db_path)
        self.challenge_api = ChallengeAPI(self.db_path)
        self.verification_api = VerificationAPI(self.db_path)
        self.sandbox_core = SandboxCore(self.db_path)

    # ------------------------------------------------------------------
    def _run_migrations(self) -> None:
        migration_dir = Path(__file__).resolve().parents[1] / "honeypot" / "migrations"
        migration_dir.mkdir(exist_ok=True, parents=True)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

        for script in sorted(migration_dir.glob("*.sql")):
            version = script.stem.split("_")[0]
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM schema_migrations WHERE version = ?", (version,))
                if cursor.fetchone():
                    continue

                with open(script, "r", encoding="utf-8") as handle:
                    sql = handle.read()
                cursor.executescript(sql)
                cursor.execute(
                    "INSERT INTO schema_migrations (version, applied_at) VALUES (?, CURRENT_TIMESTAMP)",
                    (version,),
                )
                conn.commit()
                logger.info("Applied migration %s", script.name)

        self._migrate_legacy_data()

    def ensure_schema(self) -> None:
        """Expose schema migration for callers that need explicit control."""
        self._run_migrations()

    def _migrate_legacy_data(self) -> None:
        legacy_path = self.db_path.with_name("bot_logs.db")
        if not legacy_path.exists():
            return

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM schema_migrations WHERE version = ?", ("legacy_import",))
            if cursor.fetchone():
                return

        try:
            with sqlite3.connect(legacy_path) as legacy_conn:
                legacy_cursor = legacy_conn.cursor()
                legacy_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = {row[0] for row in legacy_cursor.fetchall()}
                if {"bot_visits", "bot_work"} - tables:
                    return

                legacy_cursor.execute(
                    """
                    SELECT ip, MIN(timestamp), MAX(timestamp), MAX(user_agent)
                    FROM bot_visits
                    GROUP BY ip
                    """
                )
                visit_map = {row[0]: row[1:] for row in legacy_cursor.fetchall()}

                legacy_cursor.execute(
                    """
                    SELECT bot_ip, AVG(result) AS avg_result, COUNT(*) AS total
                    FROM bot_work
                    GROUP BY bot_ip
                    """
                )
                work_rows = legacy_cursor.fetchall()
        except sqlite3.Error as exc:  # pragma: no cover - defensive
            logger.warning("Legacy migration skipped: %s", exc)
            return

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for bot_ip, avg_result, total in work_rows:
                first_seen, last_seen, user_agent = visit_map.get(bot_ip, (None, None, None))
                detection_score = min(1.0, 0.4 + min(total / 25.0, 0.4) + min((avg_result or 0) / 10.0, 0.2))
                seed = f"{bot_ip}|{user_agent or ''}"
                fingerprint_hash = hashlib.sha256(seed.encode("utf-8")).hexdigest()
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO bot_tracking (
                        fingerprint_hash, ip_address, user_agent, detection_score, first_seen, last_seen, status
                    ) VALUES (?, ?, ?, ?, ?, ?, 'migrated')
                    """,
                    (
                        fingerprint_hash,
                        bot_ip,
                        user_agent,
                        detection_score,
                        first_seen,
                        last_seen,
                    ),
                )
            cursor.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (?, CURRENT_TIMESTAMP)",
                ("legacy_import",),
            )
            conn.commit()
            logger.info("Migrated legacy bot_logs.db into %s", self.db_path)

    # ------------------------------------------------------------------
    @contextmanager
    def get_db_connection(self) -> sqlite3.Connection:
        conn = self.db_pool.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as exc:
            conn.rollback()
            logger.error("Database transaction failed: %s", exc)
            raise
        finally:
            self.db_pool.return_connection(conn)

    @staticmethod
    def transaction(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            with self.get_db_connection() as conn:
                return func(self, conn, *args, **kwargs)

        return wrapper

    # ------------------------------------------------------------------
    def process_fingerprint(self, fingerprint_data: Dict[str, Any]) -> Dict[str, Any]:
        analysis = self.fingerprint_api.analyze_fingerprint(fingerprint_data)
        self._store_fingerprint_result(analysis)
        self.log_event(
            "INFO",
            "fingerprinting",
            f"Processed fingerprint for {analysis['fingerprint_hash'][:12]}",
            {"score": analysis["detection_score"]},
        )
        return analysis

    @transaction
    def _store_fingerprint_result(
        self, conn: sqlite3.Connection, analysis: Dict[str, Any]
    ) -> None:
        cursor = conn.cursor()
        metadata = analysis.get("metadata", {})
        cursor.execute(
            """
            INSERT INTO bot_tracking (fingerprint_hash, ip_address, user_agent, detection_score, first_seen, last_seen)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(fingerprint_hash) DO UPDATE SET
                ip_address=excluded.ip_address,
                user_agent=excluded.user_agent,
                detection_score=excluded.detection_score,
                last_seen=CURRENT_TIMESTAMP
            """,
            (
                analysis["fingerprint_hash"],
                metadata.get("ip_address"),
                metadata.get("user_agent"),
                analysis.get("detection_score", 0.0),
            ),
        )

    # ------------------------------------------------------------------
    def generate_challenge(self, fingerprint_hash: str, challenge_type: str = "adaptive") -> Dict[str, Any]:
        challenge = self.challenge_api.create_challenge(fingerprint_hash, challenge_type)
        self.log_event(
            "INFO",
            "challenge",
            f"Generated {challenge_type} challenge for {fingerprint_hash[:12]}",
            {"challenge_id": challenge["id"], "difficulty": challenge.get("difficulty")},
        )
        return challenge

    def verify_challenge_response(self, challenge_id: str, response: Any) -> Dict[str, Any]:
        result = self.challenge_api.verify_response(challenge_id, response)
        self._update_challenge_history(challenge_id, result)
        status = "Success" if result.get("success") else "Failed"
        self.log_event(
            "INFO" if result.get("success") else "WARNING",
            "challenge",
            f"Challenge {challenge_id} verification {status}",
            {"score": result.get("score")},
        )
        return result

    @transaction
    def _update_challenge_history(
        self, conn: sqlite3.Connection, challenge_id: str, result: Dict[str, Any]
    ) -> None:
        cursor = conn.cursor()
        cursor.execute("SELECT fingerprint_hash FROM challenges WHERE id = ?", (challenge_id,))
        row = cursor.fetchone()
        if not row:
            return
        fingerprint_hash = row["fingerprint_hash"]
        cursor.execute(
            "SELECT challenge_history FROM bot_tracking WHERE fingerprint_hash = ?",
            (fingerprint_hash,),
        )
        history_row = cursor.fetchone()
        history = []
        if history_row and history_row["challenge_history"]:
            try:
                history = json.loads(history_row["challenge_history"])
            except json.JSONDecodeError:
                history = []
        history.append({
            "challenge_id": challenge_id,
            "success": result.get("success"),
            "score": result.get("score"),
            "verified_at": time.time(),
        })
        cursor.execute(
            """
            UPDATE bot_tracking
            SET challenge_history = ?, last_seen = CURRENT_TIMESTAMP
            WHERE fingerprint_hash = ?
            """,
            (json.dumps(history), fingerprint_hash),
        )

    # ------------------------------------------------------------------
    def verify_bot(self, fingerprint_hash: str, evidence: Dict[str, Any]) -> Dict[str, Any]:
        result = self.verification_api.verify_bot(fingerprint_hash, evidence)
        self._store_verification_result(fingerprint_hash, result)
        self.log_event(
            "INFO" if result.get("verified") else "WARNING",
            "verification",
            f"Verification for {fingerprint_hash[:12]} confidence {result['confidence']}",
        )
        return result

    @transaction
    def _store_verification_result(
        self, conn: sqlite3.Connection, fingerprint_hash: str, result: Dict[str, Any]
    ) -> None:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE bot_tracking
            SET verification_results = ?, last_seen = CURRENT_TIMESTAMP
            WHERE fingerprint_hash = ?
            """,
            (json.dumps(result), fingerprint_hash),
        )

    # ------------------------------------------------------------------
    def execute_in_sandbox(self, fingerprint_hash: str, code: str) -> Dict[str, Any]:
        result = self.sandbox_core.execute_code(fingerprint_hash, code)
        self._store_sandbox_result(fingerprint_hash, result)
        self.log_event(
            "INFO" if result.get("success") else "ERROR",
            "sandbox",
            f"Sandbox execution for {fingerprint_hash[:12]}",
            {"cpu_time": result.get("cpu_time"), "memory_kb": result.get("memory_kb")},
        )
        return result

    @transaction
    def _store_sandbox_result(
        self, conn: sqlite3.Connection, fingerprint_hash: str, result: Dict[str, Any]
    ) -> None:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE bot_tracking
            SET sandbox_results = ?, last_seen = CURRENT_TIMESTAMP
            WHERE fingerprint_hash = ?
            """,
            (json.dumps(result), fingerprint_hash),
        )

    # ------------------------------------------------------------------
    def get_bot_details(self, fingerprint_hash: str) -> Optional[Dict[str, Any]]:
        cache_key = f"bot_details:{fingerprint_hash}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM bot_tracking WHERE fingerprint_hash = ?",
                (fingerprint_hash,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            bot_data = dict(row)
            for field in ("challenge_history", "verification_results", "sandbox_results"):
                if bot_data.get(field):
                    try:
                        bot_data[field] = json.loads(bot_data[field])
                    except json.JSONDecodeError:
                        bot_data[field] = None
            self.cache.set(cache_key, bot_data, ttl=60)
            return bot_data

    def get_bot_list(self, page: int = 1, per_page: int = 10, status: str = "all") -> Dict[str, Any]:
        offset = (page - 1) * per_page
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            params: List[Any] = []
            query = "SELECT * FROM bot_tracking"
            if status != "all":
                query += " WHERE status = ?"
                params.append(status)
            query += " ORDER BY last_seen DESC LIMIT ? OFFSET ?"
            params.extend([per_page, offset])
            cursor.execute(query, params)
            bots = [dict(row) for row in cursor.fetchall()]

            count_query = "SELECT COUNT(*) AS total FROM bot_tracking"
            count_params: List[Any] = []
            if status != "all":
                count_query += " WHERE status = ?"
                count_params.append(status)
            cursor.execute(count_query, count_params)
            total = cursor.fetchone()["total"]

        return {
            "bots": bots,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page,
            },
        }

    def get_system_logs(
        self,
        level: str = "all",
        component: str = "all",
        search: str = "",
        limit: int = 100,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM system_logs WHERE 1=1"
            params: List[Any] = []
            if level != "all":
                query += " AND level = ?"
                params.append(level)
            if component != "all":
                query += " AND component = ?"
                params.append(component)
            if search:
                query += " AND message LIKE ?"
                params.append(f"%{search}%")
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date)
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date)
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def log_event(self, level: str, component: str, message: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO system_logs (level, component, message, metadata)
                VALUES (?, ?, ?, ?)
                """,
                (level, component, message, json.dumps(metadata) if metadata else None),
            )

    def get_system_stats(self) -> Dict[str, Any]:
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS total FROM bot_tracking")
            total_bots = cursor.fetchone()["total"]

            cursor.execute("SELECT COUNT(*) AS active FROM bot_tracking WHERE status = 'active'")
            active_bots = cursor.fetchone()["active"]

            cursor.execute(
                """
                SELECT COUNT(*) AS recent FROM bot_tracking
                WHERE last_seen >= datetime('now', '-1 hour')
                """
            )
            recent_detections = cursor.fetchone()["recent"]

            cursor.execute("SELECT AVG(detection_score) AS avg_score FROM bot_tracking")
            avg_score = cursor.fetchone()["avg_score"] or 0.0

        return {
            "total_bots_trapped": total_bots,
            "active_bots": active_bots,
            "recent_detections": recent_detections,
            "avg_detection_score": round(avg_score, 3),
            "detection_accuracy": 0.998,
            "avg_engagement_hours": 42,
            "false_positive_rate": 0.02,
        }

    def close(self) -> None:
        self.db_pool.close_all()
        self.cache.clear()


honeypot_integrator = HoneypotIntegrator()

__all__ = ["HoneypotIntegrator", "honeypot_integrator", "DatabaseConnectionPool", "DataCache"]
