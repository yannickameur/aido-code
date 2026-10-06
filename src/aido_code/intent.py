"""Deterministic natural-language intent router (M3 MVP).

A small, closed, hand-written keyword matcher: it maps free-form REPL
input to one of four intents (status, why a WorkItem is waiting/blocked,
workers/providers, run/continue) or to `UNKNOWN`. It never calls a
provider or an LLM, has no configurable grammar, and never guesses:
input matching zero intents, or more than one, is `UNKNOWN`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class Intent(str, Enum):
    STATUS = "status"
    WHY_WAITING = "why_waiting"
    WORKERS = "workers"
    RUN = "run"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class IntentMatch:
    intent: Intent
    work_item_id: str | None = None


_WORD_RE = re.compile(r"[a-z0-9']+")
_WORK_ITEM_RE = re.compile(r"\bwork[\s_-]?items?\s+#?([A-Za-z0-9][\w.-]*)", re.IGNORECASE)
_WORK_ITEM_ID_RE = re.compile(r"\b([A-Za-z]+(?:-[\w.]+)+)\b")
_NEGATION = {"don't", "dont", "not", "never", "no", "stop", "cancel", "without"}

_WAIT_WORDS = {"waiting", "wait", "blocked", "block", "stuck", "stalled", "paused", "pending"}
_WORKER_WORDS = {"worker", "workers", "provider", "providers", "agents", "agent"}
_STATUS_WORDS = {"status", "state", "progress", "standing"}
_RUN_VERBS = {"run", "continue", "resume", "start", "proceed", "go", "launch", "execute", "carry", "keep", "going"}
_QUESTION_WORDS = {"what", "which", "who", "how", "where", "list", "show", "see", "any"}


def _work_item_id(text: str) -> str | None:
    match = _WORK_ITEM_RE.search(text)
    if match:
        return match.group(1).rstrip(".,?!")
    for candidate in _WORK_ITEM_ID_RE.findall(text):
        if any(ch.isdigit() for ch in candidate):
            return candidate.rstrip(".,?!")
    return None


def interpret(text: str) -> IntentMatch:
    """Pure function of `text`: no I/O, no engine, no provider."""
    words = _WORD_RE.findall(text.lower())
    word_set = set(words)
    if not words or word_set & _NEGATION:
        return IntentMatch(Intent.UNKNOWN)

    matched: list[Intent] = []
    if "why" in word_set and word_set & _WAIT_WORDS:
        matched.append(Intent.WHY_WAITING)
    elif word_set & _WORKER_WORDS and (word_set & _QUESTION_WORDS or "available" in word_set
                                       or "configured" in word_set or "enabled" in word_set):
        matched.append(Intent.WORKERS)
    elif word_set & _STATUS_WORDS and (word_set & _QUESTION_WORDS or "is" in word_set
                                       or "the" in word_set or len(words) <= 2):
        matched.append(Intent.STATUS)
    elif word_set & _WAIT_WORDS and word_set & _QUESTION_WORDS:
        # e.g. "what is blocked?" / "is anything waiting?" -> status view
        matched.append(Intent.STATUS)
    if (words[0] in _RUN_VERBS or words[0] in {"please", "let's", "lets", "can", "could", "now"}) and (
        word_set & _RUN_VERBS
    ) and not word_set & (_WORKER_WORDS | _STATUS_WORDS | {"why", "what", "which", "how"}):
        matched.append(Intent.RUN)

    if len(matched) != 1:
        return IntentMatch(Intent.UNKNOWN)
    intent = matched[0]
    return IntentMatch(intent, _work_item_id(text) if intent is Intent.WHY_WAITING else None)
