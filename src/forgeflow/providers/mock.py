"""Deterministic mock provider.

This powers offline demos and CI evals — no API keys, no network, same output
every time. It is intentionally a *small heuristic reasoner*, not a real model:
it inspects the requested JSON fields and the prompt text and fills in plausible,
deterministic values. Good enough to exercise the whole workflow engine.
"""

from __future__ import annotations

import json
import re
from typing import Any

from forgeflow.providers.base import LLMResponse, Provider

# Signal words kept deliberately distinct from instruction vocabulary so that
# prompt instructions don't leak into classification.
_HIGH_URGENCY = [
    "urgent", "asap", "immediately", "emergency", "three times", "3 times",
    "no one", "still not", "again", "angry", "furious", "unacceptable",
    "no heat", "no cooling", "no cool", "leak", "flooding", "sparks", "burning",
    "down", "outage", "cannot", "can't", "won't turn",
]
_BILLING = ["refund", "charge", "charged", "billing", "invoice", "overcharged", "payment", "double"]
_COMPLAINT = [
    "broken", "not working", "doesn't work", "fix", "fixed", "failed", "fault",
    "no one", "three times", "again", "still", "leak", "no heat", "no cool",
    "frustrated", "disappointed", "angry", "complaint",
]
_QUESTION = ["how do", "how can", "what is", "when will", "do you", "can i", "is it possible", "?"]

_HVAC = ["ac", "a/c", "air conditioner", "furnace", "heat", "heating", "cooling", "thermostat", "hvac"]
_PLUMBING = ["leak", "pipe", "drain", "toilet", "faucet", "water heater", "clog", "sewer"]
_ELECTRICAL = ["outlet", "breaker", "wiring", "sparks", "panel", "circuit", "electrical", "power"]


def _has_any(text: str, words: list[str]) -> bool:
    return any(w in text for w in words)


def _count_any(text: str, words: list[str]) -> int:
    return sum(1 for w in words if w in text)


def _classify_urgency(text: str) -> str:
    hits = _count_any(text, _HIGH_URGENCY)
    if hits >= 2 or _has_any(text, ["emergency", "no heat", "leak", "flooding", "sparks"]):
        return "high"
    if hits == 1:
        return "medium"
    return "low"


def _classify_category(text: str) -> str:
    if _has_any(text, _BILLING):
        return "billing"
    if _has_any(text, _COMPLAINT):
        return "complaint"
    if _has_any(text, _QUESTION):
        return "question"
    return "general"


def _classify_trade(text: str) -> str:
    scores = {
        "hvac": _count_any(text, _HVAC),
        "plumbing": _count_any(text, _PLUMBING),
        "electrical": _count_any(text, _ELECTRICAL),
    }
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "general"


_OWNER_STOP = {
    "We", "The", "This", "That", "Send", "Review", "Ship", "Fix", "Return",
    "Read", "Write", "Format", "Draft", "Classify",
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
}


def _user_content(prompt: str) -> str:
    """Isolate the actual user input from surrounding instructions.

    Workflow prompts label the input with a line like ``Notes:`` / ``Message:``.
    Everything after the last such label is the user content; this keeps
    instruction text out of summaries and classification.
    """
    lines = prompt.splitlines()
    label_idx = None
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.endswith(":") and len(s.split()) <= 3:
            label_idx = i
    if label_idx is not None:
        body = "\n".join(lines[label_idx + 1:]).strip()
        if body:
            return body
    return prompt.strip()


def _summarize(text: str) -> str:
    lines = [ln.strip(" -•\t") for ln in text.splitlines() if ln.strip()]
    content = lines[0] if lines else text
    words = content.split()
    return " ".join(words[:16]) + ("..." if len(words) > 16 else "")


def _lead_score(text: str) -> int:
    score = 30
    score += 25 if _has_any(text, ["budget", "$", "funded", "revenue"]) else 0
    score += 20 if _has_any(text, ["enterprise", "team", "company", "employees", "seats"]) else 0
    score += 15 if _has_any(text, ["urgent", "this quarter", "soon", "now", "asap"]) else 0
    score += 15 if _has_any(text, ["ceo", "founder", "vp", "head of", "director", "owner"]) else 0
    score -= 20 if _has_any(text, ["just curious", "student", "no budget", "free"]) else 0
    return max(0, min(100, score))


def _next_action(score: int) -> str:
    if score >= 70:
        return "book_demo"
    if score >= 45:
        return "nurture"
    return "disqualify"


def _action_items(text: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    name_re = re.compile(r"\b([A-Z][a-z]+)\b")
    for ln in text.splitlines():
        ln = ln.strip(" -•\t")
        if not ln or len(ln.split()) < 2:
            continue
        if _has_any(ln.lower(), ["will", "to ", "by ", "follow up", "send", "review", "ship", "fix", "owns", "deadline"]):
            names = [n for n in name_re.findall(ln) if n not in _OWNER_STOP]
            owner = names[0] if names else "Unassigned"
            items.append({"task": ln, "owner": owner, "due": "next week"})
    if not items:
        items.append({"task": "Review notes and assign owners", "owner": "Unassigned", "due": "next week"})
    return items


_FIELD_BUILDERS = {
    "category": lambda t: _classify_category(t),
    "urgency": lambda t: _classify_urgency(t),
    "priority": lambda t: _classify_urgency(t),
    "summary": lambda t: _summarize(t),
    "trade": lambda t: _classify_trade(t),
    "service_category": lambda t: _classify_trade(t),
    "score": lambda t: _lead_score(t),
    "lead_score": lambda t: _lead_score(t),
    "qualification_score": lambda t: _lead_score(t),
    "action_items": lambda t: _action_items(t),
    "decisions": lambda t: _action_items(t),
    "tasks": lambda t: _action_items(t),
}


# Fields that should preserve original casing (extractive), not be lowercased.
_EXTRACTIVE = {"summary", "action_items", "decisions", "tasks"}


def _build_json(fields: list[str], prompt: str) -> dict[str, Any]:
    content = _user_content(prompt)
    text = content.lower()
    out: dict[str, Any] = {}
    for field in fields:
        key = field.lower()
        if key in _EXTRACTIVE:
            out[field] = _FIELD_BUILDERS[key](content) if key in _FIELD_BUILDERS else _summarize(content)
        elif key in _FIELD_BUILDERS:
            out[field] = _FIELD_BUILDERS[key](text)
        elif key in ("next_action", "recommended_action"):
            out[field] = _next_action(_lead_score(text))
        else:
            out[field] = _summarize(content)
    return out


def _free_text(prompt: str) -> str:
    urgent = _classify_urgency(prompt.lower()) == "high"
    opener = (
        "Thanks for reaching out - I understand this is time-sensitive and we're "
        "treating it as a priority. "
        if urgent
        else "Thanks for getting in touch. "
    )
    return (
        opener
        + "Here's a clear next step based on what you shared, written so it's ready "
        + "to send with light review. [mock provider output]"
    )


class MockProvider(Provider):
    name = "mock"

    @property
    def default_model(self) -> str:
        return "mock-1"

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        json_fields: list[str] | None = None,
    ) -> LLMResponse:
        if json_fields:
            payload = _build_json(json_fields, prompt)
            return LLMResponse(content=json.dumps(payload), model=self.model, raw=payload)
        return LLMResponse(content=_free_text(prompt), model=self.model)
