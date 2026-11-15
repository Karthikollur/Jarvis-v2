"""One request from the command line. The bridge must already be running."""

from __future__ import annotations

import sys
import urllib.error

from core.agent import build


def _say(pending_id) -> None:
    print(f"pending {pending_id}: approve or deny in tab 2")


def main(argv=None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    try:
        print(build(on_pending=_say).handle(" ".join(argv)))
    except urllib.error.URLError:
        print("bridge is not running")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
