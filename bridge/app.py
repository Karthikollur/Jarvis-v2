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
from typing import Any
import uuid

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.datastructures import Headers

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
# that will be allowed to approve them (P2.3). Every route needs an entry here.
ROUTE_ROLES: dict[str, set[str]] = {
    "/health": {"core", "ui"},
    "/task": {"core"},
    "/tool": {"core"},
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


def create_app(
    storage: Path | None = None,
    roots: list[Path] | None = None,
    handlers: dict[str, Callable[[dict[str, Any]], Any]] | None = None,
) -> FastAPI:
    """`handlers` maps a tool name from safety.policy.TOOLS to the function that performs it."""
    if storage is None:
        storage = Path(os.environ["LOCALAPPDATA"]) / "Jarvis"
    if roots is None:
        roots = load_roots(Path(__file__).resolve().parent.parent / "config" / "allowed_roots.toml")
    tokens = {"core": load_token(storage), "ui": load_token(storage, "ui.token")}
    policy = Policy(roots)
    handlers = dict(handlers or {})
    tasks: dict[str, Task] = {}  # ponytail: never evicted; cap or expire when core is wired in
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(Authenticate, tokens=tokens)

    @app.post("/task")
    def new_task():
        task_id = uuid.uuid4().hex
        tasks[task_id] = policy.new_task()
        return {"task_id": task_id}

    @app.post("/tool")
    def run_tool(request: ToolRequest):
        """The only place a tool handler is called. Do not call handlers anywhere else."""
        task = tasks.get(request.task_id)
        if task is None:
            return JSONResponse({"detail": "Unknown task"}, status_code=404)
        decision = policy.check(task, request.tool, request.args)
        if decision.action == "deny":
            return JSONResponse({"detail": decision.reason}, status_code=403)
        if decision.action != "allow":
            # No confirm queue yet (P2.3): anything needing confirmation does not run.
            return JSONResponse({"detail": "Needs confirmation"}, status_code=409)
        handler = handlers.get(request.tool)
        if handler is None:
            return JSONResponse({"detail": "Tool not implemented"}, status_code=501)
        try:
            result = handler({**request.args, **decision.paths})  # resolved paths win
        except Exception:
            policy.record(task, request.tool, ok=False)
            return JSONResponse({"detail": "Tool failed"}, status_code=500)
        policy.record(task, request.tool, ok=True)
        return {"result": result}

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app
