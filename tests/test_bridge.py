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
        for route in ["/docs", "/openapi.json", "/tools", "/tool/", "/health/"]:
            assert client.get(route, headers=headers).status_code == 403  # not in ROUTE_ROLES


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
        refused(client, good)  # a route with no entry in ROUTE_ROLES is open to nobody
        with patch.dict(bridge_app.ROUTE_ROLES, {"/ws": {"core"}}):
            with client.websocket_connect(url, headers=good) as connection:
                assert connection.receive_text() == "in"
            refused(client, {})
            refused(client, {"x-jarvis-token": "wrong"})
            refused(client, {"x-jarvis-token": load_token(storage, "ui.token")})
            refused(client, {**good, "host": "evil.example"})
            with TestClient(app, base_url=BASE, client=LAN_PEER) as lan:
                refused(lan, good)


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
def sandbox(storage, clock):
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
        "run_named_script": broken,
    }
    app = create_app(storage, roots=[root], handlers=handlers, clock=clock)
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
    assert table == {
        ("GET", "/health"),
        ("POST", "/task"),
        ("POST", "/tool"),
        ("GET", "/pending"),
        ("POST", "/approve"),
        ("POST", "/deny"),
        ("POST", "/outcome"),
    }
    assert {path for _, path in table} == set(bridge_app.ROUTE_ROLES)


def test_ui_token_cannot_request_tools(sandbox):
    client, root, outside = sandbox
    core = load_token(root.parent)
    ui = {"x-jarvis-token": load_token(root.parent, "ui.token")}
    assert core != ui["x-jarvis-token"]
    assert client.get("/health", headers=ui).status_code == 200
    assert client.post("/task", headers=ui).status_code == 403
    body = {"task_id": new_task(client), "tool": "create_folder", "args": {"path": str(root / "n")}}
    assert client.post("/tool", json=body, headers=ui).status_code == 403
    assert not (root / "n").exists()


def test_core_token_cannot_use_ui_only_route(sandbox):
    client, root, outside = sandbox
    ui = {"x-jarvis-token": load_token(root.parent, "ui.token")}
    with patch.dict(bridge_app.ROUTE_ROLES, {"/health": {"ui"}}):
        assert client.get("/health").status_code == 403  # client default is the core token
        assert client.get("/health", headers=ui).status_code == 200


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
    assert call(client, new_task(client), "delete_file", path=str(victim)).status_code == 202
    assert victim.exists()
    # Reading a file taints the task: the next T1 action needs confirmation too.
    task = new_task(client)
    assert call(client, task, "read_text_file", path=str(victim)).status_code == 200
    assert call(client, task, "create_folder", path=str(root / "new")).status_code == 202
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


# --- confirm queue (P2.3) ----------------------------------------------------


def ui_headers(root):
    return {"x-jarvis-token": load_token(root.parent, "ui.token")}


def approve(client, root, pending_id):
    return client.post("/approve", json={"pending_id": pending_id}, headers=ui_headers(root))


def deny(client, root, pending_id):
    return client.post("/deny", json={"pending_id": pending_id}, headers=ui_headers(root))


def outcome(client, pending_id):
    return client.post("/outcome", json={"pending_id": pending_id})


def queue_delete(client, root, name="victim.txt"):
    """Queue a delete of a real file; returns (victim, pending_id)."""
    victim = root / name
    victim.write_text("keep")
    response = call(client, new_task(client), "delete_file", path=str(victim))
    assert response.status_code == 202
    return victim, response.json()["pending_id"]


def test_approved_t2_action_runs_once(sandbox):
    client, root, outside = sandbox
    victim, pending_id = queue_delete(client, root)
    listed = client.get("/pending", headers=ui_headers(root)).json()["pending"]
    assert [(p["id"], p["tool"], p["reason"]) for p in listed] == [(pending_id, "delete_file", "T2")]
    assert listed[0]["args"] == {"path": str(victim)}
    assert listed[0]["paths"] == {"path": str(victim)}
    assert victim.exists()
    assert outcome(client, pending_id).json() == {"status": "pending"}
    assert approve(client, root, pending_id).status_code == 200
    assert not victim.exists()
    assert outcome(client, pending_id).json() == {"status": "done", "result": None}
    assert client.get("/pending", headers=ui_headers(root)).json() == {"pending": []}


def test_queue_routes_enforce_roles(sandbox):
    client, root, outside = sandbox
    victim, pending_id = queue_delete(client, root)
    body = {"pending_id": pending_id}
    assert client.get("/pending").status_code == 403  # client default is the core token
    assert client.post("/approve", json=body).status_code == 403
    assert client.post("/deny", json=body).status_code == 403
    assert client.post("/outcome", json=body, headers=ui_headers(root)).status_code == 403
    routes = [("GET", "/pending"), ("POST", "/approve"), ("POST", "/deny"), ("POST", "/outcome")]
    for method, path in routes:
        response = client.request(method, path, json=body, headers={"x-jarvis-token": ""})
        assert response.status_code == 401, path
    bare = TestClient(client.app, base_url=BASE, client=LOOPBACK)  # no token header at all
    for method, path in routes:
        assert bare.request(method, path, json=body).status_code == 401, path
    assert victim.exists()
    assert outcome(client, pending_id).json() == {"status": "pending"}


def test_approve_is_one_shot_and_ids_must_exist(sandbox):
    client, root, outside = sandbox
    victim, pending_id = queue_delete(client, root)
    assert approve(client, root, pending_id).status_code == 200
    victim.write_text("again")
    assert approve(client, root, pending_id).status_code == 404
    assert deny(client, root, pending_id).status_code == 404
    assert victim.exists()
    assert approve(client, root, "no-such-id").status_code == 404
    assert outcome(client, "no-such-id").status_code == 404


def test_denied_action_never_runs(sandbox):
    client, root, outside = sandbox
    victim, pending_id = queue_delete(client, root)
    assert deny(client, root, pending_id).status_code == 200
    assert approve(client, root, pending_id).status_code == 404
    assert victim.exists()
    assert outcome(client, pending_id).json() == {"status": "denied"}


def test_tainted_t1_waits_for_approval(sandbox):
    client, root, outside = sandbox
    (root / "a.txt").write_text("text")
    task = new_task(client)
    assert call(client, task, "read_text_file", path=str(root / "a.txt")).status_code == 200
    response = call(client, task, "create_folder", path=str(root / "new"))
    assert response.status_code == 202
    pending_id = response.json()["pending_id"]
    listed = client.get("/pending", headers=ui_headers(root)).json()["pending"]
    assert listed[0]["reason"] == "tainted T1"
    assert not (root / "new").exists()
    assert approve(client, root, pending_id).json() == {"result": "created"}
    assert (root / "new").is_dir()


def test_junction_swapped_in_while_waiting_is_refused(sandbox):
    client, root, outside = sandbox
    (root / "sub").mkdir()
    (outside / "victim.txt").write_text("outside")
    response = call(client, new_task(client), "delete_file", path=str(root / "sub" / "victim.txt"))
    assert response.status_code == 202
    pending_id = response.json()["pending_id"]
    (root / "sub").rmdir()
    _winapi.CreateJunction(str(outside), str(root / "sub"))
    refused = approve(client, root, pending_id)
    assert refused.status_code == 403
    assert "outside the allowed roots" in refused.json()["detail"]
    assert (outside / "victim.txt").read_text() == "outside"
    assert outcome(client, pending_id).json() == {"status": "denied"}


def test_waiting_past_the_task_window_expires(sandbox, clock):
    client, root, outside = sandbox
    victim, pending_id = queue_delete(client, root)
    clock.now = 121.0
    assert approve(client, root, pending_id).status_code == 410
    assert victim.exists()
    assert outcome(client, pending_id).json() == {"status": "expired"}


def test_timed_out_action_expires_without_approve(sandbox, clock):
    client, root, outside = sandbox
    queued = [queue_delete(client, root, f"v{i}.txt") for i in range(16)]
    victim, pending_id = queued[0]
    assert call(client, new_task(client), "delete_file", path=str(victim)).status_code == 403
    clock.now = 121.0
    assert client.get("/pending", headers=ui_headers(root)).json() == {"pending": []}
    assert outcome(client, pending_id).json() == {"status": "expired"}
    # Expired actions free their slots: a fresh task can queue again.
    assert call(client, new_task(client), "delete_file", path=str(victim)).status_code == 202
    assert approve(client, root, pending_id).status_code == 410
    assert deny(client, root, queued[1][1]).status_code == 410
    assert outcome(client, queued[1][1]).json() == {"status": "expired"}
    assert all(path.exists() for path, _ in queued)


def test_expiry_found_by_tool_call(sandbox, clock):
    """A task stopped for time by another call reports `expired`, not `denied`."""
    client, root, outside = sandbox
    victim = root / "v.txt"
    victim.write_text("keep")
    task = new_task(client)
    pending_id = call(client, task, "delete_file", path=str(victim)).json()["pending_id"]
    clock.now = 121.0
    stopped = call(client, task, "get_time")
    assert stopped.status_code == 403
    assert "time budget" in stopped.json()["detail"]
    assert approve(client, root, pending_id).status_code == 410
    assert victim.exists()
    assert outcome(client, pending_id).json() == {"status": "expired"}


def test_outcome_is_pending_while_handler_runs(storage, clock):
    root = Path(os.path.realpath(storage / "root"))
    root.mkdir()
    seen = {}

    def delete_file(args):
        seen["during"] = outcome(client, seen["id"]).json()  # core polls mid-run
        args["path"].unlink()

    app = create_app(storage, roots=[root], handlers={"delete_file": delete_file}, clock=clock)
    headers = {"x-jarvis-token": load_token(storage)}
    with TestClient(app, base_url=BASE, client=LOOPBACK, headers=headers) as client:
        victim, seen["id"] = queue_delete(client, root)
        assert approve(client, root, seen["id"]).status_code == 200
        assert seen["during"] == {"status": "pending"}
        assert outcome(client, seen["id"]).json() == {"status": "done", "result": None}
    assert not victim.exists()


def test_one_pending_per_task_and_global_cap(sandbox):
    client, root, outside = sandbox
    victim = root / "v.txt"
    victim.write_text("keep")
    task = new_task(client)
    assert call(client, task, "delete_file", path=str(victim)).status_code == 202
    second = call(client, task, "get_time")
    assert (second.status_code, second.json()["detail"]) == (409, "awaiting confirmation")
    for _ in range(15):
        assert call(client, new_task(client), "delete_file", path=str(victim)).status_code == 202
    refused = call(client, new_task(client), "delete_file", path=str(victim))
    assert refused.status_code == 403
    assert "too many" in refused.json()["detail"]
    assert len(client.get("/pending", headers=ui_headers(root)).json()["pending"]) == 16
    assert victim.exists()


def test_failing_handler_on_approve_counts_as_failure(sandbox):
    client, root, outside = sandbox
    task = new_task(client)
    for _ in range(3):
        response = call(client, task, "run_named_script", name="x")
        assert response.status_code == 202
        pending_id = response.json()["pending_id"]
        failed = approve(client, root, pending_id)
        assert failed.status_code == 500
        assert "blew up" not in failed.text
        assert outcome(client, pending_id).json() == {"status": "failed"}
    # Policy.record saw all three failures: the tool is now refused for this task.
    assert call(client, task, "run_named_script", name="x").status_code == 403
