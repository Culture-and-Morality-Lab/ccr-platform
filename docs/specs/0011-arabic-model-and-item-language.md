# Spec 0011 - Arabic embedding model (ATM2) + item-language warning

**Status:** implemented (2026-11-05)
**Phase:** 0    **Design doc ref:** §12 (language), §13 (model registry)
**Requested by:** Deva (2026-11-05), proposing Omartificial-Intelligence-Space/Arabic-Triplet-Matryoshka-V2

## Problem
The only model on the site that covers Arabic is Multilingual E5 Base, which is the weakest
Arabic option we compared (MTEB STS17 ar-ar 74.5). Researchers analysing Arabic text need a
model built for Arabic. The candidate, ATM2, is Arabic-only: it scores 85.3 on Arabic STS17
but 25.8 on English-Arabic pairs, so it cannot compare English items with Arabic texts. Every
construct in the library is in English, and nothing on the site checks the language of the
ITEMS: MODEL_LANGUAGE_UNSUPPORTED only checks the language selected for the texts. An English
construct run with ATM2 on Arabic texts would return plausible-looking, meaningless scores with
no warning. In a real-model check (Arabic SWLS texts, pinned revision), English SWLS items
ranked dissatisfied texts above satisfied ones; the Arabic translation of the same items
ranked them correctly.

## Contract
- Registry: new entry `arabic-triplet-matryoshka-v2`, supported_languages ["ar"], 768 dims,
  512 tokens, no prefix, mean pooling (descriptive), lazy-loaded, pinned to
  17b87422aa4bfb3b478369299e701070b308314f. That revision differs from the MTEB-evaluated one
  (ed357f2) only in README.md. Three picker notes: Arabic only (items too), Modern Standard
  Arabic training data, cross-family comparability.
- Warning (new code, severity `warning`, never blocking):

  | Code | Trigger | Fields |
  |---|---|---|
  | CONSTRUCT_LANGUAGE_UNSUPPORTED | one or more of a construct's items are written in a script (writing system) that none of the model's supported languages use | construct, items_script (script ids), count (offending items), n_items, model_id |

  Each item's script is the script most of its letters belong to (Unicode character names;
  marks, digits and emoji do not vote). Language to script comes from `languages.SCRIPTS`
  (non-Latin languages listed, everything else Latin). Checked for every construct in a run,
  including an anchor's opposite pole. No warning when the model's coverage is unknown or an
  item has no letters. The message names the script and the model's languages; the data keeps
  ids (same convention as MODEL_LANGUAGE_UNSUPPORTED). Same-script mismatches (Spanish items
  on MiniLM) are out of scope, see Deviations.
- Custom constructs: POST /api/constructs now treats `language` as optional. When it is
  omitted (the UI never sends it), the server records a detected language only when the
  items are in a non-Latin script and langdetect is confident (at least 4 words, probability
  at least 0.90) and names a language written in that script. Otherwise it records "en", as
  before. A stated language still wins. This makes the construct snapshot in run metadata say
  "ar" for an Arabic construct instead of "en".
- Metadata: the warning lands in summary.warnings and metadata like every other warning.
  No export column changes; output_schema_version unchanged.

## Non-goals
Cross-lingual CCR (English items on Arabic texts with a multilingual model); per-item
language detection; Arabic translations in the library; Arabic text normalization (the model
card applies none, and the registry never adds preprocessing a model does not ship with).

## Tests
backend/tests/test_construct_language.py:
- units: Arabic items on an English model warn (names in message, ids in data); English
  items on an Arabic model warn; a mixed construct counts only its uncovered items; covered
  script, unknown coverage and letterless items do not; the multilingual set covers both;
  script reading ignores harakat, digits and an embedded Latin brand name.
- regression guards: no library construct (all 117 YAML files) and none of four English
  keyword lists that langdetect misreads (Italian, Catalan, Somali) warns on an English model.
- inference: Arabic records "ar", Persian "fa", Egyptian dialect "ar", keyword lists "en".
- registry: an Arabic-only model exists, pinned to a 40-hex revision, with no prefix and an
  "Arabic" picker note.
- e2e (fake embeddings, models found by language coverage, never by name): English library
  construct on the Arabic model warns; Arabic construct on it is clean; Arabic construct on the
  default model warns; the anchor's opposite pole is checked; fake-model runs skip the check;
  custom constructs record detected, stated, or fallback language.
- golden impact: none. Golden runs use MiniLM with English items, which never trigger it.

## Implementation notes
- languages.py: SCRIPTS (language to writing system), scripts(), display_script().
- warnings_engine.py: text_script, detect_items_language, infer_items_language,
  construct_language_warning.
- jobs.py: one loop after the model-language check.
- main.py + schemas.py: optional construct language, inferred when omitted.
- scripts/bench_models.py: Arabic filler text for models that do not cover English (English
  filler splits into extra subword tokens under an Arabic vocabulary and overstates the time).

## Deviations (filled after implementation)
- The first version detected the items' LANGUAGE with langdetect on the joined items and
  warned below a 0.90 bar. The research-validity review found it misfires on short keyword
  lists, at probability 1.0, so the bar filtered nothing: "piano, violin, cello, opera,
  soprano" was read as Italian, "hotel, taxi, museum" as Catalan, and a list of Islamic terms
  as Somali. Each would have warned on MiniLM and been saved as the construct's language. The
  warning now compares writing systems, which is exact and is what the Arabic case needs.
  Same-script mismatches go unwarned, which is no worse than before this spec.
- Not done (review suggestions, open): recording passes and skips of the check in metadata
  (today only a warning is recorded, as for every other check); a `language_source` field
  (stated, detected, default) on the construct snapshot; backfilling any Arabic custom
  constructs created before this change, which still say "en".
- The step-3 picker gets no new component: the model's "Arabic only" note already shows under
  the dropdown, and the warning appears in the results warnings panel.
