"""The command eval set is well-formed and consistent with the stub tools."""

from collections import Counter
from pathlib import Path

import yaml

from evals.stub_tools import SPECS

CASES = yaml.safe_load(
    (Path(__file__).parent.parent / "evals" / "commands.yaml").read_text(encoding="utf-8")
)


def test_counts_match_plan():
    kinds = Counter(case["expect"] for case in CASES)
    assert len(CASES) == 40
    assert kinds["refuse"] == 10
    assert kinds["clarify"] == 5
    assert set(kinds) == {"tool", "answer", "refuse", "clarify"}


def test_ids_and_prompts_are_unique():
    assert len({case["id"] for case in CASES}) == len(CASES)
    assert len({case["say"] for case in CASES}) == len(CASES)


def test_tool_cases_fit_the_stub_schemas():
    for case in CASES:
        if case["expect"] != "tool":
            assert "tool" not in case and "args" not in case, case["id"]
            continue
        schema = SPECS[case["tool"]][1]  # KeyError = eval names a tool that does not exist
        if "args" not in case:
            continue
        assert set(case["args"]) == set(schema["required"]), case["id"]
        for key, value in case["args"].items():
            allowed = schema["properties"][key].get("enum")
            assert allowed is None or value in allowed, case["id"]


def test_every_stub_tool_is_exercised():
    assert {case.get("tool") for case in CASES} - {None} == set(SPECS)


def test_stub_tools_are_registered_and_record_calls():
    from evals import stub_tools
    from openjarvis.core.registry import ToolRegistry

    for name in SPECS:
        assert ToolRegistry.contains(name)
    stub_tools.CALLS.clear()
    result = ToolRegistry.get("open_app")().execute(app="notepad")
    assert result.success
    assert stub_tools.CALLS == [("open_app", {"app": "notepad"})]
    stub_tools.CALLS.clear()
