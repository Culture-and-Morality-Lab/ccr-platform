"""Anchor-vector (bipolar) runs end to end (spec 0006).

Contract under test:
  * an anchored job (target construct + opposite_construct_id) completes and the
    JobOut echoes the anchored fields,
  * the summary is bipolar (per-pole item loadings, target/opposite names, most
    target = top_docs / most opposite = bottom_docs),
  * export columns are target_sim_item_N / opposite_sim_item_N / target_ccr_score
    / opposite_ccr_score / anchor_score under schema version 1.2, and for the dot
    metric anchor_score == target_ccr_score - opposite_ccr_score row by row,
  * metadata carries the scoring block, the anchor block, and BOTH snapshots,
  * the reproduction script embeds both item sets and stays valid Python,
  * validation rejects self-opposition, anchored+multi, bad metric, missing pole.
"""

import ast
import csv
import io
import time

import pytest
from fastapi.testclient import TestClient

from app.main import app

CSV = (
    "id,text\n"
    "1,I am deeply satisfied with my life and grateful every day.\n"
    "2,The bus was late again this morning.\n"
    "3,My life is close to my ideal in most ways.\n"
    "4,We fixed the printer in the lab office.\n"
    "5,Caring for others and protecting the vulnerable matters to me.\n"
)


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
    project = client.post("/api/projects", json={"name": "Anchor"}).json()
    constructs = client.get("/api/constructs").json()
    swls = next(c for c in constructs if c["name"] == "Satisfaction with Life")
    care = next(c for c in constructs if c["name"] == "Moral Foundations - Care")
    return {"project": project, "swls": swls, "care": care}


def _fresh_corpus(client, project_id):
    return client.post(
        f"/api/projects/{project_id}/corpora",
        files={"file": ("c.csv", io.BytesIO(CSV.encode()), "application/octet-stream")},
    ).json()


def _anchored_job(client, setup, metric):
    corpus = _fresh_corpus(client, setup["project"]["id"])
    resp = client.post(
        "/api/jobs",
        json={
            "project_id": setup["project"]["id"],
            "corpus_id": corpus["id"],
            "construct_id": setup["swls"]["id"],
            "opposite_construct_id": setup["care"]["id"],
            "similarity_metric": metric,
            "text_column": "text",
            "model_name": "fake-deterministic",
        },
    )
    assert resp.status_code == 201, resp.text
    return wait_for_job(client, resp.json()["id"])


@pytest.fixture(scope="module")
def cosine_job(client, setup):
    return _anchored_job(client, setup, "cosine")


@pytest.fixture(scope="module")
def dot_job(client, setup):
    return _anchored_job(client, setup, "dot")


def test_anchored_job_completes_and_echoes(cosine_job, setup):
    assert cosine_job["status"] == "completed", cosine_job["error"]
    assert cosine_job["anchored"] is True
    assert cosine_job["opposite_construct_id"] == setup["care"]["id"]
    assert cosine_job["opposite_construct_name"] == "Moral Foundations - Care"
    assert cosine_job["similarity_metric"] == "cosine"


def test_anchored_summary_is_bipolar(client, cosine_job, setup):
    summary = client.get(f"/api/jobs/{cosine_job['id']}/results").json()["summary"]
    assert summary["anchored"] is True
    assert summary["target_name"] == "Satisfaction with Life"
    assert summary["opposite_name"] == "Moral Foundations - Care"
    assert summary["metric"] == "cosine"
    assert len(summary["target_item_means"]) == len(setup["swls"]["items"])
    assert len(summary["opposite_item_means"]) == len(setup["care"]["items"])
    assert summary["top_docs"] and summary["bottom_docs"]
    assert "histogram" in summary and "score_mean" not in summary.get("constructs", {})


def test_anchored_export_columns_and_dot_selfcheck(client, dot_job, setup):
    text = client.get(f"/api/jobs/{dot_job['id']}/export").text
    header = text.splitlines()[0].split(",")
    assert header[:2] == ["id", "text"]
    assert "anchor_score" in header
    assert "target_ccr_score" in header and "opposite_ccr_score" in header
    assert sum(1 for h in header if h.startswith("target_sim_item_")) == len(setup["swls"]["items"])
    assert sum(1 for h in header if h.startswith("opposite_sim_item_")) == len(setup["care"]["items"])
    assert "ccr_score" not in header  # no bare (ambiguous) column
    # dot anchor score is exactly the per-pole difference, row by row.
    for r in csv.DictReader(io.StringIO(text)):
        diff = float(r["target_ccr_score"]) - float(r["opposite_ccr_score"])
        assert abs(float(r["anchor_score"]) - diff) < 1e-4


def test_anchored_metadata(client, cosine_job, setup):
    md = client.get(f"/api/jobs/{cosine_job['id']}/results").json()["metadata"]
    assert md["output_schema_version"] == "1.2"
    assert md["scoring"]["method"] == "anchored_vector"
    assert md["scoring"]["similarity"] == "cosine"
    assert md["anchor"]["target_construct_id"] == setup["swls"]["id"]
    assert md["anchor"]["opposite_construct_id"] == setup["care"]["id"]
    assert md["target_construct"]["snapshot"]["items"]
    assert md["opposite_construct"]["snapshot"]["items"]
    assert md["target_items_sha256_16"] and md["opposite_items_sha256_16"]
    assert "anchor_score" in md["output_schema"]


def test_anchored_script_reproduces(client, cosine_job):
    script = client.get(f"/api/jobs/{cosine_job['id']}/script").text
    ast.parse(script)  # valid offline Python
    assert "TARGET_ITEMS" in script and "OPPOSITE_ITEMS" in script
    assert "AV = target_emb.mean" in script
    assert script.count("doc_emb = model.encode") == 1  # corpus embedded once


def test_anchor_validation_errors(client, setup):
    corpus = _fresh_corpus(client, setup["project"]["id"])
    base = {
        "project_id": setup["project"]["id"],
        "corpus_id": corpus["id"],
        "text_column": "text",
        "model_name": "fake-deterministic",
    }
    swls, care = setup["swls"]["id"], setup["care"]["id"]

    r = client.post("/api/jobs", json={**base, "construct_id": swls, "opposite_construct_id": swls})
    assert r.status_code == 400 and "differ" in r.json()["detail"]

    r = client.post(
        "/api/jobs",
        json={**base, "construct_ids": [swls, care], "opposite_construct_id": care},
    )
    assert r.status_code == 400  # anchored is single-target vs one opposite

    r = client.post(
        "/api/jobs",
        json={**base, "construct_id": swls, "opposite_construct_id": care, "similarity_metric": "euclid"},
    )
    assert r.status_code == 400 and "cosine" in r.json()["detail"]

    r = client.post(
        "/api/jobs",
        json={**base, "construct_id": swls, "opposite_construct_id": "nonexistent"},
    )
    assert r.status_code == 404
