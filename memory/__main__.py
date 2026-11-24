"""python -m memory ingest [--dry-run] | reset-documents | review | facts | forget <id>"""

import sys

from memory.ingest import ModelMismatch, main as ingest_main
from memory.review import main as review_main

if __name__ == "__main__":
    argv = sys.argv[1:]
    try:
        if argv and argv[0] in {"review", "facts", "forget"}:
            review_main()
        else:
            ingest_main()
    except ModelMismatch as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
