"""P3.5 section A: the core's HTTP client for the bridge."""

import json
import os
import socket
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

import pytest
import uvicorn

from bridge.app import create_app, load_token
from core.bridge_client import BridgeClient, BridgeError

REPO = Path(__file__).resolve().parents[1]
_no_proxy = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def ui(base, storage, path, body):
    """POST one ui-token route. Section A uses /approve, /deny and /stop."""
    request = urllib.request.Request(
        base + path,
        data=json.dumps(body).encode(),
        headers={
            "x-jarvis-token": load_token(storage, "ui.token"),
            "content-type": "application/json",
        },
        method="POST",
    )
    with _no_proxy.open(request, timeout=5) as response:
        return json.loads(response.read())


def audit(storage):
    text = (storage / "audit.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line]


@pytest.fixture
def folders():
    """(root, outside): an empty folder to list and a sibling folder outside it."""
    (REPO / ".test-storage").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=REPO / ".test-storage") as directory:
        base = Path(os.path.realpath(directory))
        (base / "root").mkdir()
        (base / "outside").mkdir()
        yield base / "root", base / "outside"


@pytest.fixture
def live_bridge(folders):
    """A real bridge on a bound loopback socket. Yields (client, root, storage, base)."""
    root, _outside = folders
    storage = root.parent / "storage"
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    app = create_app(storage, roots=[root], protected=[], hotkey=None)
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", workers=1)
    )
    thread = threading.Thread(target=lambda: server.run(sockets=[sock]), daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started:
            if time.monotonic() >= deadline or not thread.is_alive():
                pytest.fail("bridge did not start")
            time.sleep(0.05)
        base = f"http://127.0.0.1:{port}"
        yield BridgeClient(base, load_token(storage)), root, storage, base
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()
        assert not thread.is_alive(), "bridge did not stop"


def test_non_fresh_task_then_fresh(live_bridge):
    """A non-fresh task is opened first: a fresh task would clear the taint."""
    client, root, storage, _base = live_bridge
    first = client.new_task(fresh=False)
    second = client.new_task(fresh=True)
    tasks = [line for line in audit(storage) if line["event"] == "task"]
    assert [(line["fresh_context"], line["tainted"]) for line in tasks] == [
        (False, True),
        (True, False),
    ]
    queued, _body = client.tool(first, "create_folder", {"path": str(root / "x")})
    assert queued == 202 and not (root / "x").exists()
    allowed, body = client.tool(second, "create_folder", {"path": str(root / "x")})
    assert allowed == 200 and "result" in body and (root / "x").is_dir()


def test_tool_returns_status_and_body(live_bridge):
    client, root, _storage, _base = live_bridge
    outside = root.parent / "outside"
    task = client.new_task(fresh=True)
    status, body = client.tool(task, "list_dir", {"path": str(root)})
    assert status == 200 and isinstance(body["result"], dict)
    status, body = client.tool(task, "list_dir", {"path": str(outside)})
    assert (status, body) == (403, {"detail": "path: outside the allowed roots"})


def test_outcome_pending_approve_and_deny(live_bridge):
    client, root, storage, base = live_bridge
    task = client.new_task(fresh=False)
    status, body = client.tool(task, "create_folder", {"path": str(root / "a")})
    assert status == 202
    pending = body["pending_id"]
    assert client.outcome(pending) == (200, {"status": "pending"})
    ui(base, storage, "/approve", {"pending_id": pending})
    status, body = client.outcome(pending)
    assert status == 200 and body["status"] == "done" and "result" in body
    assert (root / "a").is_dir()
    status, body = client.tool(task, "create_folder", {"path": str(root / "b")})
    assert status == 202
    pending = body["pending_id"]
    ui(base, storage, "/deny", {"pending_id": pending})
    assert client.outcome(pending) == (200, {"status": "denied"})
    assert not (root / "b").exists()


def test_rejects_bad_base_token_and_missing_file(monkeypatch, tmp_path):
    with pytest.raises(ValueError):
        BridgeClient("http://192.168.1.5:8765", token="0" * 64)
    with pytest.raises(RuntimeError):
        BridgeClient(token="xyz")
    monkeypatch.setattr("core.bridge_client.TOKEN", tmp_path / "missing.token")
    with pytest.raises(FileNotFoundError):
        BridgeClient(token=None)


def test_core_stop_does_not_latch(live_bridge):
    client, _root, storage, _base = live_bridge
    status, body = client.stop()
    assert status == 200 and isinstance(body, dict)
    stop = next(line for line in audit(storage) if line["event"] == "stop")
    assert stop["source"] == "core" and stop["latched"] is False


def test_new_task_raises_when_bridge_is_latched(live_bridge):
    client, _root, storage, base = live_bridge
    ui(base, storage, "/stop", {})
    with pytest.raises(BridgeError):
        client.new_task(fresh=True)


def test_proxy_env_is_ignored(live_bridge, monkeypatch):
    _client, _root, storage, base = live_bridge
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")
    monkeypatch.delenv("NO_PROXY", raising=False)
    monkeypatch.delenv("no_proxy", raising=False)
    # urlopen builds one process-wide opener on first use. Tests 1-6 already used the
    # client, so a mutant that calls urlopen would keep an opener from before this env.
    cached = urllib.request._opener
    urllib.request._opener = None
    try:
        client = BridgeClient(base, load_token(storage))
        assert client.new_task(fresh=True)
    finally:
        urllib.request._opener = cached
