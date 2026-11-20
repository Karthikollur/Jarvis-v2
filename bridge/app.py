"""Run: uv run python -m uvicorn bridge.app:create_app --factory --host 127.0.0.1 --port 8765 --no-access-log"""

from collections.abc import Callable
from contextlib import asynccontextmanager
import csv
from dataclasses import asdict
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import tempfile
import threading
import time
from typing import Any
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, StrictBool
from starlette.datastructures import Headers

from bridge import hotkey as hotkeys
from bridge import tools
from safety.audit import AuditLog
from safety.confirm import ConfirmQueue, QueueRefused
from safety.policy import MAX_SECONDS, Policy, Task, load_names, load_roots, resolve_inside
from safety.undo import UndoLog, UndoRefused, UnknownRecord

# A 202 comes within MAX_SECONDS of the task start, and the core then polls /outcome
# for at most MAX_SECONDS. No honest reader asks after that, so a task is kept for 2x.
KEEP = 2 * MAX_SECONDS


def _run(*args: str) -> str:
    executable = Path(os.environ["SystemRoot"]) / "System32" / (args[0] + ".exe")
    if not executable.is_absolute():
        raise RuntimeError("SystemRoot must be absolute")
    result = subprocess.run((str(executable), *args[1:]), capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError("Bridge token ACL operation failed")
    return result.stdout


def protect(path: Path) -> None:
    """Remove inheritance, grant only this user, and verify the resulting DACL."""
    if os.name != "nt":
        raise RuntimeError("Bridge token storage requires Windows")
    sid = next(csv.reader([_run("whoami", "/user", "/fo", "csv", "/nh").strip()]))[1]
    if not re.fullmatch(r"S-1-[0-9-]+", sid):
        raise RuntimeError("Cannot determine current user SID")
    grant = f"*{sid}:" + ("(OI)(CI)F" if path.is_dir() else "F")
    _run("icacls", str(path), "/inheritance:r", "/grant:r", grant)
    # /grant:r replaces this user's ACE only. Reject any other explicit grant.
    fd, name = tempfile.mkstemp(dir=path if path.is_dir() else path.parent, suffix=".acl")
    os.close(fd)
    try:
        _run("icacls", str(path), "/save", name, "/q")
        descriptor = Path(name).read_text(encoding="utf-16-le")
        aces = re.findall(r"\(([^()]*)\)", descriptor)
        aliases = {"BA": "S-1-5-32-544", "SY": "S-1-5-18", "OW": "S-1-3-4", "WD": "S-1-1-0"}
        for trustee in {ace.split(";")[-1] for ace in aces} - {sid}:
            identity = aliases.get(trustee, trustee)
            _run("icacls", str(path), "/remove", "*" + identity)
        _run("icacls", str(path), "/save", name, "/q")
        descriptor = Path(name).read_text(encoding="utf-16-le")
        aces = re.findall(r"\(([^()]*)\)", descriptor)
        if not aces or any(ace.split(";")[-1] != sid for ace in aces):
            raise RuntimeError("Bridge token ACL is not user-only")
    finally:
        Path(name).unlink(missing_ok=True)


def load_token(storage: Path, name: str = "bridge.token") -> str:
    storage.mkdir(parents=True, exist_ok=True)
    if storage.is_symlink() or storage.is_junction():
        raise RuntimeError("Unsafe token storage")
    protect(storage)
    path = storage / name
    if path.is_symlink() or path.is_junction():
        raise RuntimeError("Unsafe token file")
    if not path.exists():
        with path.open("x", encoding="ascii") as handle:
            handle.write(secrets.token_hex(32))
    protect(path)
    token = path.read_text(encoding="ascii")
    if not re.fullmatch(r"[0-9a-f]{64}", token):
        raise RuntimeError("Invalid bridge token file")
    return token


# Which token role may call which path. "core" sends tool requests; "ui" is the only role
# that may see, approve or deny actions waiting for confirmation. Every route needs an entry.
ROUTE_ROLES: dict[str, set[str]] = {
    "/health": {"core", "ui"},
    "/task": {"core"},
    "/tool": {"core"},
    "/outcome": {"core"},
    "/pending": {"ui"},
    "/approve": {"ui"},
    "/deny": {"ui"},
    "/end": {"core"},
    "/stop": {"core", "ui"},  # stopping is the safe direction; core relays a spoken "stop"
    "/undo": {"ui"},  # only Karthik undoes; no model-facing undo tool
    "/resume": {"ui"},  # only Karthik lifts the latch a hotkey or UI Stop sets
}


class Authenticate:
    """Peer address, Host, token and role checks for every HTTP and WebSocket request."""

    def __init__(self, app, tokens: dict[str, str], audit: AuditLog) -> None:
        self.app = app
        self.tokens = tokens  # role -> token
        self.audit = audit

    def refusal(self, scope) -> tuple[int, str] | None:
        # The peer check holds even if the server is wrongly bound to another interface.
        client = scope.get("client")
        if not client or client[0] != "127.0.0.1":
            return 403, "Forbidden"
        headers = Headers(scope=scope)
        hosts = headers.getlist("host")
        if len(hosts) != 1 or not re.fullmatch(r"127\.0\.0\.1(?::[0-9]{1,5})?", hosts[0]):
            return 400, "Invalid host"
        sent = headers.getlist("x-jarvis-token")
        roles = [
            role
            for role, token in self.tokens.items()
            if len(sent) == 1 and hmac.compare_digest(sent[0].encode(), token.encode())
        ]
        if not roles:
            return 401, "Unauthorized"  # not logged: any local process could flood the file
        # A path missing from ROUTE_ROLES is open to nobody.
        if roles[0] not in ROUTE_ROLES.get(scope["path"], ()):
            self.audit.write("forbidden", role=roles[0], path=scope["path"])
            return 403, "Forbidden"
        scope.setdefault("state", {})["role"] = roles[0]  # read by /stop for the audit line
        return None

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] == "lifespan":
            await self.app(scope, receive, send)
            return
        if scope["type"] not in ("http", "websocket"):
            return  # unknown scope type: fail closed
        refused = self.refusal(scope)
        if refused is None:
            await self.app(scope, receive, send)
        elif scope["type"] == "websocket":
            await receive()  # websocket.connect
            await send({"type": "websocket.close", "code": 1008})
        else:
            response = JSONResponse({"detail": refused[1]}, status_code=refused[0])
            await response(scope, receive, send)


class ToolRequest(BaseModel):
    task_id: str
    tool: str
    args: dict[str, Any] = {}


class TaskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # The core has dropped the model's conversation context. Strict: only a JSON true counts.
    fresh_context: StrictBool = False


class PendingRequest(BaseModel):
    pending_id: str


class EndRequest(BaseModel):
    task_id: str


class UndoRequest(BaseModel):
    record_id: str


CONFIG = Path(__file__).resolve().parent.parent / "config"
FROM_CONFIG: Any = object()  # default for `hotkey`: read config/hotkey.toml


def create_app(
    storage: Path | None = None,
    roots: list[Path] | None = None,
    handlers: dict[str, Callable[[dict[str, Any]], Any]] | None = None,
    clock: Callable[[], float] = time.monotonic,
    hotkey: str | None = FROM_CONFIG,
    protected: list[Path] | None = None,
    apps: set[str] | None = None,
    scripts: set[str] | None = None,
) -> FastAPI:
    """`handlers` maps a tool name from safety.policy.TOOLS to the function that performs it.
    `hotkey` is the kill-switch combo; None (tests only) runs without one.
    `protected`: folders no tool may reach besides `storage`, which is always protected.
    None (production) means this repo folder; tests pass [] because their sandbox is in it.
    `apps`, `scripts`: names open_app / run_named_script accept. None (production) reads
    config/apps.toml and config/scripts.toml; a missing file allows nothing."""
    if storage is None:
        storage = Path(os.environ["LOCALAPPDATA"]) / "Jarvis"
    if roots is None:
        roots = load_roots(CONFIG / "allowed_roots.toml")
    if apps is None:
        apps = load_names(CONFIG / "apps.toml")
    if scripts is None:
        scripts = load_names(CONFIG / "scripts.toml")
    if hotkey is FROM_CONFIG:
        hotkey = hotkeys.load(CONFIG / "hotkey.toml")
    elif hotkey is not None:
        hotkeys.parse(hotkey)
    tokens = {"core": load_token(storage), "ui": load_token(storage, "ui.token")}
    audit_path = storage / "audit.jsonl"
    if audit_path.is_symlink() or audit_path.is_junction():
        raise RuntimeError("Unsafe audit log")
    audit_path.touch()
    protect(audit_path)
    audit = AuditLog(audit_path)
    audit.write("start")  # in-memory pending actions from an earlier run are gone
    repo = [CONFIG.parent] if protected is None else list(protected)
    policy = Policy(roots, clock, [storage, *repo], apps, scripts)
    queue = ConfirmQueue(clock)
    undo_log = UndoLog(storage / "quarantine")  # inside storage: protected, user-only ACL
    if handlers is None:  # production
        app_entries = tools.load_apps(CONFIG / "apps.toml")  # a bad entry stops the start
        scripts_cmds = tools.load_scripts(CONFIG / "scripts.toml")
        handlers = {**tools.HANDLERS, **tools.mutating(undo_log, app_entries, scripts_cmds)}
    handlers = dict(handlers)
    tasks: dict[str, Task] = {}  # evict() forgets a task once it is older than KEEP
    outcomes: dict[str, dict[str, Any]] = {}  # pending_id -> outcome; evict() forgets it with the task
    owners: dict[str, str] = {}  # pending_id -> task_id, so evict() can drop the outcome too
    # Untrusted text stays in the model's context after the task that read it, so a new
    # task starts tainted until the core declares `fresh_context` (P2.8). Every live task
    # is tainted with it (P2.9 R1). A start knows nothing about the model's context, so it
    # starts tainted: the core's first task after a start sends `fresh_context` (P2.9 R2).
    # ponytail: one flag = one conversation at a time; per-conversation ids if there are ever two
    context_tainted = True
    # Held while the flag is read or written and a task is inserted, so a taint arriving
    # mid-`/task` cannot miss the new task or be overwritten by a fresh_context. Never held
    # by `stop()`; never held across a handler.
    taint_lock = threading.Lock()
    # Latch set by a Stop from the hotkey or the UI: no new task and no tool call until a
    # ui-only /resume (P2.8). A bridge restart also clears it.
    halted = False
    listener = None  # the hotkey listener, started with the app

    @asynccontextmanager
    async def lifespan(_app):
        nonlocal listener
        # A combo that cannot be registered raises here: the bridge does not start.
        listener = hotkeys.listen(hotkey, lambda: stop("hotkey")) if hotkey else None
        try:
            yield
        finally:
            if listener:
                listener.close()

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.add_middleware(Authenticate, tokens=tokens, audit=audit)

    def log(event: str, **fields: Any) -> bool:
        """Write one audit line. False means it was not written: the caller fails closed."""
        try:
            audit.write(event, **fields)
        except Exception:  # any failure means no line (P2.9 R6), not only a full disk
            return False
        return True

    def unavailable() -> JSONResponse:
        return JSONResponse({"detail": "Audit log unavailable"}, status_code=500)

    def encoded(body: Any) -> Response:
        """ASCII-escaped JSON: a lone surrogate in a file name cannot be sent as UTF-8."""
        return Response(json.dumps(body, default=str), media_type="application/json")

    def execute(
        task_id: str, task: Task, tool: str, args: dict[str, Any], paths: dict[str, Path],
        pending_id: str | None = None,
    ):
        """The only place a tool handler is called. Reached from /tool and /approve only,
        always after the policy said yes and that was logged. Logs the result.
        Returns (response, outcome)."""
        nonlocal context_tainted
        handler = handlers.get(tool)
        if hotkey and (listener is None or not listener.alive()):
            # Same rule as at startup: no kill switch, no tools. Also true before the app
            # has started its listener and after it has shut down.
            stop("hotkey-dead")
            response = JSONResponse({"detail": "kill switch unavailable"}, status_code=503)
            outcome = logged = {"status": "cancelled"}
        elif task.stopped:  # Stop landed after the policy check (e.g. an approve past recheck)
            response = JSONResponse({"detail": "task stopped"}, status_code=403)
            outcome = logged = {"status": "cancelled"}
        elif handler is None:
            response = JSONResponse({"detail": "Tool not implemented"}, status_code=501)
            outcome, logged = {"status": "failed"}, {"status": "not_implemented"}
        else:
            try:
                result = handler({**args, **paths})  # resolved paths win
            except Exception as error:
                policy.record(task, tool, ok=False)
                response = JSONResponse({"detail": "Tool failed"}, status_code=500)
                # The error text is for Karthik's log only, never returned to the model.
                outcome = {"status": "failed"}
                logged = {"status": "failed", "error": f"{type(error).__name__}: {error}"}
            else:
                policy.record(task, tool, ok=True)
                if task.tainted:
                    with taint_lock:
                        context_tainted = True
                        for other in list(tasks.values()):
                            other.tainted = True
                try:
                    response = encoded({"result": result})
                except Exception as error:  # e.g. tuple keys: it ran, but cannot be reported
                    response = JSONResponse({"detail": "Tool failed"}, status_code=500)
                    outcome = {"status": "failed"}
                    reason = f"result not encodable: {type(error).__name__}: {error}"
                    logged = {"status": "failed", "error": reason}
                else:
                    outcome = logged = {"status": "done", "result": result}
        ids = {"pending_id": pending_id} if pending_id else {}
        if not log("result", task_id=task_id, tool=tool, **ids, **logged):
            task.stopped = True  # nothing further runs unlogged
            return unavailable(), outcome
        return response, outcome

    def settle(pending, outcome: dict[str, Any]) -> None:
        """Remember an outcome and which task it belongs to. evict() drops both together."""
        outcomes[pending.id] = outcome
        owners[pending.id] = pending.task_id

    def expire() -> bool:
        """Every pending action whose task ran out of time, or was stopped, leaves the queue.
        Out of time is `expired`. Stopped, and still in time, is `cancelled`.
        False if that could not be logged (the action stays queued; it can no longer run)."""
        for pending in queue.list():
            if policy.out_of_time(tasks[pending.task_id]):
                if not log("expired", pending_id=pending.id, task_id=pending.task_id, tool=pending.tool):
                    return False
                if queue.take(pending.id):
                    settle(pending, {"status": "expired"})
            elif tasks[pending.task_id].stopped:
                if not log("cancelled", pending_id=pending.id, task_id=pending.task_id, tool=pending.tool):
                    return False
                if queue.take(pending.id):
                    settle(pending, {"status": "cancelled"})
        return True

    def evict() -> None:
        """Forget tasks older than KEEP that have nothing queued, and their outcomes.

        An evicted outcome now answers 404 instead of 410.
        """
        old = {
            task_id
            for task_id, task in list(tasks.items())
            if clock() - task.started > KEEP and queue.for_task(task_id) is None
        }
        for task_id in list(old):
            tasks.pop(task_id, None)  # a second sweep may already have dropped it
        for pending_id, owner in list(owners.items()):
            if owner in old:
                outcomes.pop(pending_id, None)
                owners.pop(pending_id, None)

    def unknown_pending(pending_id: str) -> JSONResponse:
        status = outcomes.get(pending_id, {}).get("status")
        if status in ("expired", "cancelled"):
            return JSONResponse({"detail": f"Pending action {status}"}, status_code=410)
        return JSONResponse({"detail": "Unknown pending action"}, status_code=404)

    def stop(source: str) -> dict[str, Any]:
        """Kill switch: stop every task and cancel every pending action. The only stop path.
        Stops FIRST, logs after: stopping must never depend on the audit log (the one
        exception to write-before-run, since it only prevents actions).
        A Stop from anything but the core (hotkey, ui) also latches: see `halted`. A Stop the
        core relays (a spoken "stop") ends current tasks only."""
        nonlocal halted
        latched = source != "core"
        if latched:
            halted = True  # first, so a task created during the loop below is refused
        stopped = 0
        for task in list(tasks.values()):
            if not task.stopped:
                task.stopped = True
                stopped += 1
        dropped = queue.clear()
        for pending in dropped:
            settle(pending, {"status": "cancelled"})
        cancelled = [p.id for p in dropped]
        logged = log("stop", source=source, tasks=stopped, cancelled=cancelled, latched=latched)
        return {"stopped": stopped, "cancelled": len(dropped), "logged": logged}

    @app.post("/task")
    def new_task(request: TaskRequest | None = None):
        nonlocal context_tainted
        if not expire():
            return unavailable()  # no task made
        evict()
        if halted:
            if not log("task", refused="stopped"):
                return unavailable()
            return JSONResponse({"detail": "stopped"}, status_code=403)
        fresh = request is not None and request.fresh_context
        task_id = uuid.uuid4().hex
        with taint_lock:
            tainted = context_tainted and not fresh
            if not log("task", task_id=task_id, tainted=tainted, fresh_context=fresh):
                return unavailable()  # an unlogged fresh_context clears nothing
            context_tainted = tainted
            tasks[task_id] = policy.new_task(tainted)
        # A latching Stop that ran between the check above and the insert missed this task
        # (P2.9 R7). stop() sets `halted` before it walks `tasks`, so one side always sees
        # the other. Stop first, log after, as stop() does.
        if halted:
            tasks[task_id].stopped = True
            if not log("task", task_id=task_id, refused="stopped"):
                return unavailable()
            return JSONResponse({"detail": "stopped"}, status_code=403)
        return {"task_id": task_id}

    @app.post("/tool")
    def run_tool(request: ToolRequest):
        if not expire():
            return unavailable()
        request_line = {"task_id": request.task_id, "tool": request.tool, "args": request.args}
        if halted:
            if not log("request", **request_line, decision="deny", reason="stopped"):
                return unavailable()
            return JSONResponse({"detail": "stopped"}, status_code=403)
        task = tasks.get(request.task_id)
        if task is None:
            if not log("request", **request_line, decision="deny", reason="unknown task"):
                return unavailable()
            return JSONResponse({"detail": "Unknown task"}, status_code=404)
        # Checked first so a call made while an action waits still spends budget.
        decision = policy.check(task, request.tool, request.args)
        if not log(
            "request", **request_line, decision=decision.action, reason=decision.reason,
            tier=decision.tier.name if decision.tier is not None else None,
            paths=decision.paths, tainted=task.tainted,
        ):
            return unavailable()
        if decision.action == "deny":
            return JSONResponse({"detail": decision.reason}, status_code=403)
        if queue.for_task(request.task_id) is not None:
            if not log("queued", task_id=request.task_id, refused="awaiting confirmation"):
                return unavailable()
            return JSONResponse({"detail": "awaiting confirmation"}, status_code=409)
        if decision.action == "confirm":
            try:
                pending = queue.add(
                    request.task_id, request.tool, request.args, decision.paths, decision.reason
                )
            except QueueRefused as refused:
                if not log("queued", task_id=request.task_id, refused=str(refused)):
                    return unavailable()
                return JSONResponse({"detail": str(refused)}, status_code=403)
            if task.stopped:  # Stop landed between the policy check and the queue
                queue.take(pending.id)
                settle(pending, {"status": "cancelled"})
                ids = {"task_id": request.task_id, "pending_id": pending.id}
                if not log("queued", **ids, refused="task stopped"):
                    return unavailable()
                return JSONResponse({"detail": "task stopped"}, status_code=403)
            if not log("queued", task_id=request.task_id, pending_id=pending.id):
                queue.take(pending.id)  # an unlogged action must not be approvable
                return unavailable()
            return JSONResponse({"pending_id": pending.id}, status_code=202)
        return execute(request.task_id, task, request.tool, request.args, decision.paths)[0]

    @app.get("/pending")
    def list_pending():
        if not expire():
            return unavailable()
        now = clock()
        return encoded({  # one odd name must not hide every pending action (P2.9 R5)
            "pending": [
                {
                    "id": p.id,
                    "task_id": p.task_id,
                    "tool": p.tool,
                    "args": p.args,
                    "paths": {  # a batch (move_files) shows every source and landing
                        name: [str(item) for item in path] if isinstance(path, tuple) else str(path)
                        for name, path in p.paths.items()
                    },
                    "reason": p.reason,
                    "age": now - p.created,
                }
                for p in queue.list()
            ]
        })

    @app.post("/approve")
    def approve(request: PendingRequest):
        """Runs exactly the stored action, once, after re-validating it."""
        pending = queue.take(request.pending_id)
        if pending is None:
            return unknown_pending(request.pending_id)
        # Race: evict() can drop the task after take() and before this lookup.
        task = tasks.get(pending.task_id)
        ids = {"pending_id": pending.id, "task_id": pending.task_id, "tool": pending.tool}
        if task is None:
            if not log("approve", **ids, recheck="task gone"):
                return unavailable()
            return JSONResponse({"detail": "Pending action expired"}, status_code=410)
        settle(pending, {"status": "pending"})  # running: /outcome must not answer 404
        refused = policy.recheck(task, pending.tool, pending.args, pending.paths)
        if not log("approve", **ids, recheck=refused or "ok"):
            # Already taken out of the queue: it can never run.
            settle(pending, {"status": "denied"})
            return unavailable()
        if refused is not None:
            expired = policy.out_of_time(task)
            settle(pending, {"status": "expired" if expired else "denied"})
            return JSONResponse({"detail": refused}, status_code=410 if expired else 403)
        response, outcome = execute(
            pending.task_id, task, pending.tool, pending.args, pending.paths, pending.id
        )
        settle(pending, outcome)
        return response

    @app.post("/deny")
    def deny(request: PendingRequest):
        pending = queue.take(request.pending_id)
        if pending is None:
            return unknown_pending(request.pending_id)
        settle(pending, {"status": "denied"})
        if not log("deny", pending_id=pending.id, task_id=pending.task_id, tool=pending.tool):
            return unavailable()
        return {"status": "denied"}

    @app.post("/outcome")
    def outcome(request: PendingRequest):
        if not expire():
            return unavailable()
        if request.pending_id in outcomes:
            return encoded(outcomes[request.pending_id])
        if any(p.id == request.pending_id for p in queue.list()):
            return {"status": "pending"}
        return JSONResponse({"detail": "Unknown pending action"}, status_code=404)

    @app.post("/end")
    def end_task(request: EndRequest):
        """End one task and drop its queued action. Acts first, logs after.
        A handler that is already running is left to finish."""
        task = tasks.get(request.task_id)
        if task is None:
            if not log("end", task_id=request.task_id, refused="unknown task"):
                return unavailable()
            return JSONResponse({"detail": "Unknown task"}, status_code=404)
        task.stopped = True
        pending = queue.for_task(request.task_id)
        taken = queue.take(pending.id) if pending is not None else None
        if taken is not None:
            settle(taken, {"status": "cancelled"})
        logged = log(
            "end",
            task_id=request.task_id,
            cancelled=taken.id if taken is not None else None,
        )
        return {"status": "ended", "logged": logged}

    @app.post("/stop")
    def stop_route(request: Request):
        return stop(request.state.role)

    @app.post("/resume")
    def resume():
        """Lift the latch. Stopped tasks stay stopped; only new tasks can run."""
        nonlocal halted
        if not log("resume"):
            return unavailable()  # an unlogged resume resumes nothing
        halted = False
        return {"status": "resumed"}

    @app.get("/undo")
    def list_undo():
        return encoded({"records": [asdict(record) for record in undo_log.list()]})

    @app.post("/undo")
    def undo(request: UndoRequest):
        """Reverse one undo record. Logged before anything moves; refuses, never overwrites."""
        record_id = request.record_id
        try:
            record = undo_log.get(record_id)
        except UndoRefused:
            record = None  # undo() below raises the same refusal, after it is logged
        details = {}
        if record is not None:
            paths = {name: getattr(record, name) for name in ("path", "source", "destination")}
            details = {"kind": record.kind, "paths": {k: v for k, v in paths.items() if v}}
        if not log("undo", record_id=record_id, **details):
            return unavailable()

        def resolve(raw: str) -> Path:
            return resolve_inside(raw, policy.roots, policy.protected, mutating=True)

        try:
            done = undo_log.undo(record_id, resolve)
        except UndoRefused as refused:
            if not log("undo_result", record_id=record_id, status="refused", reason=str(refused)):
                return unavailable()
            status = 404 if isinstance(refused, UnknownRecord) else 409
            return JSONResponse({"detail": str(refused)}, status_code=status)
        if not log("undo_result", record_id=record_id, status="done"):
            return unavailable()
        return asdict(done)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app
