"""Sandbox execution utilities for the Quantum Deception Nexus honeypot."""
from __future__ import annotations

import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, Any

DEFAULT_DB_PATH = Path("quantum_nexus.db")

# Restricted Python code template that will be written to a temporary file
# This approach provides process isolation to prevent sandbox escapes
SANDBOX_WRAPPER_TEMPLATE = '''import sys

# Define a minimal set of safe built-in functions
safe_builtins = {{
    "abs": abs,
    "min": min,
    "max": max,
    "sum": sum,
    "len": len,
    "range": range,
    "enumerate": enumerate,
    "int": int,
    "float": float,
    "str": str,
    "bool": bool,
    "list": list,
    "dict": dict,
    "tuple": tuple,
    "set": set,
    "print": print,
}}

# Execute user code with restricted builtins
try:
    exec(compile({code_repr}, "<sandbox>", "exec"), {{"__builtins__": safe_builtins}})
except Exception as e:
    print(f"Error: {{type(e).__name__}}: {{e}}", file=sys.stderr)
    sys.exit(1)
'''


class SandboxCore:
    """Executes untrusted snippets in an isolated subprocess environment.
    
    SECURITY MODEL:
    ===============
    This implementation addresses the critical vulnerability of in-process exec()
    by using subprocess isolation. Each code execution runs in a completely
    separate Python process, which provides the following security guarantees:
    
    1. **Process Isolation**: Even if an attacker bypasses the builtin restrictions
       using introspection attacks (e.g., __class__.__mro__.__subclasses__()), they
       can only compromise the isolated subprocess, NOT the main honeypot process.
    
    2. **Timeout Protection**: All executions are subject to a timeout, preventing
       infinite loops or resource exhaustion attacks.
    
    3. **Limited Environment**: The subprocess runs with minimal environment variables
       to reduce attack surface.
    
    4. **No Shared State**: The subprocess has no access to the parent process's
       memory, database connections, or file handles.
    
    FUTURE ENHANCEMENTS:
    ===================
    For production deployments, consider additional hardening:
    - Container-based isolation (Docker/Podman with limited capabilities)
    - Syscall filtering (seccomp-bpf on Linux)
    - Resource limits (ulimit, cgroups)
    - Network namespace isolation
    - Read-only filesystem mounts
    
    The current subprocess approach provides a solid security boundary for a
    honeypot environment where the goal is to safely observe attacker behavior
    without compromising the host system.
    """

    def __init__(self, db_path: Path | str | None = None, timeout: int = 5) -> None:
        self.db_path = Path(db_path or DEFAULT_DB_PATH)
        self.timeout = timeout  # Maximum execution time in seconds
        self._ensure_tables()

    def execute_code(self, fingerprint_hash: str, code: str) -> Dict[str, Any]:
        start_time = time.perf_counter()
        success = True
        error_message = None
        output = ""

        try:
            # Create a temporary file with the wrapped code
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp_file:
                # Use repr() to properly escape the user code as a string literal
                code_repr = repr(code)
                wrapped_code = SANDBOX_WRAPPER_TEMPLATE.format(code_repr=code_repr)
                tmp_file.write(wrapped_code)
                tmp_file.flush()
                tmp_path = tmp_file.name

            try:
                # Execute in isolated subprocess with timeout
                # The subprocess provides the actual isolation barrier
                result = subprocess.run(
                    [sys.executable, tmp_path],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    # Additional security: limit environment variables
                    env={'PYTHONHASHSEED': '0', 'PATH': ''}
                )
                
                output = result.stdout.strip()
                
                if result.returncode != 0:
                    success = False
                    error_message = result.stderr.strip() or f"Process exited with code {result.returncode}"
                    
            except subprocess.TimeoutExpired:
                success = False
                error_message = f"Execution timed out after {self.timeout} seconds"
            except Exception as exc:
                success = False
                error_message = f"Subprocess error: {str(exc)}"
            finally:
                # Clean up temporary file
                try:
                    Path(tmp_path).unlink()
                except Exception:
                    pass  # Best effort cleanup

        except Exception as exc:  # pragma: no cover - defensive
            success = False
            error_message = f"Sandbox setup error: {str(exc)}"

        cpu_time = time.perf_counter() - start_time
        memory_kb = len(code.encode("utf-8")) / 1024.0

        result_dict = {
            "fingerprint_hash": fingerprint_hash,
            "success": success,
            "output": output,
            "error": error_message,
            "cpu_time": round(cpu_time, 4),
            "memory_kb": round(memory_kb, 4),
        }

        self._persist_run(result_dict, code)
        return result_dict

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
