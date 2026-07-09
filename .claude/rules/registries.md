---
paths:
  - "packages/model_registry/**"
  - "packages/construct_library/**"
---

# Registry & construct library rules

- models.yaml is the single source of model truth: id, provider_model_id, pinned revision, supported_languages OR supported_language_set, embedding_dimension, max_seq_length, usage_config (requires_prefix, prefix strings, normalize_embeddings), tiers, operational_config, user-facing warnings.
- The `pooling` field is DESCRIPTIVE only — models load via their own sentence-transformers config; never reimplement pooling.
- E5-family entries must set requires_prefix: true with "query: " on BOTH items and texts.
- supported_language_set values (e.g., xlm_roberta_100) must resolve to real ISO codes in language_sets.py — a bare "multilingual" label is banned.
- Constructs are versioned append-only YAML: editing items/wording/flags creates a NEW version with a new item_hash; never mutate an existing version in place.
- Every construct carries: name, version, language, items (text + reverse_scored), citation, verification_status (draft|needs_verification|verified|archived). Item wordings must be flagged until verified verbatim against the original publication.
- After any change here, run both validators before considering the change done.
