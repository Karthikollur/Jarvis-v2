"""Run: uv run python -m uvicorn bridge.app:create_app --factory --host 127.0.0.1 --port 8765 --no-access-log"""

from collections.abc import Callable
import csv
import hmac
import os
from pathlib import Path
import re
import secrets
import subprocess
import tempfile
import time
from typing import Any
import uuid

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.datastructures import Headers

from safety.confirm import ConfirmQueue, QueueRefused
from safety.policy import Policy, Task, load_roots


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
}


class Authenticate:
    """Peer address, Host, token and role checks for every HTTP and WebSocket request."""

    def __init__(self, app, tokens: dict[str, str]) -> None:
        self.app = app
        self.tokens = tokens  # role -> token

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
            return 401, "Unauthorized"
        # A path missing from ROUTE_ROLES is open to nobody.
        if roles[0] not in ROUTE_ROLES.get(scope["path"], ()):
            return 403, "Forbidden"
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


class PendingRequest(BaseModel):
    pending_id: str


def create_app(
    storage: Path | None = None,
    roots: list[Path] | None = None,
    handlers: dict[str, Callable[[dict[str, Any]], Any]] | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> FastAPI:
    """`handlers` maps a tool name from safety.policy.TOOLS to the function that performs it."""
    if storage is None:
        storage = Path(os.environ["LOCALAPPDATA"]) / "Jarvis"
    if roots is None:
        roots = load_roots(Path(__file__).resolve().parent.parent / "config" / "allowed_roots.toml")
    tokens = {"core": load_token(storage), "ui": load_token(storage, "ui.token")}
    policy = Policy(roots, clock)
    queue = ConfirmQueue(clock)
    handlers = dict(handlers or {})
    tasks: dict[str, Task] = {}  # ponytail: never evicted; cap or expire when core is wired in
    outcomes: dict[str, dict[str, Any]] = {}  # pending_id -> outcome; ponytail: never evicted
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(Authenticate, tokens=tokens)

    def execute(task: Task, tool: str, args: dict[str, Any], paths: dict[str, Path]):
        """The only place a tool handler is called. Reached from /tool and /approve only,
        always after the policy said yes. Returns (response, outcome)."""
        handler = handlers.get(tool)
        if handler is None:
            return JSONResponse({"detail": "Tool not implemented"}, status_code=501), {"status": "failed"}
        try:
            result = handler({**args, **paths})  # resolved paths win
        except Exception:
            policy.record(task, tool, ok=False)
            return JSONResponse({"detail": "Tool failed"}, status_code=500), {"status": "failed"}
        policy.record(task, tool, ok=True)
        return {"result": result}, {"status": "done", "result": result}

    def expire() -> None:
        """Every pending action whose task ran out of time leaves the queue as `expired`."""
        for pending in queue.list():
            if policy.out_of_time(tasks[pending.task_id]) and queue.take(pending.id):
                outcomes[pending.id] = {"status": "expired"}

    def unknown_pending(pending_id: str) -> JSONResponse:
        if outcomes.get(pending_id, {}).get("status") == "expired":
            return JSONResponse({"detail": "Pending action expired"}, status_code=410)
        return JSONResponse({"detail": "Unknown pending action"}, status_code=404)

    @app.post("/task")
    def new_task():
        task_id = uuid.uuid4().hex
        tasks[task_id] = policy.new_task()
        return {"task_id": task_id}

    @app.post("/tool")
    def run_tool(request: ToolRequest):
        expire()
        task = tasks.get(request.task_id)
        if task is None:
            return JSONResponse({"detail": "Unknown task"}, status_code=404)
        # Checked first so a call made while an action waits still spends budget.
        decision = policy.check(task, request.tool, request.args)
        if decision.action == "deny":
            return JSONResponse({"detail": decision.reason}, status_code=403)
        if queue.for_task(request.task_id) is not None:
            return JSONResponse({"detail": "awaiting confirmation"}, status_code=409)
        if decision.action == "confirm":
            try:
                pending = queue.add(
                    request.task_id, request.tool, request.args, decision.paths, decision.reason
                )
            except QueueRefused as refused:
                return JSONResponse({"detail": str(refused)}, status_code=403)
            return JSONResponse({"pending_id": pending.id}, status_code=202)
        return execute(task, request.tool, request.args, decision.paths)[0]

    @app.get("/pending")
    def list_pending():
        expire()
        now = clock()
        return {
            "pending": [
                {
                    "id": p.id,
                    "task_id": p.task_id,
                    "tool": p.tool,
                    "args": p.args,
                    "paths": {name: str(path) for name, path in p.paths.items()},
                    "reason": p.reason,
                    "age": now - p.created,
                }
                for p in queue.list()
            ]
        }

    @app.post("/approve")
    def approve(request: PendingRequest):
        """Runs exactly the stored action, once, after re-validating it."""
        pending = queue.take(request.pending_id)
        if pending is None:
            return unknown_pending(request.pending_id)
        outcomes[pending.id] = {"status": "pending"}  # running: /outcome must not answer 404
        task = tasks[pending.task_id]
        refused = policy.recheck(task, pending.tool, pending.args, pending.paths)
        if refused is not None:
            expired = policy.out_of_time(task)
            outcomes[pending.id] = {"status": "expired" if expired else "denied"}
            return JSONResponse({"detail": refused}, status_code=410 if expired else 403)
        response, outcomes[pending.id] = execute(task, pending.tool, pending.args, pending.paths)
        return response

    @app.post("/deny")
    def deny(request: PendingRequest):
        pending = queue.take(request.pending_id)
        if pending is None:
            return unknown_pending(request.pending_id)
        outcomes[pending.id] = {"status": "denied"}
        return {"status": "denied"}

    @app.post("/outcome")
    def outcome(request: PendingRequest):
        expire()
        if request.pending_id in outcomes:
            return outcomes[request.pending_id]
        if any(p.id == request.pending_id for p in queue.list()):
            return {"status": "pending"}
        return JSONResponse({"detail": "Unknown pending action"}, status_code=404)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app
