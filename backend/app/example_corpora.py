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
    # First in the list and selected on load. NOT a claim that it is 'the'
    # corpus: the PI's ask was for CAMEL to be available and ready to use.
    preselected: bool = False
    storage_key: str = ""
    # Optional mark for the dataset, served from sample_data/ at /samples.
    # Shown in the info dialog, where it identifies THIS dataset - not in the
    # picker row, which lists several and would imply they share a source.
    logo: str = ""
    # One line under the name in the sample-data list, so a researcher can judge
    # fit before running. The row already shows the count and language.
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

    def blocked_reason(self, row_ceiling: int) -> str:
        """Why this instance cannot run this corpus, or "" if it can.

        A corpus larger than CCR_MAX_ROWS is refused at ingest, so offering it
        as a working option produces a dead end. Saying so up front, and why,
        beats an error after the click - and it corrects itself the moment the
        deployment raises the limit.
        """
        if not self.available():
            return "Not loaded on this instance."
        if row_ceiling and self.n_rows > row_ceiling:
            return (
                f"Too large for this instance: {self.n_rows:,} texts against a "
                f"{row_ceiling:,}-row limit."
            )
        return ""

    def public(self, row_ceiling: int = 0) -> dict:
        data = asdict(self)
        data["bundled"] = self.bundled
        data["logo_url"] = (
            f"/samples/{self.logo}" if self.logo and (SAMPLES_DIR / self.logo).exists() else ""
        )
        data.pop("logo", None)
        blocked = self.blocked_reason(row_ceiling)
        data["usable"] = not blocked
        data["blocked_reason"] = blocked
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
            "Median 25 words, mean 69. Runs in seconds on any model. "
            "Best for a first look at how CCR works."
        ),
        preselected=True,
        logo="camel_logo.png",
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
            "Median 26 words, up to 1,770. Expect a few minutes on MiniLM and "
            "considerably longer on the large models; pick MiniLM unless you have a "
            "reason not to."
        ),
        logo="camel_logo.png",
    ),
]

BY_ID = {e.id: e for e in EXAMPLES}


def get(example_id: str) -> ExampleCorpus | None:
    return BY_ID.get(example_id)


def listed(row_ceiling: int = 0) -> list[dict]:
    """Examples this instance has, preselected one first.

    Entries too large for the row ceiling are still listed but marked unusable
    with a reason, rather than hidden: a corpus quietly vanishing is harder to
    explain than one that says why it is unavailable.
    """
    return [
        e.public(row_ceiling)
        for e in sorted(EXAMPLES, key=lambda e: not e.preselected)
        if e.available()
    ]
