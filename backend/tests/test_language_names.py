"""Languages are shown by name, not ISO code (PI request 2026-09-04).

The rule under test is display-only: names are what a human reads, codes stay
the stored and exported form, because they are the reproducibility record and
the output contract.
"""

import pytest
from fastapi.testclient import TestClient

from app.languages import display, display_set
from app.main import SELECTABLE_LANGUAGES, app
from app.warnings_engine import model_language_warning


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_every_code_a_user_can_meet_has_a_name():
    """Coverage guard: a code with no name would render as a bare acronym,
    which is the thing being fixed. Both sources can reach the UI - the
    selectable list, and any language a registry model claims to support."""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "packages" / "model_registry"))
    from language_sets import LANGUAGE_SETS

    missing = [c for c in SELECTABLE_LANGUAGES if display(c) == c]
    assert not missing, f"selectable languages with no name: {missing}"

    for set_name, codes in LANGUAGE_SETS.items():
        unnamed = sorted(c for c in codes if display(c) == c)
        assert not unnamed, f"{set_name} codes with no name: {unnamed}"


def test_display_falls_back_to_the_code_and_never_blanks():
    assert display("ar") == "Arabic"
    assert display("zh-cn") == "Chinese (Simplified)"
    assert display("AR") == "Arabic", "codes are stored lowercase but be forgiving"
    assert display("qq") == "qq", "an unknown code degrades to itself, not to None"
    assert display(None) == "" and display("") == ""


def test_languages_endpoint_returns_code_and_name(client):
    rows = client.get("/api/languages").json()
    assert {"code": "ar", "name": "Arabic"} in rows
    assert [r["code"] for r in rows] == SELECTABLE_LANGUAGES, "codes stay the posted value"


def test_model_language_row_is_named_not_coded(client):
    langs = [m["languages"] for m in client.get("/api/models").json()]
    assert "English" in langs
    assert not any(x == "en" for x in langs), "raw codes must not reach the model list"
    assert display_set("xlm_roberta_100") != "xlm_roberta_100", "set names are humanised too"


def test_language_warnings_name_the_language_but_keep_codes_in_the_data():
    w = model_language_warning("ar", "all-minilm-l6-v2", frozenset({"en"}), None)
    assert "Arabic" in w["message"] and "English" in w["message"]
    assert "'ar'" not in w["message"]
    # the machine-readable field is still the code: exports and metadata read it
    assert w["selected_language"] == "ar"
