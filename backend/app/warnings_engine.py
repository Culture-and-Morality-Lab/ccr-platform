"""Structured data-quality warnings (spec 0001, design doc §12).

Every warning is an object - {code, severity, message, count?, affected_rows_sample?} -
never a bare string. Codes are UPPER_SNAKE and stable: downstream notebooks and the UI
key off them. Severity: "info" (status, not a problem) | "warning" (proceed with care).
Language detection is corpus-level only; short texts are exactly where detection is
unreliable, so uncertainty is reported instead of guessed away.

Deviation from spec 0001 (recorded there): langdetect instead of lingua - pure-Python,
~1 MB vs ~100 MB wheels; seeded for determinism. Upgrade path preserved by recording
detector + version in metadata.
"""

from __future__ import annotations

import unicodedata
from collections import Counter
from dataclasses import dataclass

from .languages import KNOWN_SCRIPTS, display, display_script, display_set, scripts

MIN_TOKENS_STABLE = 4          # texts below this are flagged TEXT_TOO_SHORT
DETECT_MIN_TOKENS = 5          # rows shorter than this are skipped for detection
DETECT_SAMPLE_MAX = 200        # rows sampled for corpus-level detection
DETECT_MIN_ROWS = 20           # fewer detectable rows -> LANGUAGE_UNCERTAIN
DETECT_CONFIDENCE = 0.70       # majority share below this -> LANGUAGE_UNCERTAIN
SAMPLE_ROWS_SHOWN = 5
# Item language (spec 0011). The WARNING compares writing systems, item by
# item, which is exact: statistical detection is not, and it reads short
# English keyword lists as Italian, Catalan or Somali at probability 1.0
# ("piano, violin, cello" -> it). langdetect is used only to NAME the language
# a custom construct is recorded under, and only for non-Latin scripts, where
# it is reliable and the old "en" default was certainly wrong.
ITEM_DETECT_MIN_WORDS = 4
ITEM_DETECT_CONFIDENCE = 0.90


def warning(code: str, severity: str, message: str, **extra) -> dict:
    return {"code": code, "severity": severity, "message": message, **extra}


# ---------------------------------------------------------------- text QA
def short_text_warning(texts: list[str]) -> dict | None:
    idx = [i for i, t in enumerate(texts) if len(t.split()) < MIN_TOKENS_STABLE]
    if not idx:
        return None
    return warning(
        "TEXT_TOO_SHORT",
        "warning",
        f"{len(idx)} text(s) contain fewer than {MIN_TOKENS_STABLE} words; "
        "CCR scores may be unstable for very short texts.",
        count=len(idx),
        affected_rows_sample=idx[:SAMPLE_ROWS_SHOWN],
    )


# ---------------------------------------------------------- language checks
@dataclass
class LanguageResult:
    selected: str
    detected: str | None
    confidence: float | None
    n_rows_sampled: int
    detector: str
    detector_version: str

    def as_metadata(self) -> dict:
        return {
            "selected": self.selected,
            "detected": self.detected,
            "confidence": self.confidence,
            "n_rows_sampled": self.n_rows_sampled,
            "detector": self.detector,
            "detector_version": self.detector_version,
        }


def detect_corpus_language(texts: list[str], selected: str) -> tuple[LanguageResult, list[dict]]:
    """Corpus-level majority-vote detection on a sample of detectable rows."""
    from langdetect import DetectorFactory, detect  # lazy import
    from langdetect.lang_detect_exception import LangDetectException

    try:
        from importlib.metadata import version as _v

        detector_version = _v("langdetect")
    except Exception:
        detector_version = "unknown"

    DetectorFactory.seed = 0  # determinism - same corpus, same result, every run

    detectable = [t for t in texts if len(t.split()) >= DETECT_MIN_TOKENS][:DETECT_SAMPLE_MAX]
    warnings: list[dict] = []

    if len(detectable) < DETECT_MIN_ROWS:
        result = LanguageResult(selected, None, None, len(detectable), "langdetect", detector_version)
        warnings.append(
            warning(
                "LANGUAGE_UNCERTAIN",
                "info",
                f"Language could not be determined confidently ({len(detectable)} detectable "
                f"row(s), need {DETECT_MIN_ROWS}); language checks were skipped.",
            )
        )
        return result, warnings

    votes: dict[str, int] = {}
    for t in detectable:
        try:
            lang = detect(t)  # one detection per row (detect() is the expensive call)
        except LangDetectException:
            continue
        votes[lang] = votes.get(lang, 0) + 1

    if not votes:
        result = LanguageResult(selected, None, None, len(detectable), "langdetect", detector_version)
        warnings.append(
            warning("LANGUAGE_UNCERTAIN", "info",
                    "Language detection produced no result; language checks were skipped.")
        )
        return result, warnings

    top_lang, top_count = max(votes.items(), key=lambda kv: kv[1])
    confidence = round(top_count / sum(votes.values()), 3)
    result = LanguageResult(selected, top_lang, confidence, len(detectable), "langdetect", detector_version)

    if confidence < DETECT_CONFIDENCE:
        warnings.append(
            warning(
                "LANGUAGE_UNCERTAIN",
                "info",
                f"Detected language is uncertain (top candidate {display(top_lang)} at "
                f"{confidence:.0%} of sampled rows); interpret language checks with care.",
            )
        )
    elif top_lang != selected.lower():
        warnings.append(
            warning(
                "LANGUAGE_MISMATCH",
                "warning",
                f"You selected {display(selected)}, but the corpus appears to be "
                f"{display(top_lang)} ({confidence:.0%} of {len(detectable)} sampled rows).",
                detected_language=top_lang,
                selected_language=selected,
            )
        )
    return result, warnings


def model_language_warning(selected: str, model_id: str, supported: frozenset[str],
                           language_set_name: str | None) -> dict | None:
    if not supported or selected.lower() in supported:
        return None
    label = display_set(language_set_name) if language_set_name else \
        ", ".join(display(c) for c in sorted(supported))
    return warning(
        "MODEL_LANGUAGE_UNSUPPORTED",
        "warning",
        f"The selected model supports {label}, but you selected {display(selected)}. "
        "Switch to a multilingual model or proceed with caution.",
        selected_language=selected,
        model_id=model_id,
    )


def detect_items_language(items: list[str]) -> tuple[str | None, float | None]:
    """Detect the language of a construct's items, joined into one text.

    Returns (iso_code, probability), or (None, None) when the items are too
    short to detect. langdetect's regional codes ("zh-cn") are reduced to the
    base ISO 639-1 code the registry uses.
    """
    from langdetect import DetectorFactory, detect_langs  # lazy import
    from langdetect.lang_detect_exception import LangDetectException

    joined = " ".join(t.strip().rstrip(".") + "." for t in items if t and t.strip())
    if len(joined.split()) < ITEM_DETECT_MIN_WORDS:
        return None, None
    DetectorFactory.seed = 0  # determinism, as for the corpus check
    try:
        top = detect_langs(joined)[0]
    except LangDetectException:
        return None, None
    return top.lang.split("-")[0].lower(), round(top.prob, 3)


def text_script(text: str) -> str | None:
    """The writing system most of a text's letters are in, or None if it has none.

    Counts only letters in scripts some language maps to, so digits, marks
    (Arabic harakat), emoji and halfwidth/fullwidth forms neither vote nor
    decide. A Latin brand name inside an Arabic item stays Arabic.
    """
    counts: Counter[str] = Counter()
    for ch in text:
        if ch.isalpha():
            name = unicodedata.name(ch, "")
            script = name.split(" ", 1)[0].lower() if name else ""
            if script in KNOWN_SCRIPTS:
                counts[script] += 1
    return counts.most_common(1)[0][0] if counts else None


def infer_items_language(items: list[str], fallback: str = "en") -> str:
    """Language to record for a custom construct whose creator did not state one.

    Latin-script items keep the historical "en": detection cannot tell short
    Latin-script word lists apart (see the note at ITEM_DETECT_*). For other
    scripts the detected language is used only when it is confident AND is
    written in that script, so Arabic items record "ar" and Persian "fa".
    """
    script = text_script(" ".join(items))
    if script in (None, "latin"):
        return fallback
    detected, confidence = detect_items_language(items)
    if (
        detected and confidence is not None and confidence >= ITEM_DETECT_CONFIDENCE
        and script in scripts(detected)
    ):
        return detected
    return fallback


def construct_language_warning(construct_name: str, items: list[str], model_id: str,
                               supported: frozenset[str],
                               language_set_name: str | None) -> dict | None:
    """Warn when a construct's items are written in a script the model does not cover.

    MODEL_LANGUAGE_UNSUPPORTED checks only the language selected for the TEXTS.
    A monolingual model (MiniLM for English, ATM2 for Arabic) given items in
    another writing system still runs, but item and text embeddings are not
    aligned and the similarities carry no construct signal (a real-model check
    with ATM2 and English SWLS items ranked dissatisfied texts first). Each
    item is checked on its own, so a construct mixing Arabic and English items
    is caught too. Same-script mismatches (Spanish items on MiniLM) are out of
    scope: telling those apart needs statistical detection, which misfires on
    short item lists.
    """
    if not supported:  # unknown coverage - never warn on it
        return None
    covered = frozenset().union(*(scripts(c) for c in supported))
    item_scripts = [text_script(t) for t in items]
    bad = [s for s in item_scripts if s is not None and s not in covered]
    if not bad:
        return None
    n_items = sum(1 for s in item_scripts if s is not None)
    bad_scripts = sorted(set(bad))
    script_label = " and ".join(display_script(s) for s in bad_scripts)
    label = display_set(language_set_name) if language_set_name else \
        ", ".join(display(c) for c in sorted(supported))
    if len(bad) == n_items:
        which = f"The items in \"{construct_name}\" are"
    else:
        verb = "is" if len(bad) == 1 else "are"
        which = f"{len(bad)} of {n_items} items in \"{construct_name}\" {verb}"
    return warning(
        "CONSTRUCT_LANGUAGE_UNSUPPORTED",
        "warning",
        f"{which} written in {script_label} script, but the selected model supports "
        f"{label}. The model cannot compare those items with the texts, so the scores "
        "are very likely not meaningful. Use items in a language the model covers (for "
        "example a validated translation of the scale) or a model that covers both "
        "languages.",
        construct=construct_name,
        items_script=bad_scripts,
        count=len(bad),
        n_items=n_items,
        model_id=model_id,
    )
