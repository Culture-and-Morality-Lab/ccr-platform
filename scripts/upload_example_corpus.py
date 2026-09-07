#!/usr/bin/env python3
"""Upload a full example corpus to object storage (R2) and report its stats.

Example corpora larger than a few hundred KB do NOT live in the git repo: they
would ride in the Docker image and the Space repo on every deploy. They live in
the configured bucket under `examples/`, a prefix nothing else writes to and
retention never sweeps, so a user's copy can be deleted without touching the
master.

The row count and columns this prints are what belongs in the catalogue entry
in backend/app/example_corpora.py; a test asserts the two agree.

Usage:
    python scripts/upload_example_corpus.py CAMEL.csv camel_full.csv
"""

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def load_env() -> None:
    """Load .env the way the app does. Values are never printed."""
    env = REPO / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        if line.strip() and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    src, dest_name = Path(sys.argv[1]), sys.argv[2]
    if not src.exists():
        raise SystemExit(f"no such file: {src}")

    load_env()
    sys.path.insert(0, str(REPO / "backend"))
    import pandas as pd

    from app import storage

    if storage.backend() != "s3":
        raise SystemExit("CCR_STORAGE is not s3; nothing to upload to.")

    df = pd.read_csv(src, low_memory=False)
    key = f"examples/{dest_name}"
    storage._s3().upload_file(str(src), storage._bucket(), key)

    print(f"uploaded -> s3://{key}  ({src.stat().st_size / 1e6:.1f} MB)")
    print(f"n_rows      = {len(df)}")
    print(f"columns     = {len(df.columns)}")
    print(f"text column = {'text' if 'text' in df.columns else '???'}")
    print("\nPut n_rows in the example_corpora.py entry for this corpus.")


if __name__ == "__main__":
    main()
