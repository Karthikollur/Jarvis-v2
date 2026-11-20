import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from safety.policy import MAX_SECONDS

BASE = "http://127.0.0.1:8765"
TOKEN = Path(os.environ["LOCALAPPDATA"]) / "Jarvis" / "bridge.token"  # read only; the bridge makes it


class BridgeError(RuntimeError):
    """A bridge answer the core cannot continue from (no task id)."""


class BridgeClient:
    def __init__(self, base: str = BASE, token: str | None = None):
        if not base.startswith("http://127.0.0.1:"):
            raise ValueError("bridge must be loopback")  # localhost only, rule 13
        token = TOKEN.read_text(encoding="ascii") if token is None else token
        if not re.fullmatch(r"[0-9a-f]{64}", token):
            raise RuntimeError("Invalid bridge token")
        self._base, self._headers = base.rstrip("/"), {"x-jarvis-token": token, "content-type": "application/json"}

    # No proxies: urlopen would honour HTTP_PROXY and could send a loopback call off the box.
    _opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def _post(self, path: str, body: dict) -> tuple[int, Any]:
        def answer(status: int, raw: bytes) -> tuple[int, Any]:
            try:
                parsed = json.loads(raw or b"{}")
            except ValueError:
                parsed = None
            if not isinstance(parsed, dict):
                return 502, {"detail": f"bad answer from bridge ({status})"}
            return status, parsed

        request = urllib.request.Request(
            self._base + path, data=json.dumps(body).encode(), headers=self._headers, method="POST"
        )
        try:
            with self._opener.open(request, timeout=MAX_SECONDS) as response:
                return answer(response.status, response.read())
        except urllib.error.HTTPError as error:
            return answer(error.code, error.read())

    def new_task(self, fresh: bool) -> str:
        status, body = self._post("/task", {"fresh_context": True} if fresh else {})
        if status != 200:
            raise BridgeError(f"{status}: {body.get('detail', '')}")
        return body["task_id"]

    def tool(self, task_id, name, args) -> tuple[int, Any]:
        return self._post("/tool", {"task_id": task_id, "tool": name, "args": args})

    def outcome(self, pending_id) -> tuple[int, Any]:
        return self._post("/outcome", {"pending_id": pending_id})

    def stop(self) -> tuple[int, Any]:
        return self._post("/stop", {})
