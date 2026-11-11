from pathlib import Path
import os
import subprocess
import tempfile
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from bridge.app import create_app, load_token
from bridge import app as bridge_app


@pytest.fixture
def storage():
    root = Path(__file__).resolve().parents[1] / ".test-storage"
    root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root) as directory:
        yield Path(directory)


def test_real_acl_and_persistence(storage):
    first = load_token(storage)
    assert len(first) == 64
    assert bool(first == load_token(storage))


def test_health_and_refusals(storage):
    app = create_app(storage)
    headers = {"x-jarvis-token": load_token(storage)}
    with TestClient(app, base_url="http://127.0.0.1:8765") as client:
        assert client.get("/health").status_code == 401
        assert client.get("/health", headers={"x-jarvis-token": "wrong"}).status_code == 401
        response = client.get("/health", headers=headers)
        assert response.json() == {"status": "ok"}
        assert "access-control-allow-origin" not in response.headers
        for host in ["localhost", "evil.example", "127.0.0.1.evil", "0.0.0.0"]:
            assert client.get("/health", headers={**headers, "host": host}).status_code == 400
        for route in ["/docs", "/openapi.json", "/tools"]:
            assert client.get(route, headers=headers).status_code == 404


def test_acl_failure_stops_startup(storage):
    with patch("bridge.app._run", side_effect=RuntimeError("ACL failed")):
        with pytest.raises(RuntimeError, match="ACL failed"):
            create_app(storage)
    assert not (storage / "bridge.token").exists()


def test_invalid_token_refused(storage):
    load_token(storage)
    (storage / "bridge.token").write_text("invalid", encoding="ascii")
    with pytest.raises(RuntimeError, match="Invalid bridge token"):
        create_app(storage)


def test_everyone_grant_removed(storage):
    load_token(storage)
    token_path = storage / "bridge.token"
    icacls = str(Path(os.environ["SystemRoot"]) / "System32" / "icacls.exe")

    def run_acl(*args):
        subprocess.run([icacls, str(token_path), *args], check=True, capture_output=True)

    saved = storage / "check.acl"
    run_acl("/grant", "*S-1-1-0:R")
    run_acl("/save", str(saved), "/q")
    assert ";;;WD)" in saved.read_text(encoding="utf-16-le")
    load_token(storage)
    run_acl("/save", str(saved), "/q")
    descriptor = saved.read_text(encoding="utf-16-le")
    assert ";;;WD)" not in descriptor
    assert ";;;S-1-1-0)" not in descriptor


def test_foreign_ace_in_verification_refused(storage):
    original_run = bridge_app._run
    saves = 0

    def foreign_verification(*args):
        nonlocal saves
        result = original_run(*args)
        if "/save" in args:
            saves += 1
            if saves == 2:
                saved = Path(args[args.index("/save") + 1])
                with saved.open("a", encoding="utf-16-le") as handle:
                    handle.write("(A;;FR;;;S-1-1-0)")
        return result

    with patch("bridge.app._run", side_effect=foreign_verification):
        with pytest.raises(RuntimeError, match="not user-only"):
            load_token(storage)
    assert not (storage / "bridge.token").exists()
