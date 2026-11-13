"""Stub tools for the command evals (P1). They record calls and do nothing.

Names and parameters mirror the real tools planned for P3, so the eval set keeps
working when the stubs are swapped for bridge-backed tools (P3.5).

Names must not collide with OpenJarvis built-ins: its registry raises on a
duplicate key (e.g. `memory_search` is taken, hence `recall_memory`).
"""

from __future__ import annotations

from typing import Any

import core.openjarvis_env  # noqa: F401  (must precede openjarvis imports)
from openjarvis.core.registry import ToolRegistry
from openjarvis.core.types import ToolResult
from openjarvis.tools._stubs import BaseTool, ToolSpec

APPS = ["vscode", "notepad", "calculator", "browser", "explorer"]
SCRIPTS = ["dev_server", "run_tests", "backup_notes"]

_PATH = {"type": "string", "description": "Absolute Windows path inside C:\\JarvisSandbox."}


def _obj(properties: dict[str, Any] | None = None) -> dict[str, Any]:
    properties = properties or {}
    return {"type": "object", "properties": properties, "required": list(properties)}


# name -> (description, JSON-schema parameters). Every parameter is required.
SPECS: dict[str, tuple[str, dict[str, Any]]] = {
    "get_time": ("Get the current local date and time.", _obj()),
    "list_windows": ("List the windows and apps currently open on the desktop.", _obj()),
    "system_stats": ("Get current CPU, RAM, GPU and VRAM usage.", _obj()),
    "list_dir": ("List the files and folders in a folder.", _obj({"path": _PATH})),
    "read_text_file": ("Read the contents of a text file.", _obj({"path": _PATH})),
    "open_app": (
        "Open an application from the allowlist.",
        _obj({"app": {"type": "string", "enum": APPS}}),
    ),
    "focus_window": (
        "Bring an already open window to the front.",
        _obj({"title": {"type": "string", "description": "App or window name, e.g. Notepad."}}),
    ),
    "create_folder": ("Create a new folder.", _obj({"path": _PATH})),
    "move_file": (
        "Move a file into another folder.",
        _obj(
            {
                "source": _PATH,
                "destination": {**_PATH, "description": "Destination FOLDER inside C:\\JarvisSandbox."},
            }
        ),
    ),
    "move_files": (
        "Move several files (up to 20) into one folder.",
        _obj(
            {
                "sources": {"type": "array", "items": _PATH, "minItems": 1, "maxItems": 20},
                "destination": {**_PATH, "description": "Destination FOLDER inside C:\\JarvisSandbox."},
            }
        ),
    ),
    "rename_file": (
        "Rename a file, keeping it in the same folder.",
        _obj(
            {
                "path": _PATH,
                "new_name": {"type": "string", "description": "New file name only, no folder."},
            }
        ),
    ),
    "delete_file": ("Delete a file (it is moved to quarantine).", _obj({"path": _PATH})),
    "run_named_script": (
        "Run one of the pre-approved named scripts.",
        _obj({"name": {"type": "string", "enum": SCRIPTS}}),
    ),
    "recall_memory": (
        "Search what the user previously asked Jarvis to remember.",
        _obj({"query": {"type": "string"}}),
    ),
}

CALLS: list[tuple[str, dict[str, Any]]] = []  # the eval runner reads and clears this


def _make(name: str, description: str, parameters: dict[str, Any]) -> type[BaseTool]:
    class StubTool(BaseTool):
        tool_id = name

        @property
        def spec(self) -> ToolSpec:
            return ToolSpec(name=name, description=description, parameters=parameters)

        def execute(self, **params: Any) -> ToolResult:
            CALLS.append((name, params))
            return ToolResult(name, f"{name}: done (stub, nothing really happened)", True)

    StubTool.__name__ = f"Stub_{name}"
    return ToolRegistry.register(name)(StubTool)


for _name, (_description, _parameters) in SPECS.items():
    _make(_name, _description, _parameters)
