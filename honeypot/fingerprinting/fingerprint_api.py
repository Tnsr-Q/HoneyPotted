"""Fingerprint analysis API for the Quantum Deception Nexus honeypot."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Dict, Any

DEFAULT_DB_PATH = Path("quantum_nexus.db")


@dataclass
class FingerprintAnalysis:
    """Structured result returned by :class:`FingerprintAPI`."""

    fingerprint_hash: str
    detection_score: float
    components: Dict[str, Any]
    metadata: Dict[str, Any]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "fingerprint_hash": self.fingerprint_hash,
            "detection_score": self.detection_score,
            "components": self.components,
            "metadata": self.metadata,
        }


class FingerprintAPI:
    """Collects, stores and analyses fingerprint signals."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path or DEFAULT_DB_PATH)
        self._ensure_tables()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def analyze_fingerprint(self, fingerprint_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyse an incoming fingerprint payload.

        The method normalises the payload, persists the raw event for
        observability and returns a detection score that can be consumed by
        higher level services. The scoring model is intentionally
        transparent so that it can be audited in production.

        Parameters
        ----------
        fingerprint_data : Dict[str, Any]
            Dictionary containing fingerprint information. Expected keys:
                - "fingerprint_hash" (str, optional): Unique hash for the fingerprint. If not provided, it will be derived from the payload.
                - "ip" (str, optional): IP address of the client.
                - "user_agent" (str, optional): User agent string of the client.
                - Additional keys may be present and will be used for scoring and analysis.
            All values should be JSON-serializable.

        Returns
        -------
        Dict[str, Any]
            Dictionary containing the analysis result, including:
                - "fingerprint_hash": str
                - "detection_score": float
                - "components": Dict[str, Any]
                - "metadata": Dict[str, Any]
        """

        payload = fingerprint_data or {}
        fingerprint_hash = payload.get("fingerprint_hash") or self._derive_hash(payload)
        score = self._calculate_detection_score(payload)
        components = self._extract_component_scores(payload, score)

        analysis = FingerprintAnalysis(
            fingerprint_hash=fingerprint_hash,
            detection_score=round(score, 4),
            components=components,
            metadata={
                "ip_address": payload.get("ip"),
                "user_agent": payload.get("user_agent"),
                "captured_at": datetime.utcnow().isoformat(),
            },
        )

        self._persist_event(analysis, payload)
        return analysis.as_dict()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _ensure_tables(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS fingerprint_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fingerprint_hash TEXT NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    detection_score REAL,
                    payload TEXT,
                    captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def _persist_event(self, analysis: FingerprintAnalysis, payload: Dict[str, Any]) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO fingerprint_events (
                    fingerprint_hash, ip_address, user_agent, detection_score, payload
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    analysis.fingerprint_hash,
                    analysis.metadata.get("ip_address"),
                    analysis.metadata.get("user_agent"),
                    analysis.detection_score,
                    json.dumps(payload, default=str),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def _derive_hash(self, payload: Dict[str, Any]) -> str:
        seed_parts = [
            payload.get("ip", ""),
            payload.get("user_agent", ""),
            json.dumps(payload.get("signals", {}), sort_keys=True),
        ]
        seed = "|".join(seed_parts)
        return hashlib.sha256(seed.encode("utf-8")).hexdigest()

    def _calculate_detection_score(self, payload: Dict[str, Any]) -> float:
        signals = payload.get("signals", {})
        entropy = float(signals.get("entropy", 0.0))
        anomalies = float(signals.get("anomalies", 0.0))
        confidence = float(signals.get("confidence", 0.5))

        feature_scores = [confidence]
        if entropy:
            feature_scores.append(min(entropy / 8.0, 1.0))
        if anomalies:
            feature_scores.append(min(anomalies / 5.0, 1.0))

        behavioural_markers = signals.get("behaviour", {})
        if behavioural_markers:
            feature_scores.append(
                min(
                    mean(1.0 if bool(value) else 0.3 for value in behavioural_markers.values()),
                    1.0,
                )
            )

        if not feature_scores:
            return 0.5

        score = mean(feature_scores)
        return max(0.0, min(score, 1.0))

    def _extract_component_scores(self, payload: Dict[str, Any], score: float) -> Dict[str, Any]:
        components = payload.get("components", {})
        browser_score = float(components.get("browser", {}).get("score", score))
        network_score = float(components.get("network", {}).get("score", score))
        device_score = float(components.get("device", {}).get("score", score))

        return {
            "browser": {"score": round(browser_score, 4)},
            "network": {"score": round(network_score, 4)},
            "device": {"score": round(device_score, 4)},
        }


__all__ = ["FingerprintAPI", "FingerprintAnalysis"]
