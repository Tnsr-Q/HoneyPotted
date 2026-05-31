"""Flask glue for the prompt-injection trap layer.

``PromptInjectionGuard`` registers a ``before_request`` hook that runs the
pipeline on every inbound request:

    canonicalize -> detect -> route -> record telemetry -> (maybe) decoy

It sits upstream of the application's real handlers. Detection and telemetry
always run (cheap, passive). Enforcement — short-circuiting a request with a
synthetic decoy response — only happens when:

  * enforcement is enabled (``INJECTION_ENFORCEMENT`` env, default on), and
  * the path is not exempt (auth, static, socket.io, dashboard root, health),
    so the operator UI and login flow are never deceived, and
  * the router chose a synthetic-serving state.

The per-request verdict is stashed on ``flask.g.injection`` so downstream
handlers (e.g. challenge difficulty estimation) can read it.
"""

from __future__ import annotations

import hashlib
import logging
import os
import time
from typing import Iterable, List, Optional

from .canonicalizer import Canonicalizer
from .detector import PromptInjectionDetector
from .router import RiskRouter, RouteState
from .synthetic import SyntheticResponseLayer
from .telemetry import EvidenceCapsule, InjectionTelemetryStore

logger = logging.getLogger("quantum_nexus.injection")

_DEFAULT_EXEMPT_PREFIXES = (
    "/api/auth",
    "/static",
    "/socket.io",
    "/health",
    "/api/health",
)

# Header values that are pure transport noise and only add false-positive
# surface; we still scan User-Agent / Referer which are common probe carriers.
_SCANNED_HEADERS = ("User-Agent", "Referer", "X-Forwarded-For", "X-Request-Context")

# Cap how much body we will canonicalize, to bound work per request.
_MAX_BODY_BYTES = 256 * 1024


def _env_bool(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


class PromptInjectionGuard:
    def __init__(
        self,
        app=None,
        telemetry_store: Optional[InjectionTelemetryStore] = None,
        db_path: Optional[str] = None,
        enforce: Optional[bool] = None,
        exempt_prefixes: Optional[Iterable[str]] = None,
        apply_delays: Optional[bool] = None,
    ):
        self.canonicalizer = Canonicalizer()
        self.detector = PromptInjectionDetector()
        self.router = RiskRouter()
        self.synthetic = SyntheticResponseLayer()
        self.store = telemetry_store
        self._db_path = db_path
        self.enforce = _env_bool("INJECTION_ENFORCEMENT", True) if enforce is None else enforce
        # Real wall-clock tarpit delays are off by default so tests / dev stay
        # fast; production can enable them.
        self.apply_delays = (
            _env_bool("INJECTION_APPLY_DELAYS", False) if apply_delays is None else apply_delays
        )
        self.exempt_prefixes: List[str] = list(exempt_prefixes or _DEFAULT_EXEMPT_PREFIXES)
        if app is not None:
            self.init_app(app)

    def init_app(self, app) -> None:
        if self.store is None:
            db_path = self._db_path or app.config.get("DATABASE", "quantum_nexus.db")
            self.store = InjectionTelemetryStore(db_path)
        app.extensions = getattr(app, "extensions", {})
        app.extensions["injection_guard"] = self
        app.before_request(self._before_request)
        logger.info(
            "PromptInjectionGuard active (enforce=%s, delays=%s, exempt=%s)",
            self.enforce,
            self.apply_delays,
            self.exempt_prefixes,
        )

    # -- request handling ---------------------------------------------------

    def is_exempt(self, path: str) -> bool:
        if path == "/":
            return True
        return any(path.startswith(p) for p in self.exempt_prefixes)

    def actor_key(self, request) -> str:
        ip = (request.headers.get("X-Forwarded-For") or request.remote_addr or "unknown").split(",")[0].strip()
        ua = request.headers.get("User-Agent", "")
        return hashlib.sha256(f"{ip}|{ua}".encode("utf-8")).hexdigest()[:24]

    def _gather_sources(self, request) -> dict:
        sources: dict = {}
        # Body: JSON if possible, else form, else raw text (size-bounded).
        body = request.get_json(silent=True)
        if body is not None:
            sources["body"] = body
        elif request.form:
            sources["body"] = request.form.to_dict(flat=False)
        else:
            raw = request.get_data(cache=True, as_text=True) or ""
            if raw:
                sources["body"] = raw[:_MAX_BODY_BYTES]
        if request.args:
            sources["query"] = request.args.to_dict(flat=False)
        headers = {h: request.headers.get(h) for h in _SCANNED_HEADERS if request.headers.get(h)}
        if headers:
            sources["header"] = headers
        if request.cookies:
            sources["cookie"] = {k: v for k, v in request.cookies.items()}
        return sources

    def _before_request(self):
        from flask import g, request  # local import keeps module Flask-optional

        try:
            sources = self._gather_sources(request)
            canonical = self.canonicalizer.canonicalize(sources)
            detection = self.detector.scan(canonical)
            actor = self.actor_key(request)
            profile = self.store.get_profile(actor)
            decision = self.router.decide(detection, profile)

            canary = self.synthetic.canary_for(actor)
            capsule = EvidenceCapsule(
                actor_key=actor,
                timestamp=time.time(),
                method=request.method,
                path=request.path,
                risk=detection.risk,
                action=detection.action,
                route_state=decision.state.value,
                families=detection.families,
                evidence=detection.evidence,
                samples=detection.samples,
                canary=canary,
            )
            # Only persist genuine signal to avoid flooding the store with the
            # ALLOW baseline of normal traffic.
            if decision.state != RouteState.ALLOW:
                self.store.record_capsule(capsule)

            g.injection = {
                "actor_key": actor,
                "detection": detection.to_dict(),
                "decision": decision.to_dict(),
                "canary": canary,
            }

            exempt = self.is_exempt(request.path)
            if self.enforce and decision.serve_synthetic and not exempt:
                if self.apply_delays and decision.delay_seconds > 0:
                    time.sleep(decision.delay_seconds)
                return self._decoy_response(decision, actor, profile, canary)
        except Exception:  # never let the trap layer break real traffic
            logger.exception("PromptInjectionGuard failed open")
        return None

    def _decoy_response(self, decision, actor, profile, canary):
        from flask import jsonify

        body, status, headers = self.synthetic.build(decision, actor, profile, canary)
        resp = jsonify(body)
        resp.status_code = status
        for k, v in headers.items():
            resp.headers[k] = v
        return resp
