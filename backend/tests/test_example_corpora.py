"""Bundled example corpora (spec 0010).

The point of the feature is that a visitor with no data of their own can run
CCR, so the anonymous path is the one that has to work.
"""

import time

import pytest
from fastapi.testclient import TestClient

from app import example_corpora
from app.ingest import load_corpus
from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_every_catalogued_example_exists_and_parses():
    """A catalogue entry whose file is missing or whose declared text column is
    wrong would 404 or land the picker on the wrong column at runtime."""
    assert example_corpora.EXAMPLES, "no examples catalogued"
    for ex in example_corpora.EXAMPLES:
        assert ex.path.exists(), f"{ex.id}: {ex.path} missing"
        df, _ = load_corpus(str(ex.path))
        assert ex.text_column in df.columns, f"{ex.id}: no '{ex.text_column}' column"
        assert len(df) == ex.n_rows, f"{ex.id}: declares {ex.n_rows} rows, file has {len(df)}"
        assert df[ex.text_column].astype(str).str.strip().str.len().gt(0).all()
        assert ex.citation and ex.source_url, f"{ex.id}: examples must be attributable"


def test_exactly_one_default_example():
    defaults = [e for e in example_corpora.EXAMPLES if e.default]
    assert len(defaults) == 1 and defaults[0].id == "camel_sample"
    assert example_corpora.listed()[0]["id"] == "camel_sample", "default is listed first"


def test_endpoint_lists_examples(client):
    rows = client.get("/api/example-corpora").json()
    camel = next(r for r in rows if r["id"] == "camel_sample")
    assert camel["text_column"] == "text" and camel["language"] == "en"
    assert "CAMEL" in camel["citation"] and "huggingface.co" in camel["source_url"]


def test_anonymous_visitor_can_load_and_run_the_example(client):
    """The whole feature: no account, no upload, still gets a result.

    The example is deliberately exempt from the anonymous ROW cap (200), which
    a 999-text corpus would otherwise fail - the cap bounds what strangers push
    to the server, and this is a file we ship.
    """
    project = client.post("/api/projects", json={"name": "Example", "description": ""}).json()
    resp = client.post(
        f"/api/projects/{project['id']}/corpora/from-example",
        json={"example_id": "camel_sample"},
    )
    assert resp.status_code == 201, resp.text
    corpus = resp.json()
    assert corpus["n_rows"] == 999
    assert corpus["suggested_text_column"] == "text", "picker should land on the right column"

    seed = next(c for c in client.get("/api/constructs").json() if c["is_seed"])
    job = client.post(
        "/api/jobs",
        json={
            "project_id": project["id"],
            "corpus_id": corpus["id"],
            "construct_ids": [seed["id"]],
            "text_column": "text",
            "model_name": "fake-deterministic",
        },
    )
    assert job.status_code == 201, job.text
    job_id = job.json()["id"]
    deadline = time.time() + 30
    while time.time() < deadline:
        if client.get(f"/api/jobs/{job_id}").json()["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)
    assert client.get(f"/api/jobs/{job_id}").json()["status"] == "completed"

    # attribution has to reach the run record, not just the screen
    meta = client.get(f"/api/jobs/{job_id}/metadata").json()
    assert "CAMEL" in meta["corpus_source"]["citation"]
    assert meta["corpus_source"]["example_id"] == "camel_sample"
    assert "huggingface.co" in meta["corpus_source"]["source_url"]


def test_unknown_example_is_404(client):
    project = client.post("/api/projects", json={"name": "P", "description": ""}).json()
    resp = client.post(
        f"/api/projects/{project['id']}/corpora/from-example",
        json={"example_id": "nope"},
    )
    assert resp.status_code == 404
