from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_SRC = ROOT / "apps" / "api" / "src"

os.environ.setdefault("VOICEAGENT_DATABASE_URL", "sqlite+pysqlite:///./test_voiceagent.db")
os.environ.setdefault("VOICEAGENT_ENV", "test")

if str(API_SRC) not in sys.path:
    sys.path.insert(0, str(API_SRC))
