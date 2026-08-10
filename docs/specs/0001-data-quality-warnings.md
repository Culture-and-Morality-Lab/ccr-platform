# Spec 0001 - Data-quality warnings: very short texts + likely wrong language

**Status:** implemented (2026-07-09)
**Phase:** 0    **Design doc ref:** §12 (language), §11 pipeline step 3 (Text QA)
**Requested by:** Mohammad (Slack brief: "proper warnings - wrong language, super short texts, super long texts")

## Problem
Researchers upload corpora with rows that embed unreliably (very short texts) or that don't
match the language they selected. Today the platform warns about empties, duplicates, and
truncation-length texts, but not about short texts or language mismatch - so silent validity
problems reach published results.

## Contract

**Inputs:** existing run flow; plus the run's selected language (new field, defaults to "en").

**New warnings (structured, in summary.warnings AND run metadata):**

| Code | Severity | Trigger | Message shape |
|---|---|---|---|
| TEXT_TOO_SHORT | warning | N rows with < 4 whitespace-separated tokens | "N text(s) contain fewer than 4 words; CCR scores may be unstable for very short texts." + affected_rows_sample (≤5 row indices) + count |
| LANGUAGE_MISMATCH | warning | corpus-level detected language ≠ selected language, detection confidence ≥ threshold | "You selected {selected}, but the corpus appears to be {detected}." |
| LANGUAGE_UNCERTAIN | info | detection confidence < threshold OR too few detectable rows | "Language could not be determined confidently; language warnings skipped." |
| MODEL_LANGUAGE_UNSUPPORTED | warning | selected language not in the model's supported set (list or resolved set) | "The selected model supports {langs}; you selected {selected}. Switch model or proceed with caution." |

**Language detection design:**
- Corpus-level only: sample up to 200 rows with ≥ 5 tokens; if < 20 such rows → LANGUAGE_UNCERTAIN.
- Library: `lingua-language-detector` (pure-Python wheels, no torch) - add to requirements; record library+version in metadata.
- Never block on language; user may proceed (design §12 user-override rule).

**Warning object schema (all warnings migrate to this shape):**
```json
{ "code": "TEXT_TOO_SHORT", "severity": "warning", "message": "...", "count": 124, "affected_rows_sample": [3, 8, 29] }
```
Existing string warnings become objects with codes: EMPTY_ROWS_DROPPED, DUPLICATE_TEXTS,
TEXTS_MAYBE_TRUNCATED, ENCODING_FALLBACK. UI renders `message`; metadata stores full objects.

**Metadata additions:** `language: {selected, detected, confidence, n_rows_sampled, detector, detector_version}`;
output_schema_version unchanged (no export column changes); warnings schema versioned as part of metadata.

## Non-goals
Row-level language labels; automatic translation; blocking on language; multilingual-corpus
splitting (future spec).

## Tests
- test_short_text_warning_counts_and_samples (4-token boundary: 3 tokens warns, 4 doesn't)
- test_language_mismatch_detected (English selected, Spanish fixture corpus)
- test_language_uncertain_on_tiny_corpus (< 20 detectable rows)
- test_model_language_unsupported (multilingual selected language outside xlm_roberta_100 vs MiniLM en)
- test_warning_objects_shape (all warnings have code/severity/message)
- golden: sample_corpus.csv against SWLS produces byte-stable warning set

## Implementation notes
- Warning construction centralizes in a new `warnings.py` module (engine-side, pure) - first
  extraction step toward packages/ccr_engine.
- Detection runs once at job start on the parsed dataframe; result flows into metadata + warnings.
- UI: no new components - existing warnings panel renders the message strings.

## Deviations (filled after implementation)
- Detector: `langdetect` (seeded, deterministic) instead of lingua - ~1 MB pure-Python vs ~100 MB wheels; detector + version recorded in metadata so an upgrade stays traceable.
- LANGUAGE_MISMATCH threshold implemented as majority-share >= 0.70 across sampled rows.
- MODEL_NOTE (info) added: registry user_warnings surface per run (not in original spec).
