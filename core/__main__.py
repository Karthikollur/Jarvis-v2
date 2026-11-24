"""One request from the command line. The bridge must already be running."""

from __future__ import annotations

import sys
import threading
import urllib.error

from core.agent import build, sources
from core.bridge_client import BridgeError


def _say(pending_id) -> None:
    print(f"pending {pending_id}: approve or deny in tab 2")


def _handle(core, text):
    box = []

    def run():
        try:
            box.append((True, core.handle(text)))
        except BaseException as error:  # handed to the main thread below
            box.append((False, error))

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    try:
        while thread.is_alive():
            # ponytail: short waits. On Windows (CPython 3.12) Ctrl+C cannot interrupt one
            # long lock wait (OpenJarvis' future.result); it lands between these.
            thread.join(0.2)
    except KeyboardInterrupt:
        core.cancel()
        raise
    ok, value = box[0]
    if not ok:
        raise value
    return value


def main(argv=None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    try:
        core = build(on_pending=_say)
        print(_handle(core, " ".join(argv)))
        for result in core.results:
            if result.tool_name == "recall_memory" and result.success:
                shown = sources([result])
                line = "ok: " + (", ".join(shown) if shown else "no hits")
            else:
                line = "ok" if result.success else result.content
            print(f"  {result.tool_name}: {line}")
    except KeyboardInterrupt:
        print("cancelled")
        raise SystemExit(1)
    except urllib.error.URLError:
        print("bridge is not running")
        raise SystemExit(1)
    except (OSError, BridgeError) as error:
        print(f"bridge error: {error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
