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


def test_every_catalogued_example_is_attributable_and_well_formed():
    """A catalogue entry with the wrong text column or row count would land the
    picker on the wrong column, or state a size the corpus does not have."""
    assert example_corpora.EXAMPLES, "no examples catalogued"
    for ex in example_corpora.EXAMPLES:
        assert ex.citation and ex.source_url, f"{ex.id}: examples must be attributable"
        assert ex.text_column and ex.n_rows > 0, f"{ex.id}: incomplete entry"
        assert bool(ex.filename) != bool(ex.storage_key), (
            f"{ex.id}: set exactly one of filename (bundled) or storage_key (in the bucket)"
        )


def test_bundled_examples_parse_and_match_their_declared_shape():
    """Only the bundled ones can be checked offline; storage-backed corpora are
    verified at upload time by scripts/upload_example_corpus.py."""
    bundled = [e for e in example_corpora.EXAMPLES if e.bundled]
    assert bundled, "expected at least one bundled example"
    for ex in bundled:
        assert ex.path.exists(), f"{ex.id}: {ex.path} missing"
        df, _ = load_corpus(str(ex.path))
        assert ex.text_column in df.columns, f"{ex.id}: no '{ex.text_column}' column"
        assert len(df) == ex.n_rows, f"{ex.id}: declares {ex.n_rows} rows, file has {len(df)}"
        assert df[ex.text_column].astype(str).str.strip().str.len().gt(0).all()


def test_storage_location_is_not_exposed_to_clients():
    """The bucket key is internal; the API should not hand it out."""
    for row in example_corpora.listed():
        assert "storage_key" not in row


def test_exactly_one_preselected_example_and_it_is_listed_first():
    picked = [e for e in example_corpora.EXAMPLES if e.preselected]
    assert len(picked) == 1 and picked[0].id == "camel_sample"
    assert example_corpora.listed()[0]["id"] == "camel_sample"


def test_a_corpus_larger_than_the_row_ceiling_is_listed_but_not_usable():
    """Offering a corpus this instance would refuse at ingest is a dead end.
    It stays visible with the reason, and becomes usable when the deployment
    raises CCR_MAX_ROWS - no code change needed."""
    rows = {r["id"]: r for r in example_corpora.listed(50_000)}
    assert rows["camel_sample"]["usable"] is True
    assert rows["camel_full"]["usable"] is False
    assert "50,000" in rows["camel_full"]["blocked_reason"]

    raised = {r["id"]: r for r in example_corpora.listed(100_000)}
    assert raised["camel_full"]["usable"] is True
    assert raised["camel_full"]["blocked_reason"] == ""


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
    # The UI recognises the project's copy of an example by this field, so a
    # second click selects it instead of copying the corpus again.
    assert corpus["example_id"] == "camel_sample"
    listed = client.get(f"/api/projects/{project['id']}/corpora").json()
    assert next(c for c in listed if c["id"] == corpus["id"])["example_id"] == "camel_sample"

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


def test_shared_example_masters_cannot_be_deleted():
    """Every visitor's copy is made from one master object. Retention runs
    unattended, so deleting a master has to be impossible, not just unlikely."""
    from app import storage

    for locator in ("s3://examples/camel_full.csv", "examples/camel_full.csv"):
        with pytest.raises(ValueError, match="refusing to delete"):
            storage.delete(locator)
    # a normal user corpus is untouched by the guard
    assert storage._is_example_locator("s3://corpora/abc.csv") is False


def test_user_copy_falls_back_when_server_side_copy_is_unavailable(tmp_path, monkeypatch):
    """R2 CopyObject is not available on every bucket: it can answer NoSuchKey
    for an object head_object resolves moments earlier, and the lab's account
    does exactly that while another account copies fine. The file is already
    local (it was downloaded to parse), so the upload path has to take over
    rather than the request failing."""
    from app import storage

    src = tmp_path / "corpus.csv"
    src.write_bytes(b"text\nhello\n")
    uploaded = {}

    class FakeS3:
        def copy_object(self, **kw):
            raise RuntimeError("NoSuchKey")

        def put_object(self, Bucket, Key, Body):
            uploaded[Key] = Body

    monkeypatch.setattr(storage, "backend", lambda: "s3")
    monkeypatch.setattr(storage, "_s3", lambda: FakeS3())
    monkeypatch.setattr(storage, "_bucket", lambda: "test-bucket")

    locator = storage.copy_within_storage("examples/big.csv", "corpora", "abc.csv", src)

    assert locator == "s3://corpora/abc.csv"
    assert uploaded["corpora/abc.csv"] == b"text\nhello\n", "the local copy was uploaded"
    assert not src.exists(), "the temp file is cleaned up either way"
