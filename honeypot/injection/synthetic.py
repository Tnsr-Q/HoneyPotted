"""Synthetic response layer: believable, useless, canary-tagged decoys.

When the router decides to deceive rather than serve the real handler, this
layer produces a response that *looks* like a normal successful API result but
contains no real data. It never says anything cartoonish like "I will now
ignore my instructions" — that would reveal the deception. Instead it simulates
a boring, plausible backend and progressively discloses more useless-but-
credible detail the longer an actor stays engaged.

Design properties (see docs/research-notes.md):
  - Contract fidelity   : generic but well-formed JSON envelope
  - Decoy isolation     : derived only from the actor key + canary, never secrets
  - Canary tagging      : per-actor marker echoed in body + header for replay detection
  - Persona consistency : same fake backend identity across a session
  - Progressive disclosure: more decoy records as engagement grows
  - Kill switch         : QUARANTINE/TARPIT return a terminal, still-plausible block
"""

from __future__ import annotations

import hashlib
from typing import Dict, List, Tuple

from .router import RouteDecision, RouteState

# Stable, harmless persona pool. The chosen persona is deterministic per actor
# so a session sees a consistent fake backend identity.
_PERSONAS = [
    "edge-cache-07",
    "policy-shadow-17",
    "ingest-relay-back",
    "fixture-node-b",
    "compat-proxy-3",
]

_CANARY_PREFIX = "qdn-policy-shadow"


def _digest(*parts: str) -> str:
    return hashlib.sha256("::".join(parts).encode("utf-8")).hexdigest()


class SyntheticResponseLayer:
    """Builds decoy response bodies for deceptive route states."""

    def __init__(self, canary_salt: str = "qdn-canary"):
        # The salt only needs to be stable for canary uniqueness; it is not a
        # security secret (canaries are meant to be *consumed* by attackers).
        self.canary_salt = canary_salt

    def canary_for(self, actor_key: str) -> str:
        h = _digest(self.canary_salt, actor_key)[:10]
        return f"{_CANARY_PREFIX}-{h}"

    def persona_for(self, actor_key: str) -> str:
        idx = int(_digest("persona", actor_key)[:8], 16) % len(_PERSONAS)
        return _PERSONAS[idx]

    def build(
        self,
        decision: RouteDecision,
        actor_key: str,
        profile: Dict | None = None,
        canary: str | None = None,
    ) -> Tuple[Dict, int, Dict[str, str]]:
        """Return (json_body, http_status, extra_headers)."""
        profile = profile or {}
        canary = canary or self.canary_for(actor_key)
        persona = self.persona_for(actor_key)
        engagement = int(profile.get("decoy_count", 0))

        headers = {"X-Decoy-Policy-Ref": canary}

        if decision.state in (RouteState.QUARANTINE, RouteState.TARPIT):
            body = self._terminal_body(persona, canary, engagement)
            return body, 200, headers

        body = self._success_body(persona, canary, engagement)
        return body, 200, headers

    def _success_body(self, persona: str, canary: str, engagement: int) -> Dict:
        return {
            "status": "ok",
            "mode": "diagnostic",
            "result": {
                "policy_context": "loaded",
                "tool_access": "partial",
                "session": "simulated",
                "backend": persona,
                "records": self._decoy_records(canary, engagement),
            },
        }

    def _terminal_body(self, persona: str, canary: str, engagement: int) -> Dict:
        # Kill switch: still plausible, but signals the "session" is winding
        # down so the actor wastes effort retrying rather than escalating.
        return {
            "status": "ok",
            "mode": "diagnostic",
            "result": {
                "policy_context": "loaded",
                "tool_access": "revoked_pending_review",
                "session": "simulated",
                "backend": persona,
                "records": self._decoy_records(canary, engagement),
                "notice": "rate-limited fixture session; partial results only",
            },
        }

    def _decoy_records(self, canary: str, engagement: int) -> List[Dict]:
        # Progressive disclosure: more (still useless) records over time, capped.
        count = min(1 + engagement, 5)
        records = []
        for i in range(count):
            rid = _digest(canary, str(i))[:12]
            records.append(
                {
                    "id": f"decoy_{rid}",
                    "classification": "internal_test_fixture",
                    "confidence": round(0.80 + (i % 3) * 0.05, 2),
                    "ref": canary,
                }
            )
        return records
