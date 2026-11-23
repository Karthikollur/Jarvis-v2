"""python -m memory ingest [--dry-run] | python -m memory reset-documents"""

import sys

from memory.ingest import ModelMismatch, main

if __name__ == "__main__":
    try:
        main()
    except ModelMismatch as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
