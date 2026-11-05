"""Item-language check (spec 0011): CONSTRUCT_LANGUAGE_UNSUPPORTED.

MODEL_LANGUAGE_UNSUPPORTED only compares the TEXT language with the model. A
monolingual model fed items in another language still runs and returns numbers,
but item and text embeddings are not aligned, so the scores mean nothing (for
the Arabic-only ATM2, English SWLS items ranked dissatisfied Arabic texts above
satisfied ones in a real-model check). This warning closes that gap.

Contract under test:
  * items written in a script the model does not cover -> one warning per
    construct, counting the offending items (mixed constructs are caught),
  * covered script, unknown coverage, or items with no letters -> none,
  * NO library construct and no short English keyword list triggers it on the
    default model (false positives on English runs would be the worst failure
    mode; statistical detection reads "piano, violin, cello" as Italian),
  * the job wires it for every construct in a run, including an anchor's
    opposite pole,
  * custom constructs record a detected language only for non-Latin scripts.

Runs use registry models found by their language coverage, never by name, and
CCR_FAKE_EMBEDDINGS=1 so no model is downloaded.
"""

import io
import time

import pytest
from fastapi.testclient import TestClient

from app import construct_lib, registry
from app.main import app
from app.warnings_engine import (
    construct_language_warning,
    detect_items_language,
    infer_items_language,
    text_script,
)

SWLS_AR = [
    "في معظم النواحي، حياتي قريبة من المثالية.",
    "ظروف حياتي ممتازة.",
    "أنا راضٍ عن حياتي.",
    "حتى الآن حصلت على الأشياء المهمة التي أريدها في الحياة.",
    "لو استطعت أن أعيش حياتي من جديد، لما غيرت شيئًا تقريبًا.",
]
SWLS_EN = [
    "In most ways my life is close to my ideal.",
    "The conditions of my life are excellent.",
    "I am satisfied with my life.",
]
EN_ONLY = frozenset({"en"})
AR_ONLY = frozenset({"ar"})


def arabic_only_model():
    return next(
        m for m in registry.list_models()
        if m.supports_language("ar") and not m.supports_language("en")
    )


KEYWORD_LISTS = [  # each one is read as a non-English language by langdetect
    ["piano", "violin", "cello", "opera", "soprano"],                          # it
    ["hotel", "taxi", "museum", "restaurant", "cafe"],                         # ca
    ["Allah", "Quran", "mosque", "imam", "hijab", "Ramadan", "halal", "jihad"],  # so
    ["pasta", "pizza", "risotto", "lasagna", "gelato", "espresso", "tiramisu",
     "focaccia", "ravioli", "cannoli"],
]


# ------------------------------------------------------------------ units
def test_arabic_items_on_english_model_warn_with_names_and_codes():
    w = construct_language_warning("SWLS (Arabic)", SWLS_AR, "m", EN_ONLY, None)
    assert w["code"] == "CONSTRUCT_LANGUAGE_UNSUPPORTED"
    assert w["severity"] == "warning"
    assert "Arabic script" in w["message"] and "English" in w["message"]
    assert w["message"].startswith('The items in "SWLS (Arabic)" are')
    assert w["items_script"] == ["arabic"]  # id in the data, name in the message
    assert w["construct"] == "SWLS (Arabic)"
    assert w["count"] == w["n_items"] == 5


def test_english_items_on_arabic_model_warn():
    w = construct_language_warning("SWLS", SWLS_EN, "m", AR_ONLY, None)
    assert w["code"] == "CONSTRUCT_LANGUAGE_UNSUPPORTED"
    assert w["items_script"] == ["latin"]


def test_mixed_construct_counts_only_the_uncovered_items():
    w = construct_language_warning("Mixed", SWLS_AR + SWLS_EN[:1], "m", AR_ONLY, None)
    assert (w["count"], w["n_items"]) == (1, 6)
    assert w["message"].startswith('1 of 6 items in "Mixed" is written in Latin script')


def test_covered_script_unknown_coverage_and_no_letters_do_not_warn():
    assert construct_language_warning("x", SWLS_AR, "m", AR_ONLY, None) is None
    assert construct_language_warning("x", SWLS_EN, "m", EN_ONLY, None) is None
    assert construct_language_warning("x", SWLS_AR, "m", frozenset(), None) is None
    assert construct_language_warning("x", ["123", "!!!"], "m", AR_ONLY, None) is None


@pytest.mark.parametrize("items", KEYWORD_LISTS)
def test_english_keyword_lists_never_warn_on_english_models(items):
    assert construct_language_warning("kw", items, "m", EN_ONLY, None) is None


def test_multilingual_set_covers_both_scripts():
    m = next(m for m in registry.list_models() if m.language_set_name)
    for items in (SWLS_AR, SWLS_EN):
        assert construct_language_warning(
            "x", items, m.id, m.supported_languages, m.language_set_name
        ) is None


def test_script_reading_ignores_marks_digits_and_embedded_latin():
    assert text_script("الرَّحْمَةُ بِمَنْ يُعَانُونَ") == "arabic"     # harakat
    assert text_script("أستخدم Facebook كل يوم بكثرة") == "arabic"   # brand name
    assert text_script("2026!") is None


def test_inferred_language_only_for_non_latin_scripts():
    assert infer_items_language(SWLS_AR) == "ar"
    assert infer_items_language(["من از زندگی خودم راضی هستم.", "شرایط زندگی من عالی است."]) == "fa"
    assert infer_items_language(
        ["أنا مبسوط قوي النهارده", "الدنيا حلوة وماشية معايا كويس"]  # Egyptian dialect
    ) == "ar"
    for items in KEYWORD_LISTS:
        assert infer_items_language(items) == "en", items
    assert detect_items_language(["Calm.", "Quiet."]) == (None, None)


def test_no_library_construct_warns_on_the_default_model():
    default = registry.default_model()
    offenders = []
    for c in construct_lib.load_yaml_constructs():
        items = [i["text"] if isinstance(i, dict) else i for i in c.get("items", [])]
        w = construct_language_warning(
            c["name"], items, default.id, default.supported_languages,
            default.language_set_name,
        )
        if w:
            offenders.append((c["_file"], w["items_script"]))
    assert not offenders, offenders


def test_registry_has_a_pinned_arabic_only_model_without_prefix():
    m = arabic_only_model()
    assert m.supported_languages == AR_ONLY
    assert m.pinned_revision and len(m.pinned_revision) == 40
    assert not m.requires_prefix and m.item_prefix == "" and m.text_prefix == ""
    assert any("Arabic" in w for w in m.user_warnings), "picker must say Arabic only"


# ------------------------------------------------------------------ e2e
CSV_AR = "text\n" + "\n".join([
    "أنا سعيد جدا بحياتي وعائلتي وعملي.",
    "حياتي صعبة جدا ولا أشعر بأي رضا.",
    "ارتفعت أسعار النفط اليوم في الأسواق العالمية.",
])


def wait_for_job(client, job_id, timeout=10.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("completed", "failed"):
            return job
        time.sleep(0.05)
    raise TimeoutError(f"Job {job_id} did not finish within {timeout}s")


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # lifespan seeds the construct library
        yield c


@pytest.fixture(scope="module")
def setup(client):
    project = client.post(
        "/api/projects", json={"name": "Arabic", "description": "item-language e2e"}
    ).json()
    swls = next(c for c in client.get("/api/constructs").json()
                if c["name"] == "Satisfaction with Life")
    swls_ar = client.post("/api/constructs", json={
        "name": "SWLS Arabic", "items": SWLS_AR,
    })
    assert swls_ar.status_code in (200, 201), swls_ar.text
    return {"project": project, "swls": swls, "swls_ar": swls_ar.json()}


def run(client, setup, model_id, construct_id, **extra):
    # Anonymous uploads are deleted after analysis, so every run uploads afresh.
    corpus = client.post(
        f"/api/projects/{setup['project']['id']}/corpora",
        files={"file": ("ar.csv", io.BytesIO(CSV_AR.encode()), "application/octet-stream")},
    ).json()
    job = client.post("/api/jobs", json={
        "project_id": setup["project"]["id"],
        "corpus_id": corpus["id"],
        "construct_id": construct_id,
        "text_column": "text",
        "model_name": model_id,
        "language": "ar",
        **extra,
    })
    assert job.status_code in (200, 201), job.text
    job = wait_for_job(client, job.json()["id"])
    assert job["status"] == "completed", job["error"]
    body = client.get(f"/api/jobs/{job['id']}/results").json()
    return [w for w in body["summary"]["warnings"]
            if w["code"] == "CONSTRUCT_LANGUAGE_UNSUPPORTED"]


def test_english_library_construct_on_arabic_model_warns(client, setup, monkeypatch):
    monkeypatch.setenv("CCR_FAKE_EMBEDDINGS", "1")
    hits = run(client, setup, arabic_only_model().id, setup["swls"]["id"])
    assert [w["construct"] for w in hits] == ["Satisfaction with Life"]
    assert hits[0]["items_script"] == ["latin"]


def test_arabic_construct_on_arabic_model_is_clean(client, setup, monkeypatch):
    monkeypatch.setenv("CCR_FAKE_EMBEDDINGS", "1")
    assert run(client, setup, arabic_only_model().id, setup["swls_ar"]["id"]) == []


def test_arabic_construct_on_default_english_model_warns(client, setup, monkeypatch):
    monkeypatch.setenv("CCR_FAKE_EMBEDDINGS", "1")
    hits = run(client, setup, registry.default_model().id, setup["swls_ar"]["id"])
    assert [w["items_script"] for w in hits] == [["arabic"]]


def test_anchor_opposite_pole_is_checked_too(client, setup, monkeypatch):
    monkeypatch.setenv("CCR_FAKE_EMBEDDINGS", "1")
    hits = run(
        client, setup, arabic_only_model().id, setup["swls_ar"]["id"],
        opposite_construct_id=setup["swls"]["id"],
    )
    assert [w["construct"] for w in hits] == ["Satisfaction with Life"]


def test_custom_construct_records_its_detected_language(client, setup):
    # The UI never sends a language, so the server infers it from the items;
    # a stated language always wins, and Latin-script items keep "en".
    assert setup["swls_ar"]["language"] == "ar"
    stated = client.post("/api/constructs", json={
        "name": "Stated", "items": SWLS_AR, "language": "AR",
    }).json()
    assert stated["language"] == "ar"
    short = client.post("/api/constructs", json={
        "name": "Short", "items": ["Calm.", "Quiet."],
    }).json()
    assert short["language"] == "en"


def test_fake_model_runs_skip_the_check(client, setup):
    # No registry entry means unknown coverage: never warn on it.
    assert run(client, setup, "fake-deterministic", setup["swls_ar"]["id"]) == []
