# Normalize and cap board gists, rejecting patch summaries with placeholder evidence.
# Verification is a deterministic text check; it does not execute the claimed tests.

from __future__ import annotations

import re
from typing import Dict, Tuple

from shared_lessons import (
    TYPES,
    MAX_CONTENT_CHARS,
    MAX_PATCH_SUMMARY_CHARS,
    parse_patch_summary_field,
)

_FORMATS = {
    "TASK": (re.compile(r"^t\d+ (?:[a-z0-9-]+-)?worker\d+ (?:isolated|collaborative): \S"),
             "TASK must read `t<n> worker<n> isolated: <what to find>` or `... collaborative: ...`"),
    "DONE": (re.compile(r"^t\d+: \S"), "DONE must read `t<n>: <what was found>`"),
    "KEY": (re.compile(r"^G\d+: \S"), "KEY must read `G<n>: <why the report depends on it>`"),
    "VERIFIED": (re.compile(r"^G\d+: \S"), "VERIFIED must read `G<n>: <what you checked>`"),
    "CHALLENGE": (re.compile(r"^G\d+: \S"), "CHALLENGE must read `G<n>: <what fails>`"),
    "ALTERNATIVE": (re.compile(r"^G\d+: \S"), "ALTERNATIVE must read `G<n>: <the other answer>`"),
    "REPORT": (re.compile(r"^v\d+: \S"), "REPORT must read `v<n>: <what changed>`"),
}

_INVALID_EVIDENCE_PHRASES = (
    "tbd",
    "pending",
    "not verified",
    "unverified",
    "should work",
    "should pass",
    "looks right",
    "looks correct",
    "seems to work",
    "to be verified",
    "will verify",
    "n/a",
)

def _is_invalid_patch_summary_evidence(content: str) -> bool:
    ev = parse_patch_summary_field(content, "evidence")
    if ev is None:
        return True
    norm = ev.strip().lower()
    if not norm:
        return True
    for p in _INVALID_EVIDENCE_PHRASES:
        if norm == p:
            return True
        if norm.startswith(p):
            tail = norm[len(p):]
            if not tail or not tail[0].isalpha():
                return True
    return False

def verify_note(note: Dict[str, str]) -> Tuple[Dict[str, str] | None, str]:
    kind = str(note.get("type", "")).strip().upper()
    content = str(note.get("content", "")).strip()
    if kind not in TYPES or not content:
        return None, "ok:0/1"
    cap = MAX_PATCH_SUMMARY_CHARS if kind == "PATCH_SUMMARY" else MAX_CONTENT_CHARS
    # Check the text that will actually be stored after truncation.
    content = content[:cap]
    if kind == "PATCH_SUMMARY" and _is_invalid_patch_summary_evidence(content):
        return None, "ok:0/1,ps_invalid_ev=1"
    if kind in _FORMATS and not _FORMATS[kind][0].match(content):
        return None, _FORMATS[kind][1]
    if kind == "REPORT" and not str(note.get("detail") or "").strip():
        return None, "REPORT needs the whole report in `detail`"
    return {"type": kind, "content": content}, "ok:1/1"
