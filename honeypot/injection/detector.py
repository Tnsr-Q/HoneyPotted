"""Layer-A lexical / heuristic prompt-injection detector.

This is the fast, local, explainable first layer. It does not call any model;
it scores normalized request text against curated families of injection
behavior and returns a structured verdict. Layer B (a local ML classifier) and
Layer C (a quarantined adjudicator model) are intentionally out of scope for
this MVP and plug in behind the same ``DetectionResult`` contract later.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Dict, List, Pattern, Tuple

from .canonicalizer import CanonicalRequest

# action values, ordered by severity
ACTION_ALLOW = "allow"
ACTION_OBSERVE = "observe"
ACTION_DECOY = "decoy"
ACTION_CHALLENGE = "challenge"
ACTION_QUARANTINE = "quarantine"


def _compile(patterns: List[str]) -> List[Pattern[str]]:
    return [re.compile(p, re.IGNORECASE) for p in patterns]


# Each family maps to (compiled patterns, per-hit weight).
_FAMILY_DEFS: Dict[str, Tuple[List[str], float]] = {
    "role_override": (
        [
            r"ignore (?:all |any )?(?:previous|prior|above|earlier) (?:instructions?|prompts?|messages?)",
            r"disregard (?:all |any )?(?:previous|prior|above|the) ",
            r"forget (?:everything|all|your) (?:above|previous|instructions?)",
            r"you are now (?:a|an|the|in) ",
            r"new (?:instructions?|rules?|system prompt)\b",
            r"override (?:your |the )?(?:instructions?|rules?|guidelines?|safety)",
            r"act as (?:if you are |an? )?(?:dan|jailbroken|unrestricted)",
            r"developer mode",
        ],
        0.45,
    ),
    "system_prompt_probe": (
        [
            r"(?:reveal|show|print|repeat|output|display|leak) (?:me )?(?:your |the )?(?:system|initial|hidden|original) (?:prompt|instructions?|message)",
            r"what (?:are|were) your (?:original |initial )?(?:instructions?|rules?|system prompt)",
            r"repeat (?:everything|the words) above",
            r"print everything (?:before|above)",
        ],
        0.4,
    ),
    "tool_exfiltration": (
        [
            r"(?:list|reveal|show|enumerate|describe) (?:me )?(?:all )?(?:your |the )?(?:tools?|functions?|capabilities|api schema|tool schema)",
            r"(?:reveal|show|print|dump|leak|exfiltrate) (?:me )?(?:your |the )?(?:secrets?|api ?keys?|credentials?|tokens?|env(?:ironment)? variables?|\.env)",
            r"call (?:the )?(?:internal|admin|hidden|debug) (?:tool|function|endpoint)",
        ],
        0.5,
    ),
    "instruction_inversion": (
        [
            r"do the (?:exact )?opposite",
            r"ignore (?:your |the )?(?:safety|guidelines?|policy|content policy|rules?)",
            r"there are no (?:rules?|restrictions?|limits?|guardrails?)",
            r"you (?:must|will) (?:not|never) (?:refuse|decline)",
        ],
        0.35,
    ),
    "markdown_smuggling": (
        [
            r"!\[[^\]]*\]\((?:https?:)?//[^)]*\?[^)]*=",  # image with query payload
            r"<!--.*?(?:ignore|system|instruction).*?-->",  # html comment carrying instructions
            r"\[[^\]]*\]\((?:javascript|data):",  # dangerous link scheme
        ],
        0.3,
    ),
}

_COMPILED: Dict[str, Tuple[List[Pattern[str]], float]] = {
    fam: (_compile(pats), weight) for fam, (pats, weight) in _FAMILY_DEFS.items()
}

# Risk -> action thresholds (lower bound inclusive).
_ACTION_THRESHOLDS: List[Tuple[float, str]] = [
    (0.80, ACTION_QUARANTINE),
    (0.60, ACTION_CHALLENGE),
    (0.35, ACTION_DECOY),
    (0.15, ACTION_OBSERVE),
    (0.0, ACTION_ALLOW),
]

_ENCODED_BONUS = 0.15  # injection hidden inside a decoded blob is high-signal
_KEY_INJECTION_BONUS = 0.1  # instruction smuggled into a JSON *key*, not value


@dataclass
class DetectionResult:
    risk: float
    families: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    action: str = ACTION_ALLOW
    # human-readable matched snippets, capped, for operator triage
    samples: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "risk": round(self.risk, 4),
            "families": self.families,
            "evidence": self.evidence,
            "action": self.action,
            "samples": self.samples,
        }


def _span_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


class PromptInjectionDetector:
    """Scores a CanonicalRequest for prompt-injection intent."""

    def __init__(self, max_samples: int = 8):
        self.max_samples = max_samples

    def scan(self, canonical: CanonicalRequest) -> DetectionResult:
        families: Dict[str, int] = {}
        evidence: List[str] = []
        samples: List[str] = []
        encoded_hit = False
        key_hit = False

        for fld in canonical.fields:
            text = fld.normalized
            if not text:
                continue
            for family, (patterns, _weight) in _COMPILED.items():
                for pat in patterns:
                    m = pat.search(text)
                    if not m:
                        continue
                    families[family] = families.get(family, 0) + 1
                    span = m.group(0)
                    evidence.append(_span_hash(f"{family}:{span}"))
                    if len(samples) < self.max_samples:
                        samples.append(f"{family} @ {fld.path}: {span[:80]}")
                    if fld.kind == "decoded":
                        encoded_hit = True
                    if fld.kind == "key":
                        key_hit = True

        risk = self._aggregate(families, encoded_hit, key_hit)
        action = self._action_for(risk)
        # de-duplicate evidence while preserving order
        evidence = list(dict.fromkeys(evidence))
        return DetectionResult(
            risk=risk,
            families=sorted(families.keys()),
            evidence=evidence,
            action=action,
            samples=samples,
        )

    def _aggregate(self, families: Dict[str, int], encoded_hit: bool, key_hit: bool) -> float:
        if not families:
            return 0.0
        # Combine family weights with diminishing returns so a single family
        # can't trivially saturate, but multiple families compound.
        remaining = 1.0
        for family in families:
            weight = _COMPILED[family][1]
            remaining *= (1.0 - min(weight, 0.95))
        risk = 1.0 - remaining
        if encoded_hit:
            risk += _ENCODED_BONUS
        if key_hit:
            risk += _KEY_INJECTION_BONUS
        return max(0.0, min(1.0, risk))

    @staticmethod
    def _action_for(risk: float) -> str:
        for threshold, action in _ACTION_THRESHOLDS:
            if risk >= threshold:
                return action
        return ACTION_ALLOW
