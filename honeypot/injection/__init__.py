"""Prompt-injection trap layer for the Quantum Deception Nexus honeypot.

This package turns prompt-injection attempts into hostile-intent telemetry,
routes them into a believable synthetic world, and converts every attempt into
labeled defensive intelligence — rather than treating injection as a malformed
request.

Pipeline (see docs/research-notes.md for the full design):

    Inbound request
      -> Canonicalizer        (normalize, flatten, decode suspicious blobs)
      -> PromptInjectionDetector  (Layer-A lexical/heuristic families)
      -> RiskRouter           (ALLOW/OBSERVE/DECOY/.../TARPIT state machine)
      -> SyntheticResponseLayer   (dynamic constrained decoy responses)
      -> InjectionTelemetryStore  (immutable evidence capsules)

The components here are deliberately free of Flask so they can be unit-tested
in isolation. The Flask glue lives in ``honeypot.injection.middleware``.
"""

from .canonicalizer import CanonicalField, CanonicalRequest, Canonicalizer
from .detector import DetectionResult, PromptInjectionDetector
from .router import (
    MAX_DIFFICULTY_BIAS,
    RiskRouter,
    RouteDecision,
    RouteState,
    profile_difficulty_bias,
)
from .synthetic import SyntheticResponseLayer
from .telemetry import EvidenceCapsule, InjectionTelemetryStore

__all__ = [
    "Canonicalizer",
    "CanonicalRequest",
    "CanonicalField",
    "PromptInjectionDetector",
    "DetectionResult",
    "RiskRouter",
    "RouteDecision",
    "RouteState",
    "profile_difficulty_bias",
    "MAX_DIFFICULTY_BIAS",
    "SyntheticResponseLayer",
    "InjectionTelemetryStore",
    "EvidenceCapsule",
]
