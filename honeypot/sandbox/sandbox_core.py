"""Sandbox execution utilities for the Quantum Deception Nexus honeypot."""
from __future__ import annotations

import io
import sqlite3
import time
from contextlib import redirect_stdout
from pathlib import Path
from typing import Dict, Any

DEFAULT_DB_PATH = Path("quantum_nexus.db")

SAFE_BUILTINS = {
    "abs": abs,
    "min": min,
    "max": max,
    "sum": sum,
    "len": len,
    "range": range,
    "enumerate": enumerate,
}


class SandboxCore:
    """Executes untrusted snippets in a constrained Python environment."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path or DEFAULT_DB_PATH)
        self._ensure_tables()

    def execute_code(self, fingerprint_hash: str, code: str) -> Dict[str, Any]:
        start_time = time.perf_counter()
        stdout_buffer = io.StringIO()
        success = True
        error_message = None
        local_env: Dict[str, Any] = {}

        try:
            compiled = compile(code, "<sandbox>", "exec")
            with redirect_stdout(stdout_buffer):
                exec(compiled, {"__builtins__": SAFE_BUILTINS.copy()}, local_env)
        except Exception as exc:  # pragma: no cover - defensive
            success = False
            error_message = str(exc)

        cpu_time = time.perf_counter() - start_time
        output = stdout_buffer.getvalue().strip()
        memory_kb = len(code.encode("utf-8")) / 1024.0

        result = {
            "fingerprint_hash": fingerprint_hash,
            "success": success,
            "output": output,
            "error": error_message,
            "cpu_time": round(cpu_time, 4),
            "memory_kb": round(memory_kb, 4),
        }

        self._persist_run(result, code)
        return result

    # ------------------------------------------------------------------
    def _ensure_tables(self) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sandbox_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fingerprint_hash TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    output TEXT,
                    error TEXT,
                    cpu_time REAL,
                    memory_kb REAL,
                    code TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def _persist_run(self, result: Dict[str, Any], code: str) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO sandbox_runs (
                    fingerprint_hash, success, output, error, cpu_time, memory_kb, code
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result["fingerprint_hash"],
                    1 if result["success"] else 0,
                    result["output"],
                    result["error"],
                    result["cpu_time"],
                    result["memory_kb"],
                    code,
                ),
            )
            conn.commit()
        finally:
            conn.close()


__all__ = ["SandboxCore"]
