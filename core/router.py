"""Deterministic fast path (P1.5): the most common commands skip the LLM.

`route(text)` returns `(tool_name, args)` for an exact, whole-utterance match and
`None` for everything else, which then goes to the model. It never guesses: a
near-miss must fall through.

The result is a tool REQUEST like any the model makes. It still goes through the
bridge and the policy engine; nothing here grants permission.
"""

from __future__ import annotations

import re
from typing import Any

# ponytail: aliases are hardcoded; move them next to the allowlist in
# config/apps.toml when that file exists (P3.2).
APP_ALIASES = {
    "vs code": "vscode",
    "vscode": "vscode",
    "visual studio code": "vscode",
    "notepad": "notepad",
    "calculator": "calculator",
    "calc": "calculator",
    "browser": "browser",
    "web browser": "browser",
    "explorer": "explorer",
    "file explorer": "explorer",
}

_WAKE = re.compile(r"^(hey |ok |okay )?jarvis[, ]+")
_TIME = re.compile(
    r"what time is it|what(?:'s| is) the time|(?:tell me )?the time"
    r"|what(?:'s| is) (?:today's|the) date|what day is it"
)
_STOP = re.compile(r"(?:stop|cancel|abort|halt)(?: it| that| now| everything)?")
_OPEN = re.compile(r"(?:open|launch|start)(?: up)? (?:the |my )?(?P<app>.+)")


def route(text: str) -> tuple[str, dict[str, Any]] | None:
    said = " ".join(text.lower().split()).rstrip(".!? ")
    said = _WAKE.sub("", said).removesuffix(" please")
    if _STOP.fullmatch(said):
        return ("stop", {})  # kill switch; wired to the bridge in P2.5
    if _TIME.fullmatch(said):
        return ("get_time", {})
    opened = _OPEN.fullmatch(said)
    if opened and opened["app"] in APP_ALIASES:
        return ("open_app", {"app": APP_ALIASES[opened["app"]]})
    return None
