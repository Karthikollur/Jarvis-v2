"""P3.5: the bridge client (section A) and the core agent (section B)."""

from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import socket
import tempfile
import threading
import time
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

import pytest
import uvicorn

import core.openjarvis_env  # noqa: F401  before openjarvis
from bridge.app import create_app, load_token
from core.agent import Core, GuardError, build
from core.bridge_client import BridgeClient, BridgeError
from core.specs import SPECS
from core.tools import BridgeTool, HIDDEN, bridge_tools
from openjarvis.core.types import Role, ToolResult
from openjarvis.engine._stubs import InferenceEngine
from openjarvis.tools._stubs import BaseTool, ToolSpec
from safety.policy import MAX_SECONDS, TOOLS

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


PROMPT = tomllib.loads((REPO / "core" / "config.toml").read_text(encoding="utf-8"))["agent"]["default_system_prompt"]


class FakeEngine(InferenceEngine):
    """Pops scripted generate() results and records (messages, tools)."""

    engine_id = "fake"

    def __init__(self, scripts):
        self._scripts = list(scripts)
        self.calls = []

    def generate(self, messages, *, model, temperature=0.7, max_tokens=1024, **kwargs):
        self.calls.append((list(messages), kwargs.get("tools")))
        return self._scripts.pop(0)

    async def stream(self, messages, *, model, temperature=0.7, max_tokens=1024, **kwargs):
        yield ""

    def list_models(self):
        return []

    def health(self):
        return True


def tool_call(name, arguments="{}"):
    return {"content": "", "tool_calls": [{"id": name, "name": name, "arguments": arguments}], "usage": {}}


def answer(text):
    return {"content": text, "tool_calls": [], "usage": {}}


def make_core(live_bridge, scripts, on_pending=None):
    client, root, storage, base = live_bridge
    engine = FakeEngine(scripts)
    core = Core(client, engine, "fake", PROMPT, temperature=0, max_tokens=64, on_pending=on_pending)
    return core, engine, client, root, storage, base


def pending(base, storage):
    """GET /pending with the ui token. ui() stays POST-only."""
    request = urllib.request.Request(
        base + "/pending",
        headers={"x-jarvis-token": load_token(storage, "ui.token")},
        method="GET",
    )
    with _no_proxy.open(request, timeout=5) as response:
        return json.loads(response.read())


def started(core, text):
    """handle() on a daemon thread. A leftover wait must not hold the process for MAX_SECONDS."""
    box = []

    def run():
        try:
            box.append(core.handle(text))
        except Exception as caught:
            box.append(caught)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread, box


def joined(thread):
    thread.join(timeout=10)
    assert not thread.is_alive()


def outcome_of(box):
    assert box, "handle did not return"
    if isinstance(box[0], Exception):
        raise box[0]
    return box[0]


def tool_contents(messages):
    return [message.content for message in messages if message.role == Role.TOOL]


def test_one_task_per_request(live_bridge):
    root, storage = live_bridge[1], live_bridge[2]
    core, _engine, _client, _root, _storage, _base = make_core(live_bridge, [
        tool_call("system_stats"),
        tool_call("create_folder", json.dumps({"path": str(root / "x")})),
        answer("Done."),
    ])
    before = [line for line in audit(storage) if line["event"] == "task"]
    assert core.handle("sort it") == "Done."
    assert (root / "x").is_dir()
    tasks = [line for line in audit(storage) if line["event"] == "task"]
    requests = [line for line in audit(storage) if line["event"] == "request"]
    assert len(tasks) == len(before) + 1
    assert [line["task_id"] for line in requests] == [tasks[-1]["task_id"], tasks[-1]["task_id"]]


def test_fresh_is_passed_to_new_task(live_bridge):
    core, _engine, _client, _root, storage, _base = make_core(live_bridge, [
        tool_call("system_stats"), answer("a-done"),
        tool_call("system_stats"), answer("b-done"),
    ])
    core.handle("a", fresh=True)
    core.handle("b", fresh=False)
    flags = [line["fresh_context"] for line in audit(storage) if line["event"] == "task"]
    assert flags == [True, False]


def test_history_carries_until_fresh(live_bridge):
    core, engine, _client, _root, _storage, _base = make_core(live_bridge, [
        answer("first-answer"), answer("second-answer"), answer("third-answer"),
    ])
    core.handle("a")
    core.handle("b", fresh=False)
    carried = engine.calls[1][0]
    assert any(message.content == "a" for message in carried)
    assert any(message.content == "first-answer" for message in carried)
    core.handle("c", fresh=True)
    reset = engine.calls[2][0]
    assert all(message.content != "a" for message in reset)
    assert all(message.content != "first-answer" for message in reset)


@pytest.mark.parametrize("change", ["replaced", "removed", "subclass"])
def test_guard_refuses_a_changed_tool_set(live_bridge, change):
    core, engine, client, _root, storage, _base = make_core(live_bridge, [])
    if change == "replaced":
        original = core._agent._tools[0]

        class Foreign(BaseTool):
            tool_id = original.tool_id

            @property
            def spec(self):
                return original.spec

            def execute(self, **params):
                raise AssertionError("foreign tool ran")

        core._agent._tools[0] = Foreign()
    elif change == "removed":
        core._agent._tools.pop()
    else:
        class Sub(BridgeTool):
            pass

        core._agent._tools.append(Sub("get_time", client, lambda: None))
    with pytest.raises(GuardError):
        core.handle("sort it")
    assert engine.calls == []
    assert [line for line in audit(storage) if line["event"] == "task"] == []


@pytest.mark.parametrize("change", ["replaced", "removed", "added"])
def test_guard_refuses_a_changed_executor(live_bridge, change):
    core, engine, _client, _root, storage, _base = make_core(live_bridge, [])
    run = core._agent._executor._tools
    if change == "replaced":
        original = core._agent._tools[0]

        class Foreign(BaseTool):
            tool_id = original.tool_id

            @property
            def spec(self):
                return original.spec

            def execute(self, **params):
                raise AssertionError("foreign tool ran")

        name = core._agent._tools[0].spec.name
        run[name] = Foreign()
    elif change == "removed":
        del run[core._agent._tools[0].spec.name]
    else:
        run["shell"] = core._agent._tools[0]
    with pytest.raises(GuardError):
        core.handle("sort it")
    assert engine.calls == []
    assert [line for line in audit(storage) if line["event"] == "task"] == []


def test_hidden_is_the_tools_without_a_handler():
    from bridge.tools import HANDLERS, mutating
    from core.tools import HIDDEN

    production_handlers = set(HANDLERS) | set(mutating(None, {}, {}))
    assert HIDDEN == set(TOOLS) - production_handlers


def test_built_core_hides_recall_memory(live_bridge):
    core, _engine, _client, _root, _storage, _base = make_core(live_bridge, [])
    assert all(tool.spec.name != "recall_memory" for tool in core._agent._tools)
    assert "recall_memory" not in core._agent._executor._tools
    offered = {item["function"]["name"] for item in core._agent._executor.get_openai_tools()}
    assert "recall_memory" not in offered


@pytest.mark.parametrize("where", ["both", "executor_only"])
def test_guard_refuses_recall_memory(live_bridge, where):
    core, engine, client, _root, storage, _base = make_core(live_bridge, [])
    run = core._agent._executor._tools
    hidden = BridgeTool("recall_memory", client, lambda: None)
    if where == "both":
        core._agent._tools[:] = [t for t in core._agent._tools if t.spec.name != "recall_memory"] + [hidden]
    run["recall_memory"] = hidden
    with pytest.raises(GuardError):
        core.handle("sort it")
    assert engine.calls == []
    assert [line for line in audit(storage) if line["event"] == "task"] == []


def test_fast_path_get_time_and_open_notepad(live_bridge, monkeypatch):
    """open notepad must not launch a real process."""
    core, engine, _client, _root, storage, _base = make_core(live_bridge, [])
    reply = json.loads(core.handle("what time is it"))
    when = datetime.fromisoformat(reply["time"])
    assert set(reply) == {"time"}
    assert when.tzinfo is not None and when.utcoffset() is not None
    assert abs((datetime.now().astimezone() - when).total_seconds()) <= 5
    assert engine.calls == []
    tasks = [line for line in audit(storage) if line["event"] == "task"]
    requests = [line for line in audit(storage) if line["event"] == "request"]
    assert len(tasks) == 1
    assert [(line["tool"], line["task_id"]) for line in requests] == [("get_time", tasks[0]["task_id"])]
    launched = []

    class FakePopen:
        def __init__(self, *args, **kwargs):
            launched.append((args, kwargs))
            self.pid = 4321

    monkeypatch.setattr("bridge.tools.subprocess.Popen", FakePopen)
    core.handle("open notepad")
    assert len(launched) == 1
    opened = [line for line in audit(storage) if line["event"] == "request" and line["tool"] == "open_app"]
    assert len(opened) == 1 and opened[0]["decision"] == "allow"
    assert engine.calls == []


def test_stop_ends_tasks_without_a_new_one(live_bridge):
    core, _engine, _client, _root, storage, _base = make_core(live_bridge, [])
    assert core.handle("stop") == "Stopped."
    assert [line for line in audit(storage) if line["event"] == "task"] == []
    stop = next(line for line in audit(storage) if line["event"] == "stop")
    assert stop["source"] == "core" and stop["latched"] is False


def test_refusal_is_an_observation(live_bridge):
    _client, root, _storage, _base = live_bridge
    outside = root.parent / "outside" / "x"
    core, engine, _client, _root, _storage, _base = make_core(live_bridge, [
        tool_call("create_folder", json.dumps({"path": str(outside)})),
        answer("No."),
    ])
    assert core.handle("make it") == "No."
    messages, _tools = engine.calls[1]
    assert any(
        message.role == Role.TOOL and message.content == "refused: path: outside the allowed roots"
        for message in messages
    )
    assert core.calls == [("create_folder", {"path": str(outside)})]
    assert not outside.exists()


def test_refused_create_folder_is_not_ok(live_bridge):
    """A refused tool stays a failed result. The reply is still the model's words."""
    outside = live_bridge[1].parent / "outside" / "x"
    core, _engine, _client, _root, _storage, _base = make_core(live_bridge, [
        tool_call("create_folder", json.dumps({"path": str(outside)})),
        answer("I created it"),
    ])
    assert core.handle("make it") == "I created it"
    result = core.results[0]
    assert result.tool_name == "create_folder"
    assert result.success is False
    assert result.content.startswith("refused:")
    shown = f"  {result.tool_name}: {'ok' if result.success else result.content}"
    assert shown == f"  create_folder: {result.content}"


def test_results_reset_then_fast_path_keeps_one(live_bridge):
    """No tool call clears the last request. A fast-path request keeps that one result."""
    root = live_bridge[1]
    core, _engine, _client, _root, _storage, _base = make_core(live_bridge, [
        tool_call("list_dir", json.dumps({"path": str(root)})),
        answer("Listed."),
        answer("Nothing."),
    ])
    assert core.handle("list it") == "Listed."
    assert len(core.results) == 1
    assert core.handle("thanks") == "Nothing."
    assert core.results == []
    reply = core.handle("what time is it")
    assert reply == core.results[0].content
    assert [(item.tool_name, item.success) for item in core.results] == [("get_time", True)]


@pytest.mark.parametrize("decision", ["approve", "deny"])
def test_pending_approve_and_deny(live_bridge, decision):
    root, storage, base = live_bridge[1], live_bridge[2], live_bridge[3]
    ids = []
    core, engine, _client, _root, _storage, _base = make_core(
        live_bridge,
        [
            tool_call("list_dir", json.dumps({"path": str(root)})),
            tool_call("create_folder", json.dumps({"path": str(root / "y")})),
            answer("Done."),
        ],
        on_pending=ids.append,
    )
    thread, box = started(core, "make y")
    approved = None
    deadline = time.monotonic() + 10
    while thread.is_alive() and time.monotonic() < deadline:
        waiting = pending(base, storage)["pending"]
        if waiting:
            approved = waiting[0]["id"]
            ui(base, storage, "/" + decision, {"pending_id": approved})
            break
        time.sleep(0.05)
    joined(thread)
    outcome_of(box)
    assert ids == [approved]
    texts = tool_contents(engine.calls[-1][0])
    if decision == "approve":
        assert (root / "y").is_dir()
        assert any('"created": true' in text for text in texts)
    else:
        assert not (root / "y").exists()
        assert "denied" in texts


def test_wait_times_out(live_bridge):
    client, root, _storage, _base = live_bridge
    task = client.new_task(fresh=False)  # the bridge starts tainted, so create_folder waits
    reads = {"n": 0}
    ticks = {"n": 0}

    class Counting:
        def tool(self, task_id, name, args):
            return client.tool(task_id, name, args)

        def outcome(self, pending_id):
            reads["n"] += 1
            return client.outcome(pending_id)

    def clock():
        ticks["n"] += 1
        return 0 if ticks["n"] == 1 else MAX_SECONDS * ticks["n"]

    tool = BridgeTool("create_folder", Counting(), lambda: task, clock=clock, sleep=lambda _seconds: None)
    result = tool.execute(path=str(root / "late"))
    assert result.success is False and result.content == "timed out"
    assert reads["n"] == 1
    assert not (root / "late").exists()


def test_sequential_confirmations(live_bridge):
    """Two confirms in one turn. Parallel refuses the second with 'awaiting confirmation'."""
    root, storage, base = live_bridge[1], live_bridge[2], live_bridge[3]
    core, engine, _client, _root, _storage, _base = make_core(live_bridge, [
        tool_call("list_dir", json.dumps({"path": str(root)})),
        {
            "content": "",
            "tool_calls": [
                {"id": "p", "name": "create_folder", "arguments": json.dumps({"path": str(root / "p")})},
                {"id": "q", "name": "create_folder", "arguments": json.dumps({"path": str(root / "q")})},
            ],
            "usage": {},
        },
        answer("Done."),
    ])
    thread, box = started(core, "make both")
    approved = []
    deadline = time.monotonic() + 10
    while thread.is_alive() and time.monotonic() < deadline:
        for action in pending(base, storage)["pending"]:
            if action["id"] not in approved:
                approved.append(action["id"])
                ui(base, storage, "/approve", {"pending_id": action["id"]})
        time.sleep(0.05)
    joined(thread)
    assert outcome_of(box) == "Done."
    assert (root / "p").is_dir() and (root / "q").is_dir()
    created = [text for text in tool_contents(engine.calls[-1][0]) if '"created": true' in text]
    assert len(created) == 2
    every_tool = [text for messages, _tools in engine.calls for text in tool_contents(messages)]
    assert all("awaiting confirmation" not in text for text in every_tool)
    queued = [line for line in audit(storage) if line["event"] == "queued"]
    assert len(queued) == 2
    assert all("pending_id" in line and "refused" not in line for line in queued)


def test_bridge_tools_match_the_table():
    made = bridge_tools(None, lambda: "t")
    assert [tool.spec.name for tool in made] == [name for name in TOOLS if name not in HIDDEN]
    for tool in made:
        assert tool.spec.parameters == SPECS[tool.spec.name][1]
        assert tool.spec.timeout_seconds > MAX_SECONDS


def test_build_reads_config(monkeypatch):
    seen = {}

    def fake_engine(*, host):
        seen["host"] = host
        return object()

    def fake_client():
        seen["client"] = True
        return object()

    monkeypatch.setattr("core.agent.OllamaEngine", fake_engine)
    monkeypatch.setattr("core.agent.BridgeClient", fake_client)
    built = build()
    assert seen == {"host": "http://127.0.0.1:11434", "client": True}
    assert built._agent._model == "qwen3.5:4b"
    assert built._agent._system_prompt == PROMPT
    assert build(router=None)._router is None


def test_cli_says_when_the_bridge_is_down(monkeypatch, capsys):
    import core.__main__ as cli

    def down(*args, **kwargs):
        raise urllib.error.URLError("refused")

    monkeypatch.setattr(cli, "build", down)
    with pytest.raises(SystemExit) as raised:
        cli.main(["what time is it"])
    assert raised.value.code == 1
    assert capsys.readouterr().out == "bridge is not running\n"


def test_cli_prints_ok_and_expired(monkeypatch, capsys):
    import core.__main__ as cli

    class Stub:
        def __init__(self):
            self.results = [
                ToolResult("get_time", "12:00", True),
                ToolResult("create_folder", "expired", False),
            ]

        def handle(self, _text):
            return "I created it"

    monkeypatch.setattr(cli, "build", lambda **_kwargs: Stub())
    cli.main(["make a folder"])
    assert capsys.readouterr().out == (
        "I created it\n"
        "  get_time: ok\n"
        "  create_folder: expired\n"
    )


@pytest.mark.parametrize(
    "error",
    [TimeoutError("timed out"), ConnectionResetError("reset"), BridgeError("502: bad")],
    ids=["TimeoutError", "ConnectionResetError", "BridgeError"],
)
def test_cli_reports_a_bridge_error(monkeypatch, capsys, error):
    import core.__main__ as cli

    def blow(*_args, **_kwargs):
        raise error

    monkeypatch.setattr(cli, "build", blow)
    with pytest.raises(SystemExit) as raised:
        cli.main(["what time is it"])
    assert raised.value.code == 1
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 1 and lines[0].startswith("bridge error: ")


@pytest.fixture
def scripted_bridge():
    """One loopback answer, chosen by the test. Shut down with the fixture."""
    script = {"status": 200, "body": b""}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            if length:
                self.rfile.read(length)
            raw = script["body"]
            self.send_response(script["status"])
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, _format, *_args):
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    client = BridgeClient(f"http://127.0.0.1:{port}", token="0" * 64)
    try:
        yield script, client
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.parametrize(
    ("status", "body", "refused"),
    [
        (500, b"plain text", True),
        (200, b"not json", True),
        (200, b"[1]", True),
        (200, b"ok\xff", True),
        (500, b"[1]", True),
        (200, b"", False),
    ],
    ids=["plain-text-500", "non-json-200", "list-200", "ok-ff-200", "list-500", "empty-200"],
)
def test_odd_answer_never_comes_back_as_data(scripted_bridge, status, body, refused):
    script, client = scripted_bridge
    script["status"], script["body"] = status, body
    if refused:
        assert client._post("/task", {}) == (502, {"detail": f"bad answer from bridge ({status})"})
        with pytest.raises(BridgeError):
            client.new_task(False)
        return
    assert client._post("/task", {}) == (200, {})
