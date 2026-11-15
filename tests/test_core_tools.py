"""Built-in tools guard (P2.8 commit F).

OpenJarvis registers its own tools (shell_exec, file_write, http_request, ...) as soon as
`openjarvis.tools` is imported. The model can only call a tool that a call site names in
`tools=[...]`, so the risk is a call site naming a built-in. These tests fail when one does.
They do not need a model.
"""

import ast
import sys
import tomllib
from pathlib import Path

import pytest

from safety.policy import TOOLS

REPO = Path(__file__).resolve().parents[1]


def sources(base):
    return sorted([*(base / "core").rglob("*.py"), *(base / "evals").rglob("*.py")])


SOURCES = sources(REPO)
BUILT_INS = ["shell_exec", "file_write", "http_request", "apply_patch"]
# Agents that bring no tools of their own. The SDK's digest agent adds its own tools.
AGENTS = {"simple", "orchestrator"}


def keyword_values(name):
    """(file, line, source text) for every `name=...` keyword argument in core/ and evals/."""
    found = []
    for source in SOURCES:
        for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call):
                for keyword in node.keywords:
                    if keyword.arg == name:
                        found.append((source.name, keyword.value.lineno, ast.unparse(keyword.value)))
    return found


def hidden_keywords():
    """(file, line) for every call with a `**` unpacking: it can hide `tools=` from the scan."""
    return [
        (source.name, node.lineno)
        for source in SOURCES
        for node in ast.walk(ast.parse(source.read_text(encoding="utf-8")))
        if isinstance(node, ast.Call) and any(keyword.arg is None for keyword in node.keywords)
    ]


def test_no_call_hides_its_keywords():
    assert hidden_keywords() == [], "write the keywords out (no f(**{...})) so the tools guard can see them"


def test_scan_reaches_subfolders(tmp_path, monkeypatch):
    """P3.1b G3: a call site in core/sub/ must not escape the guard."""
    (tmp_path / "core" / "sub").mkdir(parents=True)
    (tmp_path / "core" / "sub" / "x.py").write_text("f(tools=['shell_exec'])\n", encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "SOURCES", sources(tmp_path))
    assert keyword_values("tools") == [("x.py", 1, "['shell_exec']")]


def test_scan_sees_keyword_unpacking(tmp_path, monkeypatch):
    (tmp_path / "evals").mkdir()
    (tmp_path / "evals" / "y.py").write_text("f(**{'tools': ['shell_exec']})\n", encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "SOURCES", sources(tmp_path))
    assert hidden_keywords() == [("y.py", 1)]


def test_sources_are_scanned():
    assert {"hello_tool.py", "run.py", "stub_tools.py"} <= {source.name for source in SOURCES}
    assert keyword_values("tools"), "no tools= call site found: the scan is broken"


def test_every_tools_list_names_only_bridge_tools():
    """A new `tools=` call site must be added here on purpose."""
    from evals.stub_tools import SPECS

    assert set(SPECS) == set(TOOLS)  # so `list(SPECS)` is exactly the bridge's tool table
    allowed = {
        "list(SPECS)",  # evals: the stubs that mirror the bridge tools
        "['hello_bridge']",  # core/hello_tool.py: the throwaway P0 wiring proof
        "self._tools",  # core/agent.py: the BridgeTool list built from TOOLS
    }
    for file, line, value in keyword_values("tools"):
        assert value in allowed, f"{file}:{line}: tools={value} is not a known bridge tool list"


def test_every_agent_named_brings_no_tools_of_its_own():
    config = tomllib.loads((REPO / "core" / "config.toml").read_text(encoding="utf-8"))
    assert config["agent"]["default_agent"] in AGENTS
    for file, line, value in keyword_values("agent"):
        assert ast.literal_eval(value) in AGENTS, f"{file}:{line}: agent={value}"


def test_executor_built_from_bridge_tools_refuses_built_ins():
    import openjarvis.tools  # noqa: F401  (registers every built-in)
    from openjarvis.core.registry import ToolRegistry
    from openjarvis.core.types import ToolCall
    from openjarvis.tools._stubs import ToolExecutor

    from evals.stub_tools import SPECS

    for name in BUILT_INS:
        assert ToolRegistry.contains(name), f"{name} is no longer a built-in: update BUILT_INS"
    executor = ToolExecutor([ToolRegistry.get(name)() for name in SPECS])
    assert {spec.name for spec in executor.available_tools()} == set(TOOLS)
    for name in BUILT_INS:
        refused = executor.execute(ToolCall("x", name, "{}"))
        assert not refused.success and "Unknown tool" in refused.content, name


@pytest.mark.parametrize("name", BUILT_INS)
def test_built_ins_are_not_bridge_tools(name):
    assert name not in TOOLS
