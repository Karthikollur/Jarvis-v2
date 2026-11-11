"""Point OpenJarvis at this repo. Import this BEFORE anything from `openjarvis`.

OpenJarvis resolves its home and config paths at import time. Without these it
falls back to `~/.openjarvis`, which on this machine is an unrelated old install.
"""

import os
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

os.environ.setdefault("OPENJARVIS_HOME", str(REPO / ".openjarvis"))
os.environ.setdefault("OPENJARVIS_CONFIG", str(REPO / "core" / "config.toml"))
