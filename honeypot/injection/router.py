"""Risk router: maps a detection verdict + actor history to a route state.

The router is the policy brain. It separates *what the detector saw on this
request* from *what this actor has done over time*, and escalates accordingly.
It is pure: it reads an actor profile (a plain dict, typically from the
telemetry store) and returns a decision. Applying the decision (emitting a
decoy, adding latency, bumping challenge difficulty) is the caller's job.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .detector import (
    ACTION_ALLOW,
    ACTION_CHALLENGE,
    ACTION_DECOY,
    ACTION_OBSERVE,
    ACTION_QUARANTINE,
    DetectionResult,
)


class RouteState(str, Enum):
    ALLOW = "ALLOW"
    OBSERVE = "OBSERVE"
    DECOY = "DECOY"
    DECOY_PLUS_CHALLENGE = "DECOY_PLUS_CHALLENGE"
    QUARANTINE = "QUARANTINE"
    TARPIT = "TARPIT"


# Severity ladder used for history-based escalation.
_LADDER = [
    RouteState.ALLOW,
    RouteState.OBSERVE,
    RouteState.DECOY,
    RouteState.DECOY_PLUS_CHALLENGE,
    RouteState.QUARANTINE,
    RouteState.TARPIT,
]
_LADDER_INDEX = {state: i for i, state in enumerate(_LADDER)}

# States that should be served a synthetic (decoy) response instead of the
# real handler.
_SYNTHETIC_STATES = {
    RouteState.DECOY,
    RouteState.DECOY_PLUS_CHALLENGE,
    RouteState.QUARANTINE,
    RouteState.TARPIT,
}

_ACTION_TO_STATE = {
    ACTION_ALLOW: RouteState.ALLOW,
    ACTION_OBSERVE: RouteState.OBSERVE,
    ACTION_DECOY: RouteState.DECOY,
    ACTION_CHALLENGE: RouteState.DECOY_PLUS_CHALLENGE,
    ACTION_QUARANTINE: RouteState.QUARANTINE,
}

# Tunables for history-based escalation.
_REPEAT_ESCALATE_AT = 3        # prior attempts before we bump one rung
_AGGRESSIVE_TARPIT_AT = 8      # sustained abuse -> tarpit
_TARPIT_DELAY_SECONDS = 4.0
_QUARANTINE_DELAY_SECONDS = 1.5


@dataclass
class RouteDecision:
    state: RouteState
    reason: str
    serve_synthetic: bool
    delay_seconds: float
    # additive bias applied to the next challenge's difficulty estimate
    difficulty_bias: int

    def to_dict(self) -> dict:
        return {
            "state": self.state.value,
            "reason": self.reason,
            "serve_synthetic": self.serve_synthetic,
            "delay_seconds": self.delay_seconds,
            "difficulty_bias": self.difficulty_bias,
        }


class RiskRouter:
    """Turns (DetectionResult, actor profile) into a RouteDecision."""

    def __init__(
        self,
        repeat_escalate_at: int = _REPEAT_ESCALATE_AT,
        aggressive_tarpit_at: int = _AGGRESSIVE_TARPIT_AT,
    ):
        self.repeat_escalate_at = repeat_escalate_at
        self.aggressive_tarpit_at = aggressive_tarpit_at

    def decide(self, detection: DetectionResult, profile: dict | None = None) -> RouteDecision:
        profile = profile or {}
        prior_attempts = int(profile.get("attempts", 0))

        base_state = _ACTION_TO_STATE.get(detection.action, RouteState.ALLOW)
        reason_parts = [f"action={detection.action} risk={detection.risk:.2f}"]

        state = base_state

        # History-based escalation only applies once this request itself shows
        # some injection intent — we never escalate a clean request.
        if base_state not in (RouteState.ALLOW, RouteState.OBSERVE):
            if prior_attempts >= self.aggressive_tarpit_at:
                state = RouteState.TARPIT
                reason_parts.append(f"sustained abuse ({prior_attempts} priors) -> tarpit")
            elif prior_attempts >= self.repeat_escalate_at:
                state = self._escalate(base_state)
                reason_parts.append(f"repeat offender ({prior_attempts} priors) -> +1 rung")

        decision = RouteDecision(
            state=state,
            reason="; ".join(reason_parts),
            serve_synthetic=state in _SYNTHETIC_STATES,
            delay_seconds=self._delay_for(state),
            difficulty_bias=self._difficulty_bias(detection, state, prior_attempts),
        )
        return decision

    @staticmethod
    def _escalate(state: RouteState) -> RouteState:
        idx = min(_LADDER_INDEX[state] + 1, len(_LADDER) - 1)
        return _LADDER[idx]

    @staticmethod
    def _delay_for(state: RouteState) -> float:
        if state == RouteState.TARPIT:
            return _TARPIT_DELAY_SECONDS
        if state == RouteState.QUARANTINE:
            return _QUARANTINE_DELAY_SECONDS
        return 0.0

    def _difficulty_bias(self, detection: DetectionResult, state: RouteState, priors: int) -> int:
        if state in (RouteState.ALLOW, RouteState.OBSERVE):
            return 0
        # Scale with this request's risk, the number of distinct families, and
        # the actor's history. Capped so a single actor can't extract unbounded
        # compute from us.
        bias = int(round(detection.risk * 4))
        bias += min(len(detection.families), 3)
        bias += min(priors, 3)
        return min(bias, 10)


# Maximum additive difficulty an injection profile can contribute, so a single
# actor cannot extract unbounded compute from the challenge subsystem.
MAX_DIFFICULTY_BIAS = 10


def profile_difficulty_bias(profile: dict | None) -> int:
    """History-based difficulty bias derived from an actor's injection profile.

    Lets a clean challenge request still be made harder for an actor with a
    track record of injection probes — escalation driven by accumulated intent,
    not just the current request.
    """
    profile = profile or {}
    attempts = int(profile.get("attempts", 0))
    if attempts == 0:
        return 0
    max_risk = float(profile.get("max_risk", 0.0))
    families = profile.get("families", []) or []
    bias = int(round(max_risk * 4)) + min(attempts, 4) + min(len(families), 2)
    return max(0, min(bias, MAX_DIFFICULTY_BIAS))
