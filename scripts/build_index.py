"""Build the optional pgvector semantic index (RETRIEVAL_MODE=true).

Run after init_db.py:
    python scripts/build_index.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from texttosql.knowledge.indexer import build_index  # noqa: E402

if __name__ == "__main__":
    n = build_index()
    print(f"Indexed {n} documents into semantic_index.")
