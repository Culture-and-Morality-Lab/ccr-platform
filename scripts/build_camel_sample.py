#!/usr/bin/env python3
"""Rebuild sample_data/camel_sample.csv from the full CAMEL corpus.

The platform ships a SAMPLE, not the full corpus, for three reasons that are
properties of the deployment rather than preferences: the full corpus is 57,174
rows against a CCR_MAX_ROWS ceiling of 50,000, it is 38 MB against a sample_data
directory of 156 KB (it would ride in the Docker image and the Space repo), and
a demo has to finish in seconds on a 2 vCPU host. The full corpus stays one
click away on Hugging Face, linked from the corpus description and the guide.

Selection is a proportional draw by source platform rather than a plain random
one, so the sample keeps the corpus's platform mix instead of drowning the
smaller sources. Seeded, so this is reproducible.

Usage:
    python scripts/build_camel_sample.py /path/to/CAMEL.csv
"""

import sys
from pathlib import Path

import pandas as pd

SEED = 20260906
TARGET_ROWS = 1000
PLATFORM_COL = "Source (Platform) "  # trailing space is in the source file
OUT = Path(__file__).resolve().parents[1] / "sample_data" / "camel_sample.csv"


def build(source_csv: str) -> pd.DataFrame:
    full = pd.read_csv(source_csv, low_memory=False)
    frame = full[["text", PLATFORM_COL]].dropna(subset=["text"])
    sample = (
        frame.groupby(PLATFORM_COL, group_keys=False)[["text", PLATFORM_COL]]
        .apply(lambda g: g.sample(max(1, round(TARGET_ROWS * len(g) / len(full))), random_state=SEED))
        .rename(columns={PLATFORM_COL: "source_platform"})
        .sample(frac=1, random_state=SEED)  # interleave platforms
        .reset_index(drop=True)
    )
    sample["text"] = sample["text"].astype(str).str.strip()
    return sample[sample["text"].str.len() > 0].reset_index(drop=True)


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    sample = build(sys.argv[1])
    sample.to_csv(OUT, index=False)
    words = sample["text"].str.split().str.len()
    print(f"wrote {OUT} ({len(sample)} rows)")
    print(f"words: median={words.median():.0f} mean={words.mean():.2f} max={words.max()}")


if __name__ == "__main__":
    main()
