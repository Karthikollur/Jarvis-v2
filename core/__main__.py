"""One request from the command line. The bridge must already be running."""

from __future__ import annotations

import sys
import urllib.error

from core.agent import build
from core.bridge_client import BridgeError


def _say(pending_id) -> None:
    print(f"pending {pending_id}: approve or deny in tab 2")


def main(argv=None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    try:
        core = build(on_pending=_say)
        print(core.handle(" ".join(argv)))
        for result in core.results:
            line = "ok" if result.success else result.content
            print(f"  {result.tool_name}: {line}")
    except urllib.error.URLError:
        print("bridge is not running")
        raise SystemExit(1)
    except (OSError, BridgeError) as error:
        print(f"bridge error: {error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
