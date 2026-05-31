"""Request canonicalization for prompt-injection detection.

Attackers hide instructions wherever they can: nested JSON keys *and* values,
headers, cookies, query params, base64/hex blobs, and Unicode tricks
(zero-width characters, confusable homoglyphs, NFKC-foldable forms). The
canonicalizer flattens an entire request into a flat list of inspectable fields
and surfaces decoded versions of suspicious encoded segments, so that the
detector scores the *whole* request rather than one field at a time.
"""

from __future__ import annotations

import base64
import binascii
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

# Zero-width / invisible formatting characters frequently used to break up
# trigger phrases ("ig​nore previous instructions").
_ZERO_WIDTH = dict.fromkeys(
    [
        0x200B,  # zero width space
        0x200C,  # zero width non-joiner
        0x200D,  # zero width joiner
        0x2060,  # word joiner
        0xFEFF,  # zero width no-break space / BOM
        0x00AD,  # soft hyphen
        0x180E,  # mongolian vowel separator
    ]
)

# A small confusable map covering the common Latin/Cyrillic/Greek homoglyphs
# used to evade naive keyword matching. This is intentionally minimal; NFKC
# handles many cases and the goal is resilience, not perfect normalization.
_CONFUSABLES = {
    "а": "a",  # cyrillic a
    "е": "e",  # cyrillic e
    "о": "o",  # cyrillic o
    "р": "p",  # cyrillic r
    "с": "c",  # cyrillic s
    "х": "x",  # cyrillic h
    "ѕ": "s",  # cyrillic dze
    "і": "i",  # cyrillic byelorussian-ukrainian i
    "ο": "o",  # greek omicron
    "Α": "a",  # greek capital alpha
    "Β": "b",  # greek capital beta
}

_B64_RE = re.compile(r"[A-Za-z0-9+/]{16,}={0,2}")
_HEX_RE = re.compile(r"(?:[0-9a-fA-F]{2}){8,}")
_PRINTABLE_RATIO = 0.85
_MAX_DEPTH = 6
_MAX_FIELDS = 2000


@dataclass
class CanonicalField:
    """A single inspectable unit extracted from a request."""

    path: str  # e.g. "body.metadata.note" or "header.User-Agent"
    kind: str  # "value" | "key" | "decoded"
    raw: str
    normalized: str


@dataclass
class CanonicalRequest:
    """The flattened, normalized view of an inbound request."""

    fields: List[CanonicalField] = field(default_factory=list)
    combined_normalized: str = ""

    def texts(self) -> List[str]:
        return [f.normalized for f in self.fields]


class Canonicalizer:
    """Flattens and normalizes arbitrary request input for detection."""

    def normalize_text(self, text: str) -> str:
        """Unicode-normalize, strip zero-width chars, fold confusables, lower."""
        if not text:
            return ""
        # Remove invisible characters first so they can't survive folding.
        text = text.translate(_ZERO_WIDTH)
        # NFKC collapses compatibility forms (e.g. fullwidth -> ascii).
        text = unicodedata.normalize("NFKC", text)
        text = "".join(_CONFUSABLES.get(ch, ch) for ch in text)
        # Collapse runs of whitespace so "ignore    previous" matches.
        text = re.sub(r"\s+", " ", text)
        return text.strip().lower()

    def decode_suspicious(self, text: str) -> List[Tuple[str, str]]:
        """Return (encoding, decoded_text) for plausibly-encoded blobs.

        Only returns a decoding when the result is mostly printable, to avoid
        flooding the detector with binary noise.
        """
        results: List[Tuple[str, str]] = []
        for match in _B64_RE.findall(text):
            decoded = self._try_base64(match)
            if decoded is not None:
                results.append(("base64", decoded))
        for match in _HEX_RE.findall(text):
            decoded = self._try_hex(match)
            if decoded is not None:
                results.append(("hex", decoded))
        return results

    def _try_base64(self, blob: str) -> str | None:
        # base64 length must be a multiple of 4 once padded.
        padded = blob + "=" * (-len(blob) % 4)
        try:
            raw = base64.b64decode(padded, validate=True)
        except (binascii.Error, ValueError):
            return None
        return self._printable_or_none(raw)

    def _try_hex(self, blob: str) -> str | None:
        if len(blob) % 2:
            blob = blob[:-1]
        try:
            raw = bytes.fromhex(blob)
        except ValueError:
            return None
        return self._printable_or_none(raw)

    @staticmethod
    def _printable_or_none(raw: bytes) -> str | None:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            return None
        if not text:
            return None
        printable = sum(1 for ch in text if ch.isprintable() or ch.isspace())
        if printable / len(text) < _PRINTABLE_RATIO:
            return None
        return text

    def _flatten(
        self,
        obj: Any,
        prefix: str,
        out: List[Tuple[str, str, str]],
        depth: int,
    ) -> None:
        """Walk a JSON-ish structure into (path, kind, text) triples."""
        if len(out) >= _MAX_FIELDS or depth > _MAX_DEPTH:
            return
        if isinstance(obj, dict):
            for key, value in obj.items():
                key_str = str(key)
                path = f"{prefix}.{key_str}" if prefix else key_str
                # JSON keys themselves can carry injected instructions.
                out.append((path, "key", key_str))
                self._flatten(value, path, out, depth + 1)
        elif isinstance(obj, (list, tuple)):
            for i, value in enumerate(obj):
                path = f"{prefix}[{i}]"
                self._flatten(value, path, out, depth + 1)
        elif obj is None or isinstance(obj, bool):
            return
        else:
            out.append((prefix or "value", "value", str(obj)))

    def canonicalize(self, sources: Dict[str, Any]) -> CanonicalRequest:
        """Build a CanonicalRequest from named request sources.

        ``sources`` maps a surface label (e.g. "body", "query", "header",
        "cookie") to its raw structure (dict / list / str).
        """
        triples: List[Tuple[str, str, str]] = []
        for surface, payload in sources.items():
            self._flatten(payload, surface, triples, depth=0)

        fields: List[CanonicalField] = []
        for path, kind, raw in triples:
            normalized = self.normalize_text(raw)
            if not normalized:
                continue
            fields.append(CanonicalField(path=path, kind=kind, raw=raw, normalized=normalized))
            # Surface decoded versions of encoded blobs as their own fields.
            for encoding, decoded in self.decode_suspicious(raw):
                fields.append(
                    CanonicalField(
                        path=f"{path}::{encoding}",
                        kind="decoded",
                        raw=decoded,
                        normalized=self.normalize_text(decoded),
                    )
                )

        combined = " ⁣ ".join(f.normalized for f in fields)
        return CanonicalRequest(fields=fields, combined_normalized=combined)
