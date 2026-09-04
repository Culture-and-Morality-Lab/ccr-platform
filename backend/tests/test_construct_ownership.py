"""Custom construct ownership and deletion (spec 0008).

Reported from the public site: constructs another visitor created were listed
to everyone, with no way to remove them. Constructs had no owner column at all,
so this is the projects leak (049074a) one table over.
"""

import io
import time

import pytest
from fastapi.testclient import TestClient

from app.main import app

CSV = b"text\nI am satisfied with my life.\nThe bus was late again.\n"


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def register(client, email, name="Someone"):
    resp = client.post(
        "/api/auth/register", json={"email": email, "password": "password123", "name": name}
    )
    assert resp.status_code == 201, resp.json()


def logout(client):
    client.post("/api/auth/logout")


def make_construct(client, name):
    resp = client.post(
        "/api/constructs",
        json={"name": name, "description": "", "reference": "", "items": ["An item."]},
    )
    assert resp.status_code == 201, resp.json()
    return resp.json()["id"]


def listed_ids(client):
    resp = client.get("/api/constructs")
    assert resp.status_code == 200
    return {c["id"] for c in resp.json()}


def test_signed_in_user_does_not_see_other_peoples_custom_constructs(client):
    """The reported bug: one account's construct showed up for everyone."""
    register(client, "s0008-owner-a@test.edu")
    mine = make_construct(client, "Construct A")
    logout(client)

    # a different account must not see it
    register(client, "s0008-owner-b@test.edu")
    assert mine not in listed_ids(client)
    theirs = make_construct(client, "Construct B")
    assert theirs in listed_ids(client), "a user must still see their own"
    logout(client)

    # and neither account's construct leaks to an anonymous visitor
    anon = listed_ids(client)
    assert mine not in anon and theirs not in anon


def test_signed_in_user_does_not_see_another_visitors_anonymous_constructs(client):
    """What the reporter actually saw: a stranger's anonymous construct showing
    up in their signed-in picker. A SEPARATE client is a separate browser, so
    its anonymous session is a different one (spec 0009)."""
    with TestClient(app) as stranger:
        theirs = make_construct(stranger, "Left behind by a visitor")

    register(client, "s0008-fresh@test.edu")
    assert theirs not in listed_ids(client)
    client.post("/api/auth/logout")
    # ...and not to a different anonymous visitor either
    assert theirs not in listed_ids(client)


def test_signing_in_adopts_this_browsers_anonymous_constructs(client):
    """The other half of scoping: your OWN anonymous work has to follow you
    into the account, or "sign in to keep it" would be a lie."""
    mine = make_construct(client, "Drafted before signing up")
    register(client, "s0009-adopter@test.edu")
    assert mine in listed_ids(client), "anonymous work must transfer on sign-in"


def test_anonymous_construct_creation_is_capped_per_day(client):
    """Construct creation was the one unbounded anonymous write path."""
    from app import auth

    cap = auth.anon_max_constructs_per_day()
    for i in range(cap):
        assert (
            client.post(
                "/api/constructs",
                json={"name": f"Capped {i}", "description": "", "reference": "",
                      "items": ["An item."]},
            ).status_code
            == 201
        )
    refused = client.post(
        "/api/constructs",
        json={"name": "One too many", "description": "", "reference": "",
              "items": ["An item."]},
    )
    assert refused.status_code == 429
    assert "sign in" in refused.json()["detail"].lower()


def test_expired_anonymous_constructs_are_purged(client, monkeypatch):
    """Constructs had no lifecycle at all: they outlived the projects and runs
    that used them, forever, which is what filled the public picker."""
    from app.db import SessionLocal
    from app.models import Construct
    from app.retention import purge_expired_anonymous_constructs

    monkeypatch.setenv("CCR_ANON_TTL_HOURS", "24")
    old = make_construct(client, "Stale anonymous draft")
    fresh = make_construct(client, "Made just now")

    db = SessionLocal()
    try:
        db.get(Construct, old).created_at = "2020-01-01T00:00:00+00:00"
        db.commit()
        assert purge_expired_anonymous_constructs(db) == 1
        assert db.get(Construct, old) is None
        assert db.get(Construct, fresh) is not None
    finally:
        db.close()


def test_purge_keeps_a_construct_a_run_still_references(client, monkeypatch):
    """A run's construct row backs a foreign key and its reproducibility
    record, so the TTL sweep must not take it."""
    from app.db import SessionLocal
    from app.models import Construct
    from app.retention import purge_expired_anonymous_constructs

    monkeypatch.setenv("CCR_ANON_TTL_HOURS", "24")
    project = client.post("/api/projects", json={"name": "P", "description": ""}).json()
    corpus = client.post(
        f"/api/projects/{project['id']}/corpora",
        files={"file": ("c.csv", io.BytesIO(CSV), "text/csv")},
    ).json()
    cid = make_construct(client, "Used then aged")
    job = client.post(
        "/api/jobs",
        json={"project_id": project["id"], "corpus_id": corpus["id"],
              "construct_ids": [cid], "text_column": "text",
              "model_name": "fake-deterministic"},
    )
    assert job.status_code == 201, job.text

    db = SessionLocal()
    try:
        db.get(Construct, cid).created_at = "2020-01-01T00:00:00+00:00"
        db.commit()
        assert purge_expired_anonymous_constructs(db) == 0
        assert db.get(Construct, cid) is not None
    finally:
        db.close()


def test_seeds_stay_visible_to_everyone(client):
    seeds = [c for c in client.get("/api/constructs").json() if c["is_seed"]]
    assert seeds, "library constructs must be listed anonymously"
    register(client, "s0008-seed-viewer@test.edu")
    assert [c for c in client.get("/api/constructs").json() if c["is_seed"]]


def test_delete_removes_an_unused_construct(client):
    register(client, "s0008-deleter@test.edu")
    cid = make_construct(client, "Throwaway")
    assert cid in listed_ids(client)

    resp = client.delete(f"/api/constructs/{cid}")
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"deleted": True, "hidden": False, "used_by_runs": 0}
    assert cid not in listed_ids(client)
    assert client.delete(f"/api/constructs/{cid}").status_code == 404


def test_cannot_delete_a_seed_or_someone_elses(client):
    seed = next(c for c in client.get("/api/constructs").json() if c["is_seed"])
    assert client.delete(f"/api/constructs/{seed['id']}").status_code == 403

    register(client, "s0008-victim@test.edu")
    theirs = make_construct(client, "Not yours")
    logout(client)
    register(client, "s0008-attacker@test.edu")
    # 404 rather than 403: do not confirm that another account's construct exists
    assert client.delete(f"/api/constructs/{theirs}").status_code == 404
    logout(client)
    assert theirs in listed_ids_for_owner(client, "s0008-victim@test.edu")


def listed_ids_for_owner(client, email):
    client.post("/api/auth/login", json={"email": email, "password": "password123"})
    return listed_ids(client)


def test_construct_used_by_a_run_is_hidden_not_deleted(client):
    """Job.construct_id is a FK and the run's metadata is the reproducibility
    record, so a used construct leaves the listing without breaking the run."""
    register(client, "s0008-runner@test.edu")
    project = client.post("/api/projects", json={"name": "P", "description": ""}).json()
    corpus = client.post(
        f"/api/projects/{project['id']}/corpora",
        files={"file": ("c.csv", io.BytesIO(CSV), "text/csv")},
    ).json()
    cid = make_construct(client, "Used by a run")

    job = client.post(
        "/api/jobs",
        json={
            "project_id": project["id"],
            "corpus_id": corpus["id"],
            "construct_ids": [cid],
            "text_column": "text",
            "model_name": "fake-deterministic",
        },
    )
    assert job.status_code == 201, job.text
    job_id = job.json()["id"]
    deadline = time.time() + 10
    while time.time() < deadline:
        if client.get(f"/api/jobs/{job_id}").json()["status"] in ("completed", "failed"):
            break
        time.sleep(0.05)
    assert client.get(f"/api/jobs/{job_id}").json()["status"] == "completed"

    resp = client.delete(f"/api/constructs/{cid}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["deleted"] is False and body["hidden"] is True and body["used_by_runs"] == 1

    assert cid not in listed_ids(client), "hidden constructs leave the picker"
    # the run and its reproducibility record still resolve
    assert client.get(f"/api/jobs/{job_id}").status_code == 200
    assert client.get(f"/api/jobs/{job_id}/metadata").status_code == 200
