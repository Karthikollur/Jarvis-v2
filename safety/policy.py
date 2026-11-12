"""Policy engine (P2.2): tiers, allowed roots, taint, budgets.

The bridge asks `Policy.check` before running any tool and calls `Policy.record`
afterwards. The model's opinion is never consulted. A tool that is not in `TOOLS`
does not exist (that is how tier T3 is expressed).

`check` answers one of:
  allow   - run it
  confirm - needs a human click in the UI (T2, or T1 on a tainted task)
  deny    - refused; the reason is safe to show
"""

from __future__ import annotations

import os
import re
import threading
import time
import tomllib
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Any

MAX_CALLS = 8  # tool calls per task
MAX_SECONDS = 120  # wall time per task
MAX_FAILURES = 3  # failures of one tool per task
MAX_TEXT = 200  # characters in a free-text argument


class Tier(IntEnum):
    T0 = 0  # read-only
    T1 = 1  # local and reversible
    T2 = 2  # destructive, outbound or code-running


@dataclass(frozen=True)
class Rule:
    tier: Tier
    path_params: tuple[str, ...] = ()  # arguments that must resolve inside an allowed root
    name_params: tuple[str, ...] = ()  # arguments that must be a bare file name
    taints: bool = False  # a successful call brings untrusted text into the task
    # (argument, allowlist): the value must be a name on that allowlist ("apps" or "scripts")
    choices: tuple[tuple[str, str], ...] = ()
    text_params: tuple[str, ...] = ()  # short plain text: MAX_TEXT, printable only

    @property
    def params(self) -> tuple[str, ...]:
        """Every argument the tool takes. All are required; anything else is refused."""
        listed = tuple(name for name, _ in self.choices)
        return (*self.path_params, *self.name_params, *listed, *self.text_params)


# One entry per tool. A new tool gets a new entry at the strictest tier that works.
TOOLS: dict[str, Rule] = {
    "get_time": Rule(Tier.T0),
    "list_windows": Rule(Tier.T0),
    "system_stats": Rule(Tier.T0),
    "list_dir": Rule(Tier.T0, ("path",)),
    "read_text_file": Rule(Tier.T0, ("path",), taints=True),
    "recall_memory": Rule(Tier.T0, text_params=("query",)),
    "open_app": Rule(Tier.T1, choices=(("app", "apps"),)),
    "focus_window": Rule(Tier.T1, text_params=("title",)),
    "create_folder": Rule(Tier.T1, ("path",)),
    "move_file": Rule(Tier.T1, ("source", "destination")),
    "rename_file": Rule(Tier.T1, ("path",), ("new_name",)),
    "delete_file": Rule(Tier.T2, ("path",)),
    "run_named_script": Rule(Tier.T2, choices=(("name", "scripts"),)),
}

_RESERVED = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"} | {
    f"{device}{number}" for device in ("COM", "LPT") for number in range(10)
}


class PathRefused(ValueError):
    pass


def _bad_component(part: str) -> bool:
    """Names Windows silently rewrites (trailing dot or space) or maps to a device."""
    if part in (".", ".."):
        return False
    return part.endswith((".", " ")) or part.split(".")[0].strip().upper() in _RESERVED


def _within(folded: str, folder: Path) -> bool:
    base = os.path.normcase(str(folder))
    return folded == base or folded.startswith(base + "\\")


def _refuse_mutation(folded: str, roots: list[Path], protected: list[Path]) -> None:
    """Extra refusals for a path a tool may change (T1/T2 and undo). `folded` is the
    resolved, normcased path; it is already inside a root and outside every protected
    folder. Raise PathRefused("the root itself") or PathRefused("contains a protected
    folder"); return None if the path may be changed."""
    if any(folded == os.path.normcase(str(root)) for root in roots):
        raise PathRefused("the root itself")
    if any(_within(os.path.normcase(str(folder)), Path(folded)) for folder in protected):
        raise PathRefused("contains a protected folder")


def resolve_inside(
    raw: Any, roots: list[Path], protected: list[Path] = (), mutating: bool = False
) -> Path:
    """Return the fully resolved path, or raise PathRefused if it is not inside a root
    or is inside a protected folder (audit point 9). Roots and protected folders must
    already be realpath-resolved.

    `mutating` is for a path the caller may move, rename, delete or create: the root
    itself and a folder that contains a protected folder are refused too (P2.8).

    Callers must use the returned path, never the raw string.
    """
    if not isinstance(raw, str) or not raw or "\0" in raw:
        raise PathRefused("not a path")
    text = raw.replace("/", "\\")
    if text.startswith("\\\\"):  # \\server\share, \\?\ and \\.\
        raise PathRefused("UNC and device paths are not allowed")
    if not re.match(r"[A-Za-z]:\\", text):
        raise PathRefused("path must be absolute with a drive letter")
    if ":" in text[2:]:
        raise PathRefused("alternate data streams are not allowed")
    if any(_bad_component(part) for part in text[3:].split("\\")):
        raise PathRefused("reserved or ambiguous file name")
    # Before any file-system call: a drive with no root on it is never touched, so a
    # mapped network drive is never contacted (P2.8).
    if not any(str(root)[:2].upper() == text[:2].upper() for root in roots):
        raise PathRefused("outside the allowed roots")
    # realpath collapses `..` and follows symlinks and junctions, also for a
    # path whose last components do not exist yet.
    resolved = os.path.realpath(text)
    folded = os.path.normcase(resolved)
    if not any(_within(folded, root) for root in roots):
        raise PathRefused("outside the allowed roots")
    if any(_within(folded, folder) for folder in protected):
        raise PathRefused("protected folder")
    if mutating:
        _refuse_mutation(folded, roots, protected)
    return Path(resolved)


def load_roots(config: Path) -> list[Path]:
    """Read config/allowed_roots.toml. Only Karthik edits that file."""
    roots = []
    for entry in tomllib.loads(config.read_text(encoding="utf-8")).get("root", []):
        raw = entry["path"]
        if not isinstance(raw, str) or not re.fullmatch(r"[A-Za-z]:\\[^\\].*", raw):
            raise ValueError(f"allowed root must be an absolute folder below a drive: {raw!r}")
        roots.append(Path(os.path.realpath(raw)))
    return roots


def load_names(config: Path) -> frozenset[str]:
    """Read an allowlist (config/apps.toml, config/scripts.toml): one `[name]` table per
    entry. A missing file allows nothing. Only Karthik edits those files."""
    if not config.exists():
        return frozenset()
    entries = tomllib.loads(config.read_text(encoding="utf-8"))
    for name, entry in entries.items():
        if not re.fullmatch(r"[a-z0-9_]{1,32}", name) or not isinstance(entry, dict):
            raise ValueError(f"{config.name}: every entry must be a [lower_case_name] table: {name!r}")
    return frozenset(entries)


@dataclass
class Task:
    started: float
    calls: int = 0
    tainted: bool = False
    stopped: bool = False
    failures: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class Decision:
    action: str  # "allow" | "confirm" | "deny"
    reason: str = ""
    tier: Tier | None = None  # effective tier, after taint
    paths: dict[str, Path] = field(default_factory=dict)  # resolved path arguments


class Policy:
    def __init__(
        self,
        roots: list[Path],
        clock: Callable[[], float] = time.monotonic,
        protected: list[Path] = (),
        apps: Iterable[str] = (),
        scripts: Iterable[str] = (),
    ) -> None:
        self.roots = roots
        self.clock = clock
        # Names the model may pass to open_app / run_named_script. Empty = nothing allowed.
        self.allowed = {"apps": frozenset(apps), "scripts": frozenset(scripts)}
        # Resolved once, like roots, so a junction or 8.3 name in the given path cannot dodge it.
        self.protected = [Path(os.path.realpath(folder)) for folder in protected]
        # Routes run in a thread pool: check, recheck and record each run whole under
        # this lock, so two calls for one task cannot both pass a budget. Not re-entrant:
        # `_stop` and `out_of_time` must never take it. Never held across a handler.
        # ponytail: global lock, per-task locks if throughput matters
        self._lock = threading.Lock()

    def new_task(self) -> Task:
        return Task(started=self.clock())

    def out_of_time(self, task: Task) -> bool:
        """Read-only: True once the task's wall-time budget is spent. Stops nothing."""
        return self.clock() - task.started > MAX_SECONDS

    def _stop(self, task: Task, reason: str) -> Decision:
        task.stopped = True
        return Decision("deny", reason)

    def check(self, task: Task, tool: Any, args: Any) -> Decision:
        """Decide one tool request. Every request counts against the budget, refused or not."""
        with self._lock:
            return self._check(task, tool, args)

    def _check(self, task: Task, tool: Any, args: Any) -> Decision:
        if task.stopped:
            return Decision("deny", "task stopped")
        if self.out_of_time(task):
            return self._stop(task, f"time budget exceeded ({MAX_SECONDS} s)")
        if task.calls >= MAX_CALLS:
            return self._stop(task, f"call budget exceeded ({MAX_CALLS} tool calls)")
        task.calls += 1
        rule = TOOLS.get(tool) if isinstance(tool, str) else None
        if rule is None:
            return Decision("deny", "unknown tool")
        if task.failures.get(tool, 0) >= MAX_FAILURES:
            return self._stop(task, f"{tool} failed {MAX_FAILURES} times")
        if not isinstance(args, dict):
            return Decision("deny", "arguments must be an object")
        if set(args) - set(rule.params):  # undeclared: a handler must never see it
            return Decision("deny", "unknown argument")
        try:
            paths = self._resolve(rule, args)
        except PathRefused as refused:
            return Decision("deny", str(refused))
        for name, listed in rule.choices:
            value = args.get(name)
            if not isinstance(value, str) or value not in self.allowed[listed]:
                return Decision("deny", f"{name}: not on the allowlist")
        for name in rule.text_params:
            value = args.get(name)
            # isprintable: no control, format (e.g. right-to-left override) or separator characters
            if not isinstance(value, str) or not 0 < len(value) <= MAX_TEXT or not value.isprintable():
                return Decision("deny", f"{name}: must be short plain text")
        tier = Tier.T2 if rule.tier is Tier.T1 and task.tainted else rule.tier
        if tier is Tier.T2:
            reason = "T2" if rule.tier is Tier.T2 else "tainted T1"
            return Decision("confirm", reason, tier, paths)
        return Decision("allow", "", tier, paths)

    def recheck(
        self, task: Task, tool: str, args: dict[str, Any], paths: dict[str, Path]
    ) -> str | None:
        """Re-validate a confirmed action at approve time. None means it may run.

        Does not count against the call budget: the request was counted when it was made.
        Waiting for the click counts against the time budget. Every path argument must
        still resolve to exactly the path shown when it was queued, so a junction swapped
        in while it waited is refused.
        """
        with self._lock:
            return self._recheck(task, tool, args, paths)

    def _recheck(
        self, task: Task, tool: str, args: dict[str, Any], paths: dict[str, Path]
    ) -> str | None:
        if task.stopped:
            return "task stopped"
        if self.out_of_time(task):
            return self._stop(task, f"time budget exceeded ({MAX_SECONDS} s)").reason
        rule = TOOLS.get(tool)
        if rule is None:
            return "unknown tool"
        try:
            now = self._resolve(rule, args)
        except PathRefused as refused:
            return str(refused)
        for name, path in now.items():
            if path != paths.get(name):
                label = rule.name_params[0] if name == "target" else name
                return f"{label}: changed since the request"
        return None

    def _resolve(self, rule: Rule, args: dict[str, Any]) -> dict[str, Path]:
        """Every path a call may touch, resolved and checked; PathRefused names the argument.
        A name parameter also yields `target`: where the renamed item lands, next to the
        first path parameter. Handlers use `target`, never build it themselves."""
        mutating = rule.tier >= Tier.T1
        paths = {}
        for name in rule.path_params:
            try:
                paths[name] = resolve_inside(args.get(name), self.roots, self.protected, mutating)
            except PathRefused as refused:
                raise PathRefused(f"{name}: {refused}") from None
        for name in rule.name_params:
            value = args.get(name)
            if (
                not isinstance(value, str)
                or not value
                or value in (".", "..")
                or re.search(r'[\\/:\0]', value)
                or _bad_component(value)
            ):
                raise PathRefused(f"{name}: must be a plain file name")
            landing = paths[rule.path_params[0]].parent / value
            try:
                paths["target"] = resolve_inside(str(landing), self.roots, self.protected, True)
            except PathRefused as refused:
                raise PathRefused(f"{name}: {refused}") from None
        return paths

    def record(self, task: Task, tool: str, ok: bool) -> None:
        """Report the outcome of a tool that ran."""
        with self._lock:
            if not ok:
                task.failures[tool] = task.failures.get(tool, 0) + 1
            elif TOOLS[tool].taints:
                task.tainted = True
