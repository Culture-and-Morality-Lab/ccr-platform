# Spec 0010 - Bundled example corpora (CAMEL)

Status: implemented 2026-09-06
PI request (2026-08-19, via Slack): make the lab's CAMEL corpus the example data
on the site so visitors can try CCR without uploading anything. Corpus details
supplied by Aliah Zewail 2026-09-06.

## Problem

The site only accepted uploaded files, so a visitor with no data of their own
could not run anything, and lab members re-uploaded the same file to demo it.

## Contract

`example_corpora.py` catalogues bundled corpora: id, file, text column,
language, row count, description, citation, source URL, and what preprocessing
was applied. `GET /api/example-corpora` lists them (default first).
`POST /api/projects/{id}/corpora/from-example` copies one into a project
through the normal ingest path, so everything downstream is unchanged.

The corpus row records `example_id`, and a run on it writes a `corpus_source`
block into run metadata carrying the citation, source URL and preprocessing
note. Results produced on someone else's corpus stay attributable in the same
file as the scores.

Step 1 offers the example above the upload control, with the citation and a
link to the full dataset visible, and selects the declared text column on load.

## Update 2026-09-07: the full corpus is offered too

`CCR_MAX_ROWS` is raised to 100,000 (the code default all along; the three docs
that stated 20,000 and 50,000 are corrected), so the 57,174-row corpus is now
ingestible. Both are offered: the 999-text sample stays the DEFAULT because it
finishes in seconds, and the full corpus sits beside it for real analyses,
labelled with its cost.

The full corpus lives in object storage under `examples/`, not in the repo: 38 MB
would ride in the Docker image and the Space repo on every deploy. It is NOT
fetched from Hugging Face at runtime, because that dataset returns 401 - fetching
it would mean shipping lab credentials in a public app.

Selection downloads the master once to parse, then makes the user's copy with a
server-side `copy_object`, so 38 MB does not travel back out through the app per
visitor. Measured against the live bucket: 7.0s fetch, 0.7s parse of 57,174 x 64,
1.6s copy. `storage.delete()` refuses the `examples/` prefix outright, because
every user copy derives from one master and retention runs unattended.

## What ships bundled, and why the sample is the default

CAMEL is 57,174 texts. The platform ships a **999-text sample**, because the
full corpus cannot be the bundled default:

- it exceeds `CCR_MAX_ROWS` (50,000 on both deployments), so ingest would
  refuse it outright;
- it is 38 MB against a `sample_data/` directory of 156 KB, and that file would
  ride in the Docker image and the Space repo;
- a demo has to finish in seconds on a 2 vCPU host.

The sample is drawn proportionally by source platform with a fixed seed
(`scripts/build_camel_sample.py`), so it keeps the corpus's platform mix rather
than drowning the smaller sources. Its word distribution tracks the full corpus
(median 25 vs 26 words, mean 69.0 vs 71.5). Only `text` and `source_platform`
are kept; text is verbatim, whitespace trimmed. Usernames were already removed
by the corpus authors. The full corpus, with the 25 construct annotations, is
linked from the corpus card and the guide.

Loading an example is exempt from the anonymous upload caps. Those bound what a
stranger can push into the server; this is a file we ship at a size we chose,
and letting a visitor try the platform without their own data is the point of
the feature. The per-day run cap still applies.

## Non-goals

- Serving the full 57k corpus from the platform. It stays on Hugging Face,
  which is a better host for a 38 MB dataset than a Space repo.
- Streaming or paging a corpus larger than `CCR_MAX_ROWS`. If the lab wants
  full-corpus runs, that is the job-duration work already on the ROADMAP, not
  this.

## Tests

- every catalogued example exists, parses, has its declared text column and row
  count, and carries a citation and source URL;
- exactly one default, listed first;
- an ANONYMOUS visitor can load the example and complete a run on it (the whole
  point of the feature), and the picker lands on the right text column;
- the run's metadata carries the CAMEL citation and source URL;
- an unknown example id is a 404.

## Deviations (filled after implementation)

None.
