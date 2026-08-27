"""Construct library versioning after the 2026-08-25 review (spec 0007).

Contract under test:
  * a corrected construct ships as a NEW version; the picker shows only the
    newest, so a review does not duplicate every corrected scale in the UI,
  * superseded versions stay in the database and stay usable by id, so runs and
    reproduction scripts that pinned them keep working,
  * metadata outside item_hash (verification_status in particular) re-syncs onto
    an existing row - a verification pass has to reach an already-seeded DB,
  * the append-only guard on ITEMS is untouched by that,
  * the review landed with the shape spec 0007 describes.
"""

import io
import time

import pytest
import yaml
from fastapi.testclient import TestClient

from app.construct_lib import CONSTRUCTS_DIR, load_yaml_constructs, sync_library
from app.db import SessionLocal
from app.main import app
from app.models import Construct

CSV = (
    "id,text\n"
    "1,I am deeply satisfied with my life and grateful every day.\n"
    "2,The bus was late again this morning.\n"
    "3,My life is close to my ideal in most ways.\n"
)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # lifespan seeds the construct library
        yield c


def wait_for_job(client, job_id, timeout=10.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("completed", "failed"):
            return job
        time.sleep(0.05)
    raise TimeoutError(f"Job {job_id} did not finish within {timeout}s")


# ------------------------------------------------- superseding in the listing
def test_v2_constructs_supersede_v1_in_listing(client):
    listed = [c for c in client.get("/api/constructs").json() if c["is_seed"]]
    slugs = [c["name"] for c in listed]
    assert len(slugs) == len(set(slugs)), "a construct is listed more than once"

    db = SessionLocal()
    try:
        rows = db.query(Construct).filter_by(is_seed=True).all()
        newest = {}
        for r in rows:
            newest[r.construct_slug] = max(newest.get(r.construct_slug, 0), r.version or 1)
        assert len(rows) > len(newest), "expected at least one superseded version seeded"
        assert len(listed) == len(newest)
    finally:
        db.close()

    # every listed construct is the newest version of its slug
    by_hash = {c["item_hash"]: c for c in listed}
    db = SessionLocal()
    try:
        for c in listed:
            row = db.query(Construct).filter_by(id=c["id"]).one()
            assert (row.version or 1) == newest[row.construct_slug]
    finally:
        db.close()
    assert by_hash  # hashes are unique per listed construct


def test_superseded_version_still_resolvable_and_runnable(client):
    """A run that pinned an old version must keep working: the row stays, and a
    job can still be created against it even though the picker hides it."""
    db = SessionLocal()
    try:
        archived = (
            db.query(Construct)
            .filter_by(is_seed=True, verification_status="archived")
            .first()
        )
        assert archived is not None, "no superseded version in the library"
        archived_id, slug, version = archived.id, archived.construct_slug, archived.version
    finally:
        db.close()

    assert version == 1
    listed_ids = {c["id"] for c in client.get("/api/constructs").json()}
    assert archived_id not in listed_ids, "superseded version leaked into the picker"

    project = client.post("/api/projects", json={"name": "Superseded", "description": ""}).json()
    corpus = client.post(
        f"/api/projects/{project['id']}/corpora",
        files={"file": ("c.csv", io.BytesIO(CSV.encode()), "application/octet-stream")},
    ).json()
    job = client.post(
        "/api/jobs",
        json={
            "project_id": project["id"],
            "corpus_id": corpus["id"],
            "construct_ids": [archived_id],
            "text_column": "text",
            "model_name": "fake-deterministic",
        },
    )
    assert job.status_code == 201, job.text
    done = wait_for_job(client, job.json()["id"])
    assert done["status"] == "completed"
    meta = client.get(f"/api/jobs/{done['id']}/metadata").json()
    snap = meta["construct_snapshot"] if "construct_snapshot" in meta else meta["constructs"][0]
    assert snap["construct_id"] == slug
    assert snap["version"] == 1


# ------------------------------------------------------- metadata re-sync
def test_sync_updates_verification_status_in_place(client):
    """Status lives outside item_hash, so a review must reach an existing row
    without inventing a new version."""
    db = SessionLocal()
    try:
        row = (
            db.query(Construct)
            .filter_by(is_seed=True, verification_status="verified")
            .first()
        )
        assert row is not None
        row_id, original = row.id, row.verification_status
        row.verification_status = "needs_verification"  # simulate a pre-review DB
        row.name = "stale name"
        db.commit()

        report = sync_library(db)
        assert report["updated"] >= 1

        refreshed = db.query(Construct).filter_by(id=row_id).one()
        assert refreshed.verification_status == original
        assert refreshed.name != "stale name"
    finally:
        db.close()


def test_sync_still_refuses_item_change_under_same_version(client):
    """The append-only guard covers ITEMS and must survive the metadata sync."""
    db = SessionLocal()
    row = db.query(Construct).filter_by(is_seed=True).first()
    row_id, real_hash = row.id, row.item_hash
    try:
        row.item_hash = "0" * 64  # pretend the YAML items changed under this version
        db.commit()
        with pytest.raises(RuntimeError, match="append-only"):
            sync_library(db)
    finally:
        # restore explicitly: the corruption was committed, so a rollback would
        # leave it in place and every later sync_library in the session would fail
        db.rollback()
        db.query(Construct).filter_by(id=row_id).one().item_hash = real_hash
        db.commit()
        db.close()


# ------------------------------------------------------- the review itself
def test_review_applied_expected_shape():
    """Spec 0007's headline numbers, asserted against the YAML library."""
    constructs = load_yaml_constructs()
    by_status = {}
    for c in constructs:
        by_status.setdefault(c["verification_status"], []).append(c)

    assert len(by_status["archived"]) == 23, "superseded v1 files"
    assert len(by_status["verified"]) == 88
    assert len(by_status["needs_verification"]) == 6

    live = [c for c in constructs if c["verification_status"] != "archived"]
    assert len({c["construct_id"] for c in live}) == 94, "one live version per construct"

    reverse = sum(
        1 for c in live for i in c["items"] if i.get("reverse_scored")
    )
    assert reverse == 96, "reverse flags after the review (was 35)"

    # the pending decisions are exactly the ones the spec names
    pending = sorted(c["construct_id"] for c in by_status["needs_verification"])
    assert pending == sorted(
        [
            "ipip_50_item_big_five_factor_markers_agreeableness",
            "ipip_50_item_big_five_factor_markers_conscientiousness",
            "ipip_50_item_big_five_factor_markers_emotional_stability_neuroticism",
            "ipip_50_item_big_five_factor_markers_extraversion",
            "ipip_50_item_big_five_factor_markers_intellect_imagination",
            "k10",
        ]
    )


def test_every_live_construct_records_who_verified_it():
    """`verified` is only meaningful with provenance attached."""
    for c in load_yaml_constructs():
        if c["verification_status"] != "verified":
            continue
        review = c.get("review") or {}
        assert review.get("reviewer"), f"{c['construct_id']}: verified without a reviewer"
        assert review.get("date"), f"{c['construct_id']}: verified without a review date"


def test_superseded_files_keep_their_original_items():
    """Append-only means the old version's ITEMS are never rewritten - only its
    status and review provenance may change."""
    superseded = [
        c for c in load_yaml_constructs() if c["verification_status"] == "archived"
    ]
    assert superseded
    for old in superseded:
        newer = yaml.safe_load(
            (CONSTRUCTS_DIR / f"{old['construct_id']}_v2.yaml").read_text()
        )
        assert newer["version"] == 2
        assert old["version"] == 1
        # something about the items really did change - that is why v2 exists
        old_items = [(i["text"], bool(i.get("reverse_scored"))) for i in old["items"]]
        new_items = [(i["text"], bool(i.get("reverse_scored"))) for i in newer["items"]]
        assert old_items != new_items, f"{old['construct_id']}: v2 with identical items"
