"""Bundled example corpora, so a visitor can run CCR without their own data.

Every entry is a file in sample_data/ plus the provenance a researcher needs to
cite it. The citation travels into run metadata (see jobs.py), because results
produced on someone else's corpus have to carry the attribution into whatever
the researcher publishes - a demo dataset is still data with authors.

Adding one: drop the CSV in sample_data/, add an entry here, and say in
`preprocessing` exactly what was done to it. A test checks every file exists,
parses, and has the declared text column.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

SAMPLES_DIR = Path(__file__).resolve().parents[2] / "sample_data"


@dataclass(frozen=True)
class ExampleCorpus:
    """A corpus offered in Step 1.

    Small ones ship in sample_data/ (`filename`); large ones live in object
    storage under the `examples/` prefix (`storage_key`), because a 38 MB file
    in the repo would ride in the Docker image and the Space repo on every
    deploy. Exactly one of the two is set.
    """

    id: str
    name: str
    filename: str
    text_column: str
    language: str
    n_rows: int
    description: str
    citation: str
    source_url: str
    preprocessing: str
    default: bool = False
    storage_key: str = ""
    # Shown on the card so a researcher can judge fit before running.
    detail: str = ""

    @property
    def path(self) -> Path:
        return SAMPLES_DIR / self.filename

    @property
    def bundled(self) -> bool:
        return not self.storage_key

    def available(self) -> bool:
        """Bundled files are checked on disk; stored ones are assumed present -
        a HEAD on every listing would add a network round trip to page load,
        and a missing object surfaces as a clear 404 on selection instead."""
        return self.path.exists() if self.bundled else True

    def public(self) -> dict:
        data = asdict(self)
        data["available"] = self.available()
        data["bundled"] = self.bundled
        data.pop("storage_key", None)  # internal location, not the user's business
        return data


EXAMPLES: list[ExampleCorpus] = [
    ExampleCorpus(
        id="camel_sample",
        name="CAMEL corpus (sample)",
        filename="camel_sample.csv",
        text_column="text",
        language="en",
        n_rows=999,
        description=(
            "The Cultural and Moral Expressions in Language (CAMEL) corpus consists of "
            "over 57 thousand texts taken from several platforms and annotated for 25 "
            "different cultural and moral constructs. This is a 999-text sample drawn "
            "from it, keeping the platform mix of the full corpus (Reddit, Twitter, "
            "IMDB, news, Wikipedia, and others). The full corpus, including the "
            "annotations, is on Hugging Face."
        ),
        citation=(
            "Zewail, A., Setia, A., Mohammadsadegh, R., Seker, F., Hajian, A., Sosa, H., "
            "Morhayim, L., Reddy, S., & Atari, M. (2026). The Cultural and Moral "
            "Expressions in Language (CAMEL) corpus [Preprint]."
        ),
        source_url="https://huggingface.co/datasets/Culture-and-Morality-Lab/CAMEL_Dataset",
        preprocessing=(
            "Usernames were removed by the corpus authors. For this sample: texts drawn "
            "proportionally by source platform with a fixed seed "
            "(scripts/build_camel_sample.py), whitespace trimmed, and only the text and "
            "source_platform columns kept. Text is otherwise verbatim."
        ),
        detail=(
            "999 texts - median 25 words, mean 69. Runs in seconds on any model. "
            "Best for a first look at how CCR works."
        ),
        default=True,
    ),
    ExampleCorpus(
        id="camel_full",
        name="CAMEL corpus (full)",
        filename="",
        storage_key="examples/camel_full.csv",
        text_column="text",
        language="en",
        n_rows=57174,
        description=(
            "The complete Cultural and Moral Expressions in Language (CAMEL) corpus: "
            "57,174 texts from Reddit, Twitter, IMDB, news, Wikipedia, the Internet "
            "Archive and other sources, annotated by the lab for 25 cultural and moral "
            "constructs. The annotation columns come with it, so CCR scores can be "
            "compared against the human ratings."
        ),
        citation=(
            "Zewail, A., Setia, A., Mohammadsadegh, R., Seker, F., Hajian, A., Sosa, H., "
            "Morhayim, L., Reddy, S., & Atari, M. (2026). The Cultural and Moral "
            "Expressions in Language (CAMEL) corpus [Preprint]."
        ),
        source_url="https://huggingface.co/datasets/Culture-and-Morality-Lab/CAMEL_Dataset",
        preprocessing=(
            "Usernames were removed by the corpus authors. Otherwise the corpus exactly "
            "as published: all 64 columns, text verbatim, no sampling."
        ),
        detail=(
            "57,174 texts - median 26 words, up to 1,770. Expect a few minutes on MiniLM "
            "and considerably longer on the large models; pick MiniLM unless you have a "
            "reason not to."
        ),
    ),
]

BY_ID = {e.id: e for e in EXAMPLES}


def get(example_id: str) -> ExampleCorpus | None:
    return BY_ID.get(example_id)


def listed() -> list[dict]:
    """Available examples, the default first."""
    return [e.public() for e in sorted(EXAMPLES, key=lambda e: not e.default) if e.available()]
