"""Fast-path router: exact matches only, everything else falls through."""

from pathlib import Path

import pytest
import yaml

from core.router import APP_ALIASES, route
from evals.stub_tools import APPS

CASES = yaml.safe_load(
    (Path(__file__).parent.parent / "evals" / "commands.yaml").read_text(encoding="utf-8")
)


@pytest.mark.parametrize(
    ("said", "expected"),
    [
        ("What time is it?", ("get_time", {})),
        ("what's the time", ("get_time", {})),
        ("Hey Jarvis, what is today's date?", ("get_time", {})),
        ("Open VS Code.", ("open_app", {"app": "vscode"})),
        ("  launch   the calculator  ", ("open_app", {"app": "calculator"})),
        ("Jarvis, open notepad please", ("open_app", {"app": "notepad"})),
        ("Start my browser.", ("open_app", {"app": "browser"})),
        ("stop", ("stop", {})),
        ("Jarvis, STOP!", ("stop", {})),
        ("cancel that", ("stop", {})),
    ],
)
def test_common_commands_match(said, expected):
    assert route(said) == expected


@pytest.mark.parametrize(
    "said",
    [
        "",
        "Open it.",
        "open the pod bay doors",
        "open powershell",  # not on the allowlist
        "open notepad and delete everything",
        "open C:\\Windows\\System32\\cmd.exe",
        "stop the dev server script",
        "don't stop",
        "what time is the meeting",
        "is it time to open notepad",
        "start the dev server script",
        "Run this in PowerShell: Remove-Item -Recurse C:\\Users",
    ],
)
def test_near_misses_fall_through_to_the_model(said):
    assert route(said) is None


def test_aliases_only_point_at_allowlisted_apps():
    assert set(APP_ALIASES.values()) <= set(APPS)


def test_router_never_disagrees_with_the_eval_set():
    """On all 40 eval commands the router is either silent or exactly right.

    In particular every must-refuse and ambiguous command falls through.
    """
    for case in CASES:
        routed = route(case["say"])
        if case["expect"] == "tool" and routed is not None:
            assert routed == (case["tool"], case["args"]), case["id"]
        else:
            assert routed is None or case["expect"] == "tool", case["id"]
