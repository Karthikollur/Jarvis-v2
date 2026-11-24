"""Tool names and JSON schemas shared by the stub evals and the bridge client.

Moved out of evals/stub_tools.py so core/ does not import evals/ (that import
registers the stubs). This module must not import openjarvis.
"""

from __future__ import annotations

from typing import Any

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
    "open_in_app": (
        "Open a file or folder inside C:\\JarvisSandbox in an allowlisted app, "
        "e.g. VS Code on a project folder.",
        _obj({"app": {"type": "string", "enum": APPS}, "path": _PATH}),
    ),
    "focus_window": (
        "Bring an already open window to the front.",
        _obj({"title": {"type": "string", "description": "App or window name, e.g. Notepad."}}),
    ),
    "remember_fact": (
        "Save something the user asks you to remember. It is kept only after the user approves it.",
        _obj({"text": {"type": "string"}}),
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
        "Search the user's saved facts and local documents (notes, PDFs). Returns passages with their source file.",
        _obj({"query": {"type": "string"}}),
    ),
}
