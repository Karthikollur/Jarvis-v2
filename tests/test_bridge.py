import _winapi
from pathlib import Path
import os
import subprocess
import tempfile
from unittest.mock import patch

import pytest
from fastapi import WebSocket
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from bridge.app import create_app, load_token
from bridge import app as bridge_app

BASE = "http://127.0.0.1:8765"
LOOPBACK = ("127.0.0.1", 50000)
LAN_PEER = ("192.168.1.5", 50000)


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
    with TestClient(app, base_url=BASE, client=LOOPBACK) as client:
        assert client.get("/health").status_code == 401
        assert client.get("/health", headers={"x-jarvis-token": "wrong"}).status_code == 401
        response = client.get("/health", headers=headers)
        assert response.json() == {"status": "ok"}
        assert "access-control-allow-origin" not in response.headers
        for host in ["localhost", "evil.example", "127.0.0.1.evil", "0.0.0.0"]:
            assert client.get("/health", headers={**headers, "host": host}).status_code == 400
        for route in ["/docs", "/openapi.json", "/tools"]:
            assert client.get(route, headers=headers).status_code == 404


def test_non_loopback_peer_refused(storage):
    app = create_app(storage)
    headers = {"x-jarvis-token": load_token(storage)}
    with TestClient(app, base_url=BASE, client=LAN_PEER) as client:
        assert client.get("/health", headers=headers).status_code == 403


def test_websocket_goes_through_auth(storage):
    app = create_app(storage)

    @app.websocket("/ws")
    async def ws(websocket: WebSocket):
        await websocket.accept()
        await websocket.send_text("in")
        await websocket.close()

    good = {"x-jarvis-token": load_token(storage)}
    url = "ws://127.0.0.1:8765/ws"  # TestClient ignores base_url for WebSockets

    def refused(client, headers):
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(url, headers=headers):
                pass

    with TestClient(app, base_url=BASE, client=LOOPBACK) as client:
        with client.websocket_connect(url, headers=good) as connection:
            assert connection.receive_text() == "in"
        refused(client, {})
        refused(client, {"x-jarvis-token": "wrong"})
        refused(client, {**good, "host": "evil.example"})
    with TestClient(app, base_url=BASE, client=LAN_PEER) as client:
        refused(client, good)


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


# --- tool dispatch through the policy engine ---------------------------------


@pytest.fixture
def sandbox(storage):
    """(client, root, outside): a bridge with fake tools and one allowed root."""
    root = Path(os.path.realpath(storage / "root"))
    outside = storage / "outside"
    root.mkdir()
    outside.mkdir()

    def create_folder(args):
        args["path"].mkdir()
        return "created"

    def broken(args):
        raise RuntimeError("tool blew up")

    handlers = {
        "create_folder": create_folder,
        "read_text_file": lambda args: "file text",
        "get_time": lambda args: "now",
        "delete_file": lambda args: args["path"].unlink(),
        "system_stats": broken,
    }
    app = create_app(storage, roots=[root], handlers=handlers)
    headers = {"x-jarvis-token": load_token(storage)}
    with TestClient(app, base_url=BASE, client=LOOPBACK, headers=headers) as client:
        yield client, root, outside


def new_task(client):
    return client.post("/task").json()["task_id"]


def call(client, task, tool, **args):
    return client.post("/tool", json={"task_id": task, "tool": tool, "args": args})


def test_route_table_is_exact(storage):
    """Every route is listed here on purpose. A new route must be added deliberately."""
    app = create_app(storage, roots=[])
    assert all(type(route) is APIRoute for route in app.routes)
    table = {(method, route.path) for route in app.routes for method in route.methods}
    assert table == {("GET", "/health"), ("POST", "/task"), ("POST", "/tool")}


def test_tool_runs_inside_root(sandbox):
    client, root, outside = sandbox
    response = call(client, new_task(client), "create_folder", path=str(root / "new"))
    assert response.status_code == 200
    assert response.json() == {"result": "created"}
    assert (root / "new").is_dir()


def test_tool_cannot_act_outside_root(sandbox):
    client, root, outside = sandbox
    _winapi.CreateJunction(str(outside), str(root / "jump"))
    for path in [
        str(root / ".." / "outside" / "x"),
        str(outside / "x"),
        str(root / "jump" / "x"),
        "\\?\\" + str(outside / "x"),
    ]:
        response = call(client, new_task(client), "create_folder", path=path)
        assert response.status_code == 403, path
    assert list(outside.iterdir()) == []


def test_dispatch_needs_token(sandbox):
    client, root, outside = sandbox
    task = new_task(client)
    wrong = {"x-jarvis-token": "wrong"}
    assert client.post("/task", headers=wrong).status_code == 401
    body = {"task_id": task, "tool": "create_folder", "args": {"path": str(root / "new")}}
    assert client.post("/tool", json=body, headers=wrong).status_code == 401
    assert not (root / "new").exists()


def test_confirm_actions_do_not_run(sandbox):
    client, root, outside = sandbox
    victim = root / "keep.txt"
    victim.write_text("keep")
    task = new_task(client)
    assert call(client, task, "delete_file", path=str(victim)).status_code == 409
    assert victim.exists()
    # Reading a file taints the task: the next T1 action needs confirmation too.
    assert call(client, task, "read_text_file", path=str(victim)).status_code == 200
    assert call(client, task, "create_folder", path=str(root / "new")).status_code == 409
    assert not (root / "new").exists()


def test_budget_breach_over_http(sandbox):
    client, root, outside = sandbox
    task = new_task(client)
    for _ in range(8):
        assert call(client, task, "get_time").status_code == 200
    assert call(client, task, "get_time").status_code == 403


def test_failing_tool_is_stopped_after_three_tries(sandbox):
    client, root, outside = sandbox
    task = new_task(client)
    for _ in range(3):
        response = call(client, task, "system_stats")
        assert response.status_code == 500
        assert "blew up" not in response.text
    assert call(client, task, "system_stats").status_code == 403


def test_dispatch_refusals(sandbox):
    client, root, outside = sandbox
    assert call(client, "no-such-task", "get_time").status_code == 404
    task = new_task(client)
    assert call(client, task, "shell_exec", command="dir").status_code == 403
    assert call(client, task, "list_windows").status_code == 501  # in policy, no handler yet
    assert client.post("/tool", json={"tool": "get_time"}).status_code == 422
