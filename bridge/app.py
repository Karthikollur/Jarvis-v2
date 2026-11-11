"""Run: uv run python -m uvicorn bridge.app:create_app --factory --host 127.0.0.1 --port 8765 --no-access-log"""

import csv
import hmac
import os
from pathlib import Path
import re
import secrets
import subprocess
import tempfile

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


def _run(*args: str) -> str:
    result = subprocess.run(args, capture_output=True, text=True, check=False)
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
        aliases = {"BA": "S-1-5-32-544", "SY": "S-1-5-18", "OW": "S-1-3-4"}
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


def load_token(storage: Path) -> str:
    storage.mkdir(parents=True, exist_ok=True)
    if storage.is_symlink() or storage.is_junction():
        raise RuntimeError("Unsafe token storage")
    protect(storage)
    path = storage / "bridge.token"
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


def create_app(storage: Path | None = None) -> FastAPI:
    if storage is None:
        storage = Path(os.environ["LOCALAPPDATA"]) / "Jarvis"
    token = load_token(storage)
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def authenticate(request: Request, call_next):
        hosts = request.headers.getlist("host")
        if len(hosts) != 1 or not re.fullmatch(r"127\.0\.0\.1(?::[0-9]{1,5})?", hosts[0]):
            return JSONResponse({"detail": "Invalid host"}, status_code=400)
        tokens = request.headers.getlist("x-jarvis-token")
        if len(tokens) != 1 or not hmac.compare_digest(tokens[0].encode(), token.encode()):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        return await call_next(request)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app
