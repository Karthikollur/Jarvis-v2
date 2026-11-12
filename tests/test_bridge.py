import _winapi
from pathlib import Path
import os
import subprocess
import tempfile
import threading
from unittest.mock import patch

import pytest
from fastapi import WebSocket
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import json

from bridge.app import create_app, load_token
from bridge import app as bridge_app
from safety.audit import AuditLog
from safety.confirm import ConfirmQueue
from safety.policy import MAX_CALLS, TOOLS, Policy
from safety.undo import UndoLog

BASE = "http://127.0.0.1:8765"
LOOPBACK = ("127.0.0.1", 50000)
LAN_PEER = ("192.168.1.5", 50000)


@pytest.fixture
def storage():
    root = Path(__file__).resolve().parents[1] / ".test-storage"
    root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root) as directory:
        # Storage is a subfolder: sandbox roots sit beside it, never inside (it is protected).
        (Path(directory) / "storage").mkdir()
        yield Path(directory) / "storage"


def store(root):
    """The storage folder of a sandbox bridge, which sits beside its root."""
    return root.parent / "storage"


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
    root = Path(os.path.realpath(storage.parent / "root"))
    outside = storage.parent / "outside"
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
    app = create_app(
        storage, roots=[root], handlers=handlers, clock=clock, protected=[],
        apps={"notepad"}, scripts={"x"},
    )
    headers = {"x-jarvis-token": load_token(storage)}
    with TestClient(app, base_url=BASE, client=LOOPBACK, headers=headers) as client:
        yield client, root, outside


def new_task(client):
    return client.post("/task").json()["task_id"]


def fresh_task(client):
    """A task with a clean context, as the core opens its first task after a bridge start
    (P2.9 R2: a bridge starts tainted)."""
    response = client.post("/task", json={"fresh_context": True})
    assert response.status_code == 200
    return response.json()["task_id"]


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
        ("POST", "/stop"),
        ("POST", "/resume"),
        ("GET", "/undo"),
        ("POST", "/undo"),
    }
    assert {path for _, path in table} == set(bridge_app.ROUTE_ROLES)


def test_ui_token_cannot_request_tools(sandbox):
    client, root, outside = sandbox
    core = load_token(store(root))
    ui = {"x-jarvis-token": load_token(store(root), "ui.token")}
    assert core != ui["x-jarvis-token"]
    assert client.get("/health", headers=ui).status_code == 200
    assert client.post("/task", headers=ui).status_code == 403
    body = {"task_id": new_task(client), "tool": "create_folder", "args": {"path": str(root / "n")}}
    assert client.post("/tool", json=body, headers=ui).status_code == 403
    assert not (root / "n").exists()


def test_core_token_cannot_use_ui_only_route(sandbox):
    client, root, outside = sandbox
    ui = {"x-jarvis-token": load_token(store(root), "ui.token")}
    with patch.dict(bridge_app.ROUTE_ROLES, {"/health": {"ui"}}):
        assert client.get("/health").status_code == 403  # client default is the core token
        assert client.get("/health", headers=ui).status_code == 200


def test_tool_runs_inside_root(sandbox):
    client, root, outside = sandbox
    response = call(client, fresh_task(client), "create_folder", path=str(root / "new"))
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
        # Real device and UNC forms, refused before any resolution (no network lookup).
        "\\\\?\\" + str(outside / "x"),
        "\\\\.\\" + str(outside / "x"),
        "\\\\server\\share\\x",
        "//server/share/x",
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


# --- sweeps (P2.7): driven by the live tables, so a route or tool added later is covered


BAD_TOKENS = [
    None,  # no header
    "",
    "wrong",
    "0" * 64,  # right length and alphabet, wrong value
]


def test_every_route_needs_a_token_and_loopback(sandbox, storage):
    client, root, outside = sandbox
    app = client.app
    task = new_task(client)
    tokens = {"core": load_token(storage), "ui": load_token(storage, "ui.token")}
    before = (storage / "audit.jsonl").read_bytes()
    routes = [(method, route.path) for route in app.routes for method in sorted(route.methods)]
    assert {path for _, path in routes} == set(bridge_app.ROUTE_ROLES)  # nothing skipped
    body = {"task_id": task, "tool": "get_time", "args": {}, "pending_id": "x", "record_id": "x"}
    # Not entered with `with`: the app (and its hotkey listener) is started once, by `sandbox`.
    anyone = TestClient(app, base_url=BASE, client=LOOPBACK)
    remote = TestClient(app, base_url=BASE, client=LAN_PEER)
    for method, path in routes:
        for bad in BAD_TOKENS:
            headers = {} if bad is None else {"x-jarvis-token": bad}
            response = anyone.request(method, path, json=body, headers=headers)
            assert response.status_code == 401, (method, path, bad)
        role = sorted(bridge_app.ROUTE_ROLES[path])[0]  # a token this route accepts
        valid = {"x-jarvis-token": tokens[role]}
        response = remote.request(method, path, json=body, headers=valid)
        assert response.status_code == 403, (method, path, "non-loopback")
    # Nothing ran and nothing was logged: the task is still live and can still call.
    assert (storage / "audit.jsonl").read_bytes() == before
    assert call(client, task, "get_time").status_code == 200


@pytest.fixture
def every_tool(storage, clock):
    """(client, root, outside, protected, ran): every tool in TOOLS has a handler that
    records it ran, so a refusal that leaks through is visible."""
    root = Path(os.path.realpath(storage.parent / "root"))
    outside = storage.parent / "outside"
    protected = root / "protected"
    for folder in (root, outside, protected):
        folder.mkdir()
    _winapi.CreateJunction(str(outside), str(root / "jump"))
    ran = []
    handlers = {name: (lambda args, name=name: ran.append(name)) for name in TOOLS}
    app = create_app(
        storage, roots=[root], handlers=handlers, clock=clock, protected=[protected],
        apps={"notepad"}, scripts={"x"},
    )
    headers = {"x-jarvis-token": load_token(storage)}
    with TestClient(app, base_url=BASE, client=LOOPBACK, headers=headers) as client:
        yield client, root, outside, protected, ran


ESCAPES = {
    "dotdot": lambda root, outside, protected: str(root / ".." / "outside" / "x"),
    "absolute": lambda root, outside, protected: str(outside / "x"),
    "junction": lambda root, outside, protected: str(root / "jump" / "x"),
    "unc": lambda root, outside, protected: "\\\\server\\share\\x",
    "protected": lambda root, outside, protected: str(protected / "x"),
}
PATH_PARAMS = [(tool, name) for tool, rule in TOOLS.items() for name in rule.path_params]


def test_path_sweep_is_not_vacuous():
    assert {tool for tool, _ in PATH_PARAMS} == {t for t, r in TOOLS.items() if r.path_params}
    assert ("move_file", "destination") in PATH_PARAMS
    assert any(TOOLS[tool].tier.name == "T2" for tool, _ in PATH_PARAMS)


@pytest.mark.parametrize("escape", ESCAPES)
@pytest.mark.parametrize("tool, param", PATH_PARAMS)
def test_every_path_parameter_is_checked(every_tool, tool, param, escape):
    client, root, outside, protected, ran = every_tool
    rule = TOOLS[tool]
    args = {name: str(root / f"ok-{name}") for name in rule.path_params}  # other params valid
    args |= {name: "ok.txt" for name in rule.name_params}
    args[param] = ESCAPES[escape](root, outside, protected)
    response = call(client, new_task(client), tool, **args)
    assert response.status_code == 403, response.text
    assert response.json()["detail"].startswith(f"{param}: ")
    assert ran == []
    assert client.get("/pending", headers=ui_headers(root)).json()["pending"] == []  # T2 too
    assert list(outside.iterdir()) == [] and list(protected.iterdir()) == []


# --- protected folders (P2.6, audit point 9) -----------------------------------


def acting_handlers(ran):
    """Handlers that really act, so a refusal is visible on disk."""
    def run(name, action):
        def handler(args):
            ran.append(name)
            return action(args["path"])
        return handler

    return {
        "read_text_file": run("read", lambda path: path.read_text()),
        "delete_file": run("delete", lambda path: path.unlink()),
        "create_folder": run("create", lambda path: path.mkdir()),
        "list_dir": run("list", lambda path: [p.name for p in path.iterdir()]),
    }


@pytest.mark.parametrize("protected", [[], None])
def test_storage_is_always_protected(storage, protected):
    """A root that contains the storage folder still cannot reach it, even with protected=[]."""
    root = Path(os.path.realpath(storage.parent))
    ran = []
    app = create_app(storage, roots=[root], handlers=acting_handlers(ran), protected=protected)
    token = load_token(storage)
    audit_before = (storage / "audit.jsonl").read_bytes()
    with TestClient(app, base_url=BASE, client=LOOPBACK, headers={"x-jarvis-token": token}) as client:
        for tool, path in [
            ("read_text_file", storage / "bridge.token"),
            ("read_text_file", storage / "ui.token"),
            ("delete_file", storage / "audit.jsonl"),
            ("create_folder", storage / "quarantine" / "new"),
            ("list_dir", storage),
            ("read_text_file", root / "storage" / ".." / "storage" / "bridge.token"),
        ]:
            response = call(client, new_task(client), tool, path=str(path))
            assert response.status_code == 403, (tool, path)
            assert response.json()["detail"] == "path: protected folder"
        if protected == []:  # outside storage the root still works
            assert call(client, fresh_task(client), "create_folder", path=str(root / "ok")).status_code == 200
    assert ran == ([] if protected is None else ["create"])
    assert load_token(storage) == token
    assert not (storage / "quarantine" / "new").exists()
    assert (storage / "audit.jsonl").read_bytes().startswith(audit_before)


def test_junction_into_storage_refused(storage):
    """The root contains storage, so only the protected check can refuse the junction."""
    root = Path(os.path.realpath(storage.parent))
    (root / "sub").mkdir()
    _winapi.CreateJunction(str(storage), str(root / "sub" / "jump"))
    ran = []
    app = create_app(storage, roots=[root], handlers=acting_handlers(ran), protected=[])
    with TestClient(app, base_url=BASE, client=LOOPBACK, headers={"x-jarvis-token": load_token(storage)}) as client:
        response = call(client, new_task(client), "read_text_file", path=str(root / "sub" / "jump" / "bridge.token"))
    assert response.status_code == 403
    assert response.json()["detail"] == "path: protected folder"
    assert ran == []


def test_repo_is_protected_by_default(storage):
    """protected=None (production) adds the whole repo folder, whatever the roots say."""
    repo = Path(__file__).resolve().parents[1]
    ran = []
    app = create_app(storage, roots=[repo], handlers=acting_handlers(ran))
    with TestClient(app, base_url=BASE, client=LOOPBACK, headers={"x-jarvis-token": load_token(storage)}) as client:
        for tool, path in [
            ("read_text_file", repo / "safety" / "policy.py"),
            ("read_text_file", repo / "config" / "allowed_roots.toml"),
            ("delete_file", repo / "bridge" / "app.py"),
            ("create_folder", repo / "config" / "new"),
            ("list_dir", repo),
        ]:
            response = call(client, new_task(client), tool, path=str(path))
            assert response.status_code == 403, (tool, path)
            assert response.json()["detail"] == "path: protected folder"
    assert ran == []
    assert (repo / "bridge" / "app.py").exists()
    assert not (repo / "config" / "new").exists()


# --- confirm queue (P2.3) ----------------------------------------------------


def ui_headers(root):
    return {"x-jarvis-token": load_token(store(root), "ui.token")}


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
    log = audit(root)
    approved = [e for e in log if e["event"] == "approve"]
    assert len(approved) == 1 and "outside the allowed roots" in approved[0]["recheck"]
    assert not [e for e in log if e["event"] == "result"]


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
    root = Path(os.path.realpath(storage.parent / "root"))
    root.mkdir()
    seen = {}

    def delete_file(args):
        seen["during"] = outcome(client, seen["id"]).json()  # core polls mid-run
        args["path"].unlink()

    app = create_app(storage, roots=[root], handlers={"delete_file": delete_file}, clock=clock, protected=[])
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


# --- audit log (P2.4) --------------------------------------------------------


def audit(root):
    """Every line of the audit log of the sandbox bridge (storage sits beside root)."""
    text = (store(root) / "audit.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines()]


def kinds(root):
    return [entry["event"] for entry in audit(root)]


def failing(*events):
    """Make AuditLog.write raise OSError for the named events only."""
    original = AuditLog.write

    def write(self, event, **fields):
        if event in events:
            raise OSError("disk full")
        return original(self, event, **fields)

    return patch.object(AuditLog, "write", write)


def test_audit_allowed_tool_logs_request_then_result(sandbox):
    client, root, outside = sandbox
    task = fresh_task(client)
    assert call(client, task, "create_folder", path=str(root / "new")).status_code == 200
    assert kinds(root) == ["start", "task", "request", "result"]
    _, created, request, result = audit(root)
    assert created["task_id"] == task
    assert request["ts"] <= result["ts"]
    assert {k: request[k] for k in ("task_id", "tool", "args", "decision", "tier", "paths", "tainted")} == {
        "task_id": task,
        "tool": "create_folder",
        "args": {"path": str(root / "new")},
        "decision": "allow",
        "tier": "T1",
        "paths": {"path": str(root / "new")},
        "tainted": False,
    }
    assert {k: result[k] for k in ("task_id", "tool", "status", "result")} == {
        "task_id": task, "tool": "create_folder", "status": "done", "result": "created",
    }


def test_audit_denied_requests_have_no_result(sandbox):
    client, root, outside = sandbox
    task = new_task(client)
    assert call(client, task, "create_folder", path=str(outside / "x")).status_code == 403
    assert call(client, task, "shell_exec", command="dir").status_code == 403
    assert call(client, "no-such-task", "get_time").status_code == 404
    requests = [e for e in audit(root) if e["event"] == "request"]
    assert [(r["decision"], r["reason"]) for r in requests] == [
        ("deny", "path: outside the allowed roots"),
        ("deny", "unknown tool"),
        ("deny", "unknown task"),
    ]
    assert requests[2]["task_id"] == "no-such-task"
    assert "result" not in kinds(root)
    assert not (outside / "x").exists()


def test_audit_t2_approve_flow(sandbox):
    client, root, outside = sandbox
    victim, pending_id = queue_delete(client, root)
    assert approve(client, root, pending_id).status_code == 200
    assert kinds(root) == ["start", "task", "request", "queued", "approve", "result"]
    _, created, request, queued, approved, result = audit(root)
    task = created["task_id"]
    assert (request["decision"], request["reason"], request["tier"]) == ("confirm", "T2", "T2")
    assert (queued["task_id"], queued["pending_id"]) == (task, pending_id)
    assert (approved["task_id"], approved["pending_id"], approved["tool"]) == (task, pending_id, "delete_file")
    assert approved["recheck"] == "ok"
    assert (result["task_id"], result["pending_id"], result["status"]) == (task, pending_id, "done")


def test_audit_deny_and_expiry_flows(sandbox, clock):
    client, root, outside = sandbox
    victim, pending_id = queue_delete(client, root)
    assert deny(client, root, pending_id).status_code == 200
    assert kinds(root)[-3:] == ["request", "queued", "deny"]
    assert audit(root)[-1]["pending_id"] == pending_id
    victim, pending_id = queue_delete(client, root, "other.txt")
    clock.now = 121.0
    assert outcome(client, pending_id).json() == {"status": "expired"}
    assert kinds(root)[-3:] == ["request", "queued", "expired"]
    assert (audit(root)[-1]["pending_id"], audit(root)[-1]["tool"]) == (pending_id, "delete_file")
    assert "result" not in kinds(root)
    assert victim.exists()


def test_audit_failed_and_missing_handlers(sandbox):
    client, root, outside = sandbox
    task = new_task(client)
    response = call(client, task, "system_stats")
    assert response.status_code == 500
    assert "blew up" not in response.text  # the model never sees the error text
    assert call(client, task, "list_windows").status_code == 501
    failed, missing = [e for e in audit(root) if e["event"] == "result"]
    assert (failed["status"], failed["error"]) == ("failed", "RuntimeError: tool blew up")
    assert missing["status"] == "not_implemented"


def test_audit_forbidden_role_logged_bad_token_not(sandbox):
    client, root, outside = sandbox
    victim, pending_id = queue_delete(client, root)
    before = len(audit(root))
    assert client.post("/approve", json={"pending_id": pending_id}).status_code == 403  # core token
    assert audit(root)[-1] | {"ts": None} == {"ts": None, "event": "forbidden", "role": "core", "path": "/approve"}
    wrong = {"x-jarvis-token": "wrong"}
    assert client.post("/approve", json={"pending_id": pending_id}, headers=wrong).status_code == 401
    assert len(audit(root)) == before + 1
    assert victim.exists()


def test_audit_unavailable_fails_closed(sandbox):
    client, root, outside = sandbox
    task = new_task(client)
    with failing("request"):
        response = call(client, task, "create_folder", path=str(root / "new"))
    assert (response.status_code, response.json()["detail"]) == (500, "Audit log unavailable")
    assert not (root / "new").exists()
    with failing("queued"):
        assert call(client, new_task(client), "delete_file", path=str(root / "x")).status_code == 500
    assert client.get("/pending", headers=ui_headers(root)).json() == {"pending": []}
    victim, pending_id = queue_delete(client, root)
    with failing("approve"):
        assert approve(client, root, pending_id).status_code == 500
    assert victim.exists()
    assert approve(client, root, pending_id).status_code == 404  # not left runnable
    assert outcome(client, pending_id).json() == {"status": "denied"}
    assert "result" not in kinds(root)
    with failing("task"):
        assert client.post("/task").status_code == 500


def test_audit_result_write_failure_stops_task(sandbox):
    client, root, outside = sandbox
    task = fresh_task(client)
    with failing("result"):
        assert call(client, task, "create_folder", path=str(root / "new")).status_code == 500
    # It ran; the request line without a result line shows the outcome is unknown.
    assert (root / "new").is_dir()
    refused = call(client, task, "get_time")
    assert (refused.status_code, refused.json()["detail"]) == (403, "task stopped")


def test_audit_file_must_not_be_a_link(storage):
    (storage / "elsewhere").mkdir()
    _winapi.CreateJunction(str(storage / "elsewhere"), str(storage / "audit.jsonl"))
    with pytest.raises(RuntimeError, match="Unsafe audit log"):
        create_app(storage, roots=[])


def test_audit_file_acl_is_user_only(storage):
    create_app(storage, roots=[])
    path = storage / "audit.jsonl"
    icacls = str(Path(os.environ["SystemRoot"]) / "System32" / "icacls.exe")
    saved = storage / "check.acl"
    subprocess.run([icacls, str(path), "/grant", "*S-1-1-0:R"], check=True, capture_output=True)
    create_app(storage, roots=[])  # restart re-applies the ACL
    subprocess.run([icacls, str(path), "/save", str(saved), "/q"], check=True, capture_output=True)
    descriptor = saved.read_text(encoding="utf-16-le")
    assert ";;;WD)" not in descriptor and ";;;S-1-1-0)" not in descriptor
    events = [json.loads(line)["event"] for line in path.read_text(encoding="utf-8").splitlines()]
    assert events == ["start", "start"]


def test_audit_every_result_was_authorised(sandbox, clock):
    """Invariant: each result line directly follows the allow or approved-ok line for it."""
    client, root, outside = sandbox
    task = new_task(client)
    call(client, task, "get_time")
    call(client, task, "create_folder", path=str(outside / "x"))
    call(client, task, "system_stats")
    (root / "a.txt").write_text("text")
    call(client, task, "read_text_file", path=str(root / "a.txt"))
    tainted = call(client, task, "create_folder", path=str(root / "new")).json()["pending_id"]
    approve(client, root, tainted)
    _, approved = queue_delete(client, root)
    approve(client, root, approved)
    _, denied = queue_delete(client, root, "d.txt")
    deny(client, root, denied)
    _, late = queue_delete(client, root, "late.txt")
    clock.now = 121.0
    approve(client, root, late)
    log = audit(root)
    results = [i for i, e in enumerate(log) if e["event"] == "result"]
    assert len(results) == 5
    for i in results:
        before = log[i - 1]
        assert (before["task_id"], before["tool"]) == (log[i]["task_id"], log[i]["tool"])
        assert before["event"] in ("request", "approve")
        if before["event"] == "request":
            assert before["decision"] == "allow"
        else:
            assert before["recheck"] == "ok" and before["pending_id"] == log[i]["pending_id"]


# --- kill switch (P2.5) ------------------------------------------------------


def stop(client, headers=None):
    return client.post("/stop", headers=headers)


def test_stop_stops_live_tasks_and_new_tasks_work(sandbox):
    client, root, outside = sandbox
    task = new_task(client)
    assert call(client, task, "get_time").status_code == 200
    response = stop(client)  # relayed by the core: ends current tasks, does not latch
    assert response.json() == {"stopped": 1, "cancelled": 0, "logged": True}
    refused = call(client, task, "create_folder", path=str(root / "new"))
    assert (refused.status_code, refused.json()["detail"]) == (403, "task stopped")
    assert not (root / "new").exists()
    # No latch after a core Stop: a new task runs straight away.
    assert call(client, new_task(client), "get_time").json() == {"result": "now"}
    assert stop(client).json() == {"stopped": 1, "cancelled": 0, "logged": True}
    assert stop(client).json() == {"stopped": 0, "cancelled": 0, "logged": True}  # harmless


def test_stop_cancels_pending_actions(sandbox):
    client, root, outside = sandbox
    first, first_id = queue_delete(client, root, "a.txt")
    second, second_id = queue_delete(client, root, "b.txt")
    assert stop(client).json() == {"stopped": 2, "cancelled": 2, "logged": True}
    assert client.get("/pending", headers=ui_headers(root)).json() == {"pending": []}
    assert outcome(client, first_id).json() == {"status": "cancelled"}
    assert approve(client, root, first_id).status_code == 410
    assert deny(client, root, second_id).status_code == 410
    assert outcome(client, second_id).json() == {"status": "cancelled"}
    assert first.exists() and second.exists()


def test_stop_open_to_both_roles_only_with_token(sandbox):
    client, root, outside = sandbox
    assert stop(client).status_code == 200  # core
    assert stop(client, ui_headers(root)).status_code == 200
    assert stop(client, {"x-jarvis-token": "wrong"}).status_code == 401
    bare = TestClient(client.app, base_url=BASE, client=LOOPBACK)
    assert bare.post("/stop").status_code == 401
    assert client.get("/stop").status_code == 405


def test_stop_is_audited(sandbox):
    client, root, outside = sandbox
    victim, pending_id = queue_delete(client, root)
    stop(client, ui_headers(root))
    line = audit(root)[-1]
    assert (line["event"], line["source"], line["tasks"], line["cancelled"]) == (
        "stop", "ui", 1, [pending_id],
    )
    stop(client)
    assert (audit(root)[-1]["source"], audit(root)[-1]["tasks"]) == ("core", 0)
    assert "result" not in kinds(root)


def test_stop_works_when_audit_log_fails(sandbox):
    client, root, outside = sandbox
    task = new_task(client)
    victim, pending_id = queue_delete(client, root)
    with failing("stop"):
        response = stop(client)
    assert (response.status_code, response.json()) == (
        200, {"stopped": 2, "cancelled": 1, "logged": False},
    )
    assert call(client, task, "get_time").json()["detail"] == "task stopped"
    assert client.get("/pending", headers=ui_headers(root)).json() == {"pending": []}
    assert outcome(client, pending_id).json() == {"status": "cancelled"}
    assert victim.exists()


def test_stop_mid_task(storage, clock):
    """The handler presses Stop while it runs: it finishes, nothing after it runs."""
    root = Path(os.path.realpath(storage.parent / "root"))
    root.mkdir()

    def get_time(args):
        assert client.post("/stop").json()["stopped"] == 1
        return "now"

    app = create_app(storage, roots=[root], handlers={"get_time": get_time}, clock=clock, protected=[])
    headers = {"x-jarvis-token": load_token(storage)}
    with TestClient(app, base_url=BASE, client=LOOPBACK, headers=headers) as client:
        task = new_task(client)
        assert call(client, task, "get_time").json() == {"result": "now"}
        refused = call(client, task, "get_time")
        assert (refused.status_code, refused.json()["detail"]) == (403, "task stopped")


def test_hotkey_from_config_stops_tasks(storage, fake_hotkey):
    app = create_app(storage, roots=[])  # default: hotkey from config/hotkey.toml
    headers = {"x-jarvis-token": load_token(storage)}
    with TestClient(app, base_url=BASE, client=LOOPBACK, headers=headers) as client:
        (listener,) = fake_hotkey
        assert listener.combo == "Ctrl+Alt+End"
        task = new_task(client)
        assert listener.callback() == {"stopped": 1, "cancelled": 0, "logged": True}
        assert call(client, task, "get_time").json()["detail"] == "stopped"
        assert not listener.closed
    assert listener.closed  # shutdown releases the hotkey
    lines = map(json.loads, (storage / "audit.jsonl").read_text(encoding="utf-8").splitlines())
    assert [line["source"] for line in lines if line["event"] == "stop"] == ["hotkey"]


def test_bridge_refuses_to_start_without_hotkey(storage, monkeypatch):
    def taken(combo, callback):
        raise RuntimeError(f"hotkey {combo} could not be registered")

    monkeypatch.setattr("bridge.hotkey.listen", taken)
    app = create_app(storage, roots=[])
    with pytest.raises(RuntimeError, match="could not be registered"):
        with TestClient(app, base_url=BASE, client=LOOPBACK):
            pass


def test_bad_hotkey_refused_at_create(storage):
    with pytest.raises(ValueError):
        create_app(storage, roots=[], hotkey="End")


def test_hotkey_none_starts_no_listener(storage, fake_hotkey):
    with TestClient(create_app(storage, roots=[], hotkey=None), base_url=BASE, client=LOOPBACK):
        assert fake_hotkey == []


def test_stop_between_recheck_and_handler(sandbox):
    """An approve already past recheck when Stop lands must not run."""
    client, root, outside = sandbox
    victim, pending_id = queue_delete(client, root)
    original = Policy.recheck

    def recheck_then_stop(self, *args):
        result = original(self, *args)
        assert client.post("/stop").status_code == 200
        return result

    with patch.object(Policy, "recheck", recheck_then_stop):
        refused = approve(client, root, pending_id)
    assert (refused.status_code, refused.json()["detail"]) == (403, "task stopped")
    assert victim.exists()
    assert outcome(client, pending_id).json() == {"status": "cancelled"}
    assert audit(root)[-1] | {"ts": None} == {
        "ts": None, "event": "result", "task_id": audit(root)[1]["task_id"],
        "tool": "delete_file", "pending_id": pending_id, "status": "cancelled",
    }



def test_stop_while_queueing_leaves_nothing_queued(sandbox):
    """P2.7: Stop lands after the policy check but before the action enters the queue
    (so Stop's clear cannot drop it). The action must not stay pending."""
    client, root, outside = sandbox
    victim = root / "victim.txt"
    victim.write_text("keep")
    task = new_task(client)
    original = ConfirmQueue.add
    added = []

    def stop_then_add(self, *args):
        assert client.post("/stop").status_code == 200
        added.append(original(self, *args))
        return added[-1]

    with patch.object(ConfirmQueue, "add", stop_then_add):
        refused = call(client, task, "delete_file", path=str(victim))
    assert (refused.status_code, refused.json()["detail"]) == (403, "task stopped")
    assert client.get("/pending", headers=ui_headers(root)).json()["pending"] == []
    assert victim.exists()
    pending_id = added[0].id
    assert [entry["event"] for entry in audit(root)[-2:]] == ["stop", "queued"]
    assert audit(root)[-1] | {"ts": None} == {
        "ts": None, "event": "queued", "task_id": task, "pending_id": pending_id,
        "refused": "task stopped",
    }
    refused = approve(client, root, pending_id)
    assert (refused.status_code, refused.json()["detail"]) == (410, "Pending action cancelled")
    assert outcome(client, pending_id).json() == {"status": "cancelled"}
    assert victim.exists()


def test_concurrent_http_calls_cannot_exceed_call_budget(storage, clock):
    """P2.7: 32 concurrent /tool calls for one task, one TestClient (own event loop) each."""
    count = 32
    ran = []
    app = create_app(
        storage, roots=[], handlers={"get_time": lambda args: ran.append(1)}, clock=clock,
        protected=[], hotkey=None,  # each thread starts the app; one listener cannot serve 32
    )
    headers = {"x-jarvis-token": load_token(storage)}
    start = threading.Barrier(count)
    statuses, errors = [], []

    with TestClient(app, base_url=BASE, client=LOOPBACK, headers=headers) as setup:
        task = new_task(setup)

    def run():
        try:
            with TestClient(app, base_url=BASE, client=LOOPBACK, headers=headers) as client:
                start.wait(5)
                statuses.append(call(client, task, "get_time").status_code)
        except BaseException as error:  # reported below, never lost in the thread
            errors.append(error)

    threads = [threading.Thread(target=run, daemon=True) for _ in range(count)]
    try:
        for thread in threads:
            thread.start()
    finally:
        for thread in threads:
            if thread.ident is not None:
                thread.join(30)
    assert not [thread for thread in threads if thread.is_alive()], "a thread hung"
    assert not errors, errors
    # The policy allows exactly 8. The 9th call's budget refusal stops the task, so an
    # allowed call that has not reached its handler yet is cancelled (execute's
    # stopped-check): fewer than 8 may answer 200, never more.
    lines = [json.loads(line) for line in (storage / "audit.jsonl").read_text().splitlines()]
    assert sum(e["event"] == "request" and e["decision"] == "allow" for e in lines) == MAX_CALLS
    results = [e["status"] for e in lines if e["event"] == "result"]
    assert set(results) <= {"cancelled", "done"} and len(results) == MAX_CALLS
    assert len(ran) == results.count("done") == statuses.count(200) <= MAX_CALLS
    assert statuses.count(403) == count - len(ran)


# --- undo routes (P2.6) -------------------------------------------------------


@pytest.fixture
def undo_box(storage, clock):
    """(client, root): a bridge whose delete_file quarantines, as P3 handlers will."""
    root = Path(os.path.realpath(storage.parent / "root"))
    root.mkdir()

    def delete_file(args):
        return UndoLog(storage / "quarantine").quarantine(args["path"], "delete_file").id

    app = create_app(storage, roots=[root], handlers={"delete_file": delete_file}, clock=clock, protected=[])
    headers = {"x-jarvis-token": load_token(storage)}
    with TestClient(app, base_url=BASE, client=LOOPBACK, headers=headers) as client:
        yield client, root


def quarantined(client, root, name="victim.txt"):
    """Delete a real file through the confirm queue; returns (victim, record_id)."""
    victim, pending_id = queue_delete(client, root, name)
    assert approve(client, root, pending_id).status_code == 200
    assert not victim.exists()
    return victim, outcome(client, pending_id).json()["result"]


def undo(client, root, record_id, headers=None):
    return client.post("/undo", json={"record_id": record_id}, headers=headers or ui_headers(root))


def test_undo_restores_quarantined_file(undo_box):
    client, root = undo_box
    victim, record_id = quarantined(client, root)
    listed = client.get("/undo", headers=ui_headers(root)).json()["records"]
    assert [(r["id"], r["kind"], r["path"], r["undone"]) for r in listed] == [
        (record_id, "quarantined", str(victim), None)
    ]
    response = undo(client, root, record_id)
    assert response.status_code == 200
    assert response.json()["undone"] is not None
    assert victim.read_text() == "keep"
    before, after = audit(root)[-2:]
    assert before | {"ts": None} == {
        "ts": None, "event": "undo", "record_id": record_id, "kind": "quarantined",
        "paths": {"path": str(victim)},
    }
    assert after | {"ts": None} == {"ts": None, "event": "undo_result", "record_id": record_id, "status": "done"}


def test_undo_routes_are_ui_only(undo_box):
    client, root = undo_box
    victim, record_id = quarantined(client, root)
    assert client.get("/undo").status_code == 403  # client default is the core token
    assert audit(root)[-1] | {"ts": None} == {"ts": None, "event": "forbidden", "role": "core", "path": "/undo"}
    assert client.post("/undo", json={"record_id": record_id}).status_code == 403
    for headers in [{"x-jarvis-token": "wrong"}, {"x-jarvis-token": ""}]:
        assert client.get("/undo", headers=headers).status_code == 401
        assert undo(client, root, record_id, headers).status_code == 401
    bare = TestClient(client.app, base_url=BASE, client=LOOPBACK)  # no token header at all
    assert bare.get("/undo").status_code == 401
    assert bare.post("/undo", json={"record_id": record_id}).status_code == 401
    assert not victim.exists()
    assert "undo" not in kinds(root)


def test_undo_refusals_over_http(undo_box):
    client, root = undo_box
    for bad in ["0" * 32, "../x", r"..\..\audit.jsonl", ""]:
        response = undo(client, root, bad)
        assert response.status_code == 404, bad
    assert audit(root)[-1] | {"ts": None} == {
        "ts": None, "event": "undo_result", "record_id": "", "status": "refused", "reason": "unknown record",
    }
    victim, record_id = quarantined(client, root)
    victim.write_text("in the way")
    response = undo(client, root, record_id)
    assert (response.status_code, response.json()["detail"]) == (409, "original location is occupied")
    assert victim.read_text() == "in the way"
    assert audit(root)[-1]["status"] == "refused"
    victim.rename(root / "blocker.txt")
    assert undo(client, root, record_id).status_code == 200
    assert victim.read_text() == "keep"
    response = undo(client, root, record_id)
    assert (response.status_code, response.json()["detail"]) == (409, "already undone")
    assert (root / "blocker.txt").read_text() == "in the way"


def test_forged_undo_record_cannot_move_root_or_protected_ancestor(storage, clock):
    """P2.8: record.json is editable by any same-user process. A forged `created` record
    would quarantine the folder it names; the root itself and a folder that contains a
    protected folder are refused."""
    root = Path(os.path.realpath(storage.parent / "root"))
    keep = root / "keep"
    (keep / "secret").mkdir(parents=True)
    app = create_app(storage, roots=[root], clock=clock, protected=[keep / "secret"])
    core = {"x-jarvis-token": load_token(storage)}
    ui = {"x-jarvis-token": load_token(storage, "ui.token")}
    with TestClient(app, base_url=BASE, client=LOOPBACK, headers=core) as client:
        for number, (victim, reason) in enumerate([
            (root, "path: the root itself"),
            (keep, "path: contains a protected folder"),
        ]):
            record_id = f"{number:032x}"
            folder = storage / "quarantine" / record_id
            folder.mkdir()
            (folder / "record.json").write_text(json.dumps({
                "id": record_id, "ts": "2026-11-12T00:00:00+00:00", "kind": "created",
                "tool": "create_folder", "path": str(victim),
            }), encoding="utf-8")
            response = client.post("/undo", json={"record_id": record_id}, headers=ui)
            assert (response.status_code, response.json()["detail"]) == (409, reason)
            assert victim.is_dir() and (keep / "secret").is_dir()


def test_undo_fails_closed_without_audit(undo_box):
    client, root = undo_box
    victim, record_id = quarantined(client, root)
    with failing("undo"):
        response = undo(client, root, record_id)
    assert (response.status_code, response.json()["detail"]) == (500, "Audit log unavailable")
    assert not victim.exists()
    assert "undo_result" not in kinds(root)
    with failing("undo_result"):  # it ran; the undo line without a result shows that
        assert undo(client, root, record_id).status_code == 500
    assert victim.read_text() == "keep"


# --- argument rules (P2.8 commit B) -------------------------------------------


def valid_args(tool, root):
    """Arguments the policy accepts for `tool` (fixture allowlists: notepad, x)."""
    rule = TOOLS[tool]
    args = {name: str(root / f"ok-{name}") for name in rule.path_params}
    args |= {name: "ok.txt" for name in rule.name_params}
    args |= {name: {"apps": "notepad", "scripts": "x"}[listed] for name, listed in rule.choices}
    args |= {name: "hello" for name in rule.text_params}
    return args


@pytest.mark.parametrize("tool", TOOLS)
def test_undeclared_argument_never_reaches_a_handler(every_tool, tool):
    client, root, outside, protected, ran = every_tool
    args = valid_args(tool, root)
    refused = call(client, new_task(client), tool, **args, overwrite=True)
    assert (refused.status_code, refused.json()["detail"]) == (403, "unknown argument")
    assert ran == []
    assert client.get("/pending", headers=ui_headers(root)).json()["pending"] == []
    # The same call without the extra argument is accepted, so the refusal was the argument.
    assert call(client, new_task(client), tool, **args).status_code in (200, 202)


def test_allowlists_come_from_the_config_folder(storage, clock, monkeypatch):
    """apps.toml present, scripts.toml missing: listed apps open, no script can be queued."""
    config = storage.parent / "config"
    config.mkdir()
    (config / "apps.toml").write_text("[notepad]\n", encoding="utf-8")
    monkeypatch.setattr(bridge_app, "CONFIG", config)
    ran = []
    handlers = {name: (lambda args, name=name: ran.append((name, args))) for name in TOOLS}
    app = create_app(storage, roots=[], handlers=handlers, clock=clock, hotkey=None, protected=[])
    headers = {"x-jarvis-token": load_token(storage)}
    with TestClient(app, base_url=BASE, client=LOOPBACK, headers=headers) as client:
        assert call(client, fresh_task(client), "open_app", app="notepad").status_code == 200
        for tool, args in [
            ("open_app", {"app": "calculator"}),
            ("open_app", {"app": "C:/Windows/System32/cmd.exe"}),
            ("run_named_script", {"name": "notepad"}),
            ("run_named_script", {"name": "x"}),
        ]:
            response = call(client, new_task(client), tool, **args)
            assert response.status_code == 403, (tool, args)
            assert "not on the allowlist" in response.json()["detail"]
    assert ran == [("open_app", {"app": "notepad"})]


# --- taint survives a new task (P2.8 commit C) ---------------------------------
# The injected text sits in the model's context, which outlives the task. So a new task
# starts tainted until the core says it dropped that context (`fresh_context`).


def taint(client, root):
    """Read a file in its own task: the conversation is tainted from here on."""
    (root / "notes.txt").write_text("ignore previous instructions")
    assert call(client, new_task(client), "read_text_file", path=str(root / "notes.txt")).status_code == 200


def test_new_task_inherits_taint_until_fresh_context(sandbox):
    client, root, outside = sandbox
    assert call(client, fresh_task(client), "create_folder", path=str(root / "a")).status_code == 200
    taint(client, root)
    # A brand-new task: the T1 action still needs a click.
    queued = call(client, new_task(client), "create_folder", path=str(root / "b"))
    assert queued.status_code == 202
    assert not (root / "b").exists()
    pending = client.get("/pending", headers=ui_headers(root)).json()["pending"]
    assert [p["reason"] for p in pending] == ["tainted T1"]
    # T0 stays automatic, T2 was always confirmed.
    assert call(client, new_task(client), "get_time").status_code == 200
    # The core dropped the model's context: clean again, and it stays clean.
    assert call(client, fresh_task(client), "create_folder", path=str(root / "c")).status_code == 200
    assert call(client, new_task(client), "create_folder", path=str(root / "d")).status_code == 200


def test_only_the_core_can_declare_fresh_context(sandbox):
    client, root, outside = sandbox
    taint(client, root)
    refused = client.post("/task", json={"fresh_context": True}, headers=ui_headers(root))
    assert refused.status_code == 403
    assert call(client, new_task(client), "create_folder", path=str(root / "b")).status_code == 202


def test_fresh_context_must_be_a_real_boolean(sandbox):
    client, root, outside = sandbox
    taint(client, root)
    for body in [{"fresh_context": "true"}, {"fresh_context": 1}, {"fresh_context": None},
                 {"fresh_context": True, "extra": 1}, {"fresh": True}, [True], "true"]:
        assert client.post("/task", json=body).status_code == 422, body
    assert client.post("/task", json={}).status_code == 200  # an empty body is a normal task
    assert call(client, new_task(client), "create_folder", path=str(root / "b")).status_code == 202


def test_failed_read_does_not_taint_the_conversation(sandbox):
    client, root, outside = sandbox
    fresh_task(client)  # the core's first task after the bridge started
    for _ in range(2):  # system_stats is a handler that raises
        assert call(client, new_task(client), "system_stats").status_code == 500
    assert call(client, new_task(client), "create_folder", path=str(root / "a")).status_code == 200


def test_task_line_records_taint_and_fresh_context(sandbox):
    client, root, outside = sandbox
    taint(client, root)
    inherited = new_task(client)
    cleared = fresh_task(client)
    lines = {entry["task_id"]: entry for entry in audit(root) if entry["event"] == "task"}
    assert (lines[inherited]["tainted"], lines[inherited]["fresh_context"]) == (True, False)
    assert (lines[cleared]["tainted"], lines[cleared]["fresh_context"]) == (False, True)


def test_taint_reaches_tasks_that_already_exist(sandbox):
    """P2.9 R1: taint is per conversation, so a task opened BEFORE the read is tainted too."""
    client, root, outside = sandbox
    earlier = fresh_task(client)
    later = new_task(client)  # clean when opened
    taint(client, root)
    for name, task in [("e", earlier), ("l", later)]:
        queued = call(client, task, "create_folder", path=str(root / name))
        assert queued.status_code == 202, name
        assert not (root / name).exists()
    pending = client.get("/pending", headers=ui_headers(root)).json()["pending"]
    assert [p["reason"] for p in pending] == ["tainted T1", "tainted T1"]
    # Only the core's fresh_context clears it, for tasks opened after.
    assert call(client, fresh_task(client), "create_folder", path=str(root / "c")).status_code == 200


def test_bridge_start_is_tainted_until_fresh_context(storage, clock):
    """P2.9 R2: a (re)started bridge knows nothing about the model's context: fail closed."""
    root = Path(os.path.realpath(storage.parent / "root"))
    root.mkdir()
    (root / "notes.txt").write_text("x")
    headers = {"x-jarvis-token": load_token(storage)}

    def bridge():
        handlers = {"read_text_file": lambda args: "text", "create_folder": lambda args: "made"}
        app = create_app(storage, roots=[root], handlers=handlers, clock=clock, protected=[])
        return TestClient(app, base_url=BASE, client=LOOPBACK, headers=headers)

    with bridge() as client:
        first = new_task(client)
        assert call(client, first, "create_folder", path=str(root / "a")).status_code == 202
        assert call(client, new_task(client), "read_text_file", path=str(root / "notes.txt")).status_code == 200
    with bridge() as client:  # pending actions are gone; the taint is not forgotten
        assert call(client, new_task(client), "create_folder", path=str(root / "a")).status_code == 202
        assert call(client, fresh_task(client), "create_folder", path=str(root / "a")).status_code == 200
    lines = [entry for entry in audit(root) if entry["event"] == "task"]
    assert [entry["tainted"] for entry in lines] == [True, True, True, False]


# --- stop latch (P2.8 commit D) ------------------------------------------------
# A Stop from the hotkey or the UI is a panic button: nothing new starts until Karthik
# resumes in the UI. A Stop relayed by the core (a spoken "stop") ends current tasks only.


def resume(client, headers=None):
    return client.post("/resume", headers=headers)


def halted(client):
    """True if the bridge refuses new work."""
    response = client.post("/task")
    assert response.status_code in (200, 403)
    return response.status_code == 403


def test_ui_stop_latches_until_ui_resume(sandbox):
    client, root, outside = sandbox
    task = new_task(client)
    assert stop(client, ui_headers(root)).status_code == 200
    refused = client.post("/task")
    assert (refused.status_code, refused.json()["detail"]) == (403, "stopped")
    refused = call(client, task, "get_time")
    assert (refused.status_code, refused.json()["detail"]) == (403, "stopped")
    # The core cannot resume itself.
    assert resume(client).status_code == 403
    assert halted(client)
    assert resume(client, ui_headers(root)).json() == {"status": "resumed"}
    assert call(client, new_task(client), "get_time").json() == {"result": "now"}
    # Resuming does not revive what was stopped.
    assert call(client, task, "get_time").json()["detail"] == "task stopped"


def test_hotkey_stop_latches(sandbox, fake_hotkey):
    client, root, outside = sandbox
    (listener,) = fake_hotkey
    listener.callback()
    assert halted(client)
    assert resume(client, ui_headers(root)).status_code == 200
    assert not halted(client)


def test_core_stop_does_not_latch(sandbox):
    client, root, outside = sandbox
    task = new_task(client)
    assert stop(client).status_code == 200  # the core relays a spoken "stop"
    assert call(client, task, "get_time").json()["detail"] == "task stopped"
    assert not halted(client)
    # A core Stop while latched does not unlatch either.
    stop(client, ui_headers(root))
    stop(client)
    assert halted(client)


def test_latch_and_resume_are_audited(sandbox):
    client, root, outside = sandbox
    stop(client)
    assert audit(root)[-1]["latched"] is False
    stop(client, ui_headers(root))
    assert (audit(root)[-1]["event"], audit(root)[-1]["latched"]) == ("stop", True)
    client.post("/task")
    assert audit(root)[-1] | {"ts": None} == {"ts": None, "event": "task", "refused": "stopped"}
    call(client, "any-task", "get_time")
    line = audit(root)[-1]
    assert (line["event"], line["decision"], line["reason"]) == ("request", "deny", "stopped")
    resume(client, ui_headers(root))
    assert audit(root)[-1] | {"ts": None} == {"ts": None, "event": "resume"}


def test_latch_holds_when_the_audit_log_fails(sandbox):
    client, root, outside = sandbox
    with failing("stop"):
        assert stop(client, ui_headers(root)).json()["logged"] is False
    assert halted(client)  # stopping never depends on the log
    with failing("resume"):
        assert resume(client, ui_headers(root)).status_code == 500
    assert halted(client)  # an unlogged resume resumes nothing
    with failing("task", "request"):
        assert client.post("/task").status_code == 500
        assert call(client, "any-task", "get_time").status_code == 500


def test_resume_when_not_halted_is_harmless(sandbox):
    client, root, outside = sandbox
    assert resume(client, ui_headers(root)).json() == {"status": "resumed"}
    assert not halted(client)
    assert client.get("/resume", headers=ui_headers(root)).status_code == 405


# --- kill-switch liveness and audit encoding (P2.8 commit E) --------------------
# Same rule as at startup: no kill switch, no tools.


def test_dead_hotkey_listener_stops_everything(sandbox, fake_hotkey):
    client, root, outside = sandbox
    (listener,) = fake_hotkey
    task = fresh_task(client)
    assert call(client, task, "get_time").status_code == 200  # alive: tools run
    listener.dead = True  # the hotkey thread died
    refused = call(client, task, "create_folder", path=str(root / "new"))
    assert (refused.status_code, refused.json()["detail"]) == (503, "kill switch unavailable")
    assert not (root / "new").exists()
    stop_line, result_line = audit(root)[-2:]
    assert (stop_line["event"], stop_line["source"], stop_line["latched"]) == (
        "stop", "hotkey-dead", True)
    assert (result_line["event"], result_line["status"]) == ("result", "cancelled")
    # Latched: nothing new starts until Karthik resumes (and the bridge needs a restart).
    assert client.post("/task").json()["detail"] == "stopped"


def test_dead_hotkey_listener_blocks_approve(sandbox, fake_hotkey):
    client, root, outside = sandbox
    victim, pending_id = queue_delete(client, root)
    fake_hotkey[0].dead = True
    refused = approve(client, root, pending_id)
    assert refused.status_code in (403, 503)  # stopped by the liveness check or by its Stop
    assert victim.exists()
    assert outcome(client, pending_id).json()["status"] in ("cancelled", "denied")
    assert "done" not in [entry.get("status") for entry in audit(root)]


def test_hotkey_configured_but_never_started_runs_no_tool(storage, clock):
    """The listener starts with the app (lifespan). Without it there is no kill switch."""
    ran = []
    app = create_app(storage, roots=[], handlers={"get_time": lambda args: ran.append(1)}, clock=clock)
    headers = {"x-jarvis-token": load_token(storage)}
    client = TestClient(app, base_url=BASE, client=LOOPBACK, headers=headers)  # no `with`: no lifespan
    assert call(client, new_task(client), "get_time").status_code == 503
    assert ran == []


def test_surrogate_in_a_result_is_logged_and_returned(storage, clock):
    """Windows file names can hold an unpaired surrogate; list_dir would return one."""
    name = "report\ud800.txt"
    app = create_app(
        storage, roots=[], handlers={"get_time": lambda args: [name]}, clock=clock, hotkey=None,
    )
    headers = {"x-jarvis-token": load_token(storage)}
    with TestClient(app, base_url=BASE, client=LOOPBACK, headers=headers) as client:
        response = call(client, new_task(client), "get_time")
        assert response.status_code == 200
        assert response.json() == {"result": [name]}
    lines = [json.loads(line) for line in (storage / "audit.jsonl").read_bytes().decode("ascii").splitlines()]
    assert lines[-1]["status"] == "done" and "report" in lines[-1]["result"]


# --- sweep additions (P2.8 commit F) -------------------------------------------


def live_routes(app):
    return [(method, route.path) for route in app.routes for method in sorted(route.methods)]


SWEEP_BODY = {"tool": "get_time", "args": {}, "pending_id": "x", "record_id": "x"}


def test_duplicate_token_or_host_header_refused_on_every_route(sandbox, storage):
    """Two headers of the same name: which one would a proxy or a parser pick? Refuse both."""
    client, root, outside = sandbox
    task = new_task(client)
    body = {**SWEEP_BODY, "task_id": task}
    tokens = {"core": load_token(storage), "ui": load_token(storage, "ui.token")}
    before = (storage / "audit.jsonl").read_bytes()
    bare = TestClient(client.app, base_url=BASE, client=LOOPBACK)  # no default token header
    for method, path in live_routes(client.app):
        valid = tokens[sorted(bridge_app.ROUTE_ROLES[path])[0]]
        for pair in [(valid, "wrong"), ("wrong", valid), (valid, valid), (valid, "")]:
            headers = [("x-jarvis-token", pair[0]), ("x-jarvis-token", pair[1])]
            response = bare.request(method, path, json=body, headers=headers)
            assert response.status_code == 401, (method, path, pair)
        for hosts in [("127.0.0.1:8765", "evil.example"), ("evil.example", "127.0.0.1:8765"),
                      ("127.0.0.1:8765", "127.0.0.1:8765")]:
            headers = [("host", hosts[0]), ("host", hosts[1]), ("x-jarvis-token", valid)]
            response = bare.request(method, path, json=body, headers=headers)
            assert response.status_code == 400, (method, path, hosts)
    assert (storage / "audit.jsonl").read_bytes() == before  # nothing ran, nothing logged
    assert call(client, task, "get_time").status_code == 200


def test_wrong_role_refused_on_every_single_role_route(sandbox, storage):
    client, root, outside = sandbox
    task = new_task(client)
    body = {**SWEEP_BODY, "task_id": task}
    tokens = {"core": load_token(storage), "ui": load_token(storage, "ui.token")}
    bare = TestClient(client.app, base_url=BASE, client=LOOPBACK)
    before = len(audit(root))
    swept = []
    for method, path in live_routes(client.app):
        for role in set(tokens) - bridge_app.ROUTE_ROLES[path]:
            response = bare.request(method, path, json=body, headers={"x-jarvis-token": tokens[role]})
            assert response.status_code == 403, (method, path, role)
            swept.append((role, path))
    # Every refusal is logged as `forbidden`, and nothing else happened.
    logged = [(entry["role"], entry["path"]) for entry in audit(root)[before:]]
    assert logged == swept and all(entry["event"] == "forbidden" for entry in audit(root)[before:])
    assert {path for _, path in swept} == {
        path for path, roles in bridge_app.ROUTE_ROLES.items() if len(roles) == 1
    }  # the sweep is not vacuous: every single-role route was tried
    assert call(client, task, "get_time").status_code == 200


MISSING = object()


@pytest.mark.parametrize("value", [MISSING, None, 123, 1.5, True, ["C:/x"], {"path": "C:/x"}, ""],
                         ids=["missing", "null", "int", "float", "bool", "list", "object", "empty"])
@pytest.mark.parametrize("tool, param", PATH_PARAMS)
def test_every_path_parameter_must_be_a_string(every_tool, tool, param, value):
    client, root, outside, protected, ran = every_tool
    args = valid_args(tool, root)
    if value is MISSING:
        del args[param]
    else:
        args[param] = value
    response = call(client, new_task(client), tool, **args)
    assert (response.status_code, response.json()["detail"]) == (403, f"{param}: not a path")
    assert ran == []
    assert client.get("/pending", headers=ui_headers(root)).json()["pending"] == []
