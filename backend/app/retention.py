"""Data retention (PI decision, 2026-07-10: "remove temp data after analysis").

Policy:
  * ANONYMOUS runs: the uploaded corpus file (and its embedding cache) is
    deleted the moment the run finishes (jobs.py calls remove_corpus_files).
    Result summaries/CSVs stick around so the person can download them, then
    the whole anonymous project is purged after CCR_ANON_TTL_HOURS.
  * SIGNED-IN runs: nothing is auto-deleted; a saved-run cap applies instead
    (enforced at job creation in main.py - the user chooses what to delete).

The purge loop runs in a daemon thread (startup + hourly). TTL of 0 disables
purging entirely - the local-dev default, so nobody's dev projects vanish
overnight. Deployments set CCR_ANON_TTL_HOURS=24.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import or_
from sqlalchemy.orm import Session

from . import auth, storage
from .db import DATA_DIR, SessionLocal
from .models import Construct, Corpus, Job, Project

logger = logging.getLogger("ccr.retention")

EMB_CACHE_DIR = DATA_DIR / "emb_cache"
EMB_CACHE_DIR.mkdir(exist_ok=True)

_stop = threading.Event()
_thread: threading.Thread | None = None


def remove_corpus_files(corpus: Corpus) -> None:
    """Delete the uploaded file (whatever backend holds it) and any cached
    embeddings (always local - caches are derived data)."""
    storage.delete(corpus.path)
    for cached in EMB_CACHE_DIR.glob(f"{corpus.id}_*.npy"):
        cached.unlink(missing_ok=True)


def delete_project_cascade(db: Session, project: Project) -> dict:
    """Shared cascade used by the DELETE endpoint and the anonymous purge.
    Removes DB rows plus uploaded, result, and embedding-cache files. Logs
    counts only - never any uploaded text (design doc §9)."""
    corpora = db.query(Corpus).filter_by(project_id=project.id).all()
    jobs = db.query(Job).filter_by(project_id=project.id).all()

    for corpus in corpora:
        remove_corpus_files(corpus)
    for job in jobs:
        storage.delete(job.result_path)

    # Delete child-first, flushing between levels. The flushes are what make
    # this correct, not the call order: within a single flush SQLAlchemy sorts
    # DELETEs by mapper dependency, and Job has no ORM relationship to Corpus
    # (only a raw ForeignKey column), so it is free to emit DELETE FROM corpora
    # before DELETE FROM jobs and trip jobs_corpus_id_fkey. Postgres enforces
    # that constraint; SQLite only does with foreign_keys=ON (see db.py). One
    # transaction still commits the whole cascade, so a failure rolls it all
    # back rather than stranding a half-deleted project.
    for job in jobs:
        db.delete(job)
    db.flush()
    for corpus in corpora:
        db.delete(corpus)
    db.flush()
    db.delete(project)
    db.commit()
    return {"corpora": len(corpora), "runs": len(jobs)}


def purge_expired_anonymous(db: Session) -> int:
    """Delete anonymous projects whose last activity is older than the TTL."""
    ttl = auth.anon_ttl_hours()
    if ttl <= 0:
        return 0
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=ttl)).isoformat(timespec="seconds")

    purged = 0
    candidates = (
        db.query(Project)
        .filter(auth.anonymous_owner_clause(Project.owner_user_id))
        .all()
    )
    for project in candidates:
        latest_job = (
            db.query(Job.created_at)
            .filter_by(project_id=project.id)
            .order_by(Job.created_at.desc())
            .first()
        )
        last_activity = max(project.created_at, latest_job[0]) if latest_job else project.created_at
        if last_activity < cutoff:
            counts = delete_project_cascade(db, project)
            purged += 1
            logger.info(
                "purged expired anonymous project id=%s (corpora=%d runs=%d, ttl=%dh)",
                project.id, counts["corpora"], counts["runs"], ttl,
            )
    return purged


def purge_expired_anonymous_constructs(db: Session) -> int:
    """Delete anonymous custom constructs older than the TTL.

    Custom constructs were the one anonymous artifact with no lifecycle at all:
    corpora go the moment a run finishes and projects expire on this TTL, but a
    construct anyone typed stayed in the database and in the picker forever, so
    a public instance accumulated them without bound (spec 0009).

    Constructs are not owned by a project, so this is a separate sweep. A
    construct a run still references is left alone: Job.construct_id is a
    foreign key and the run's metadata is its reproducibility record. Run this
    AFTER the project sweep, which removes the anonymous runs that were holding
    most of them.
    """
    ttl = auth.anon_ttl_hours()
    if ttl <= 0:
        return 0
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=ttl)).isoformat(timespec="seconds")

    expired = (
        db.query(Construct)
        .filter(Construct.is_seed.is_(False))
        .filter(auth.anonymous_owner_clause(Construct.owner_user_id))
        .filter(Construct.created_at < cutoff)
        .all()
    )
    purged = 0
    for construct in expired:
        still_used = (
            db.query(Job.id)
            .filter(
                or_(
                    Job.construct_id == construct.id,
                    Job.opposite_construct_id == construct.id,
                    Job.construct_ids_json.contains(construct.id),
                )
            )
            .first()
        )
        if still_used:
            continue
        db.delete(construct)
        purged += 1
    if purged:
        db.commit()
        logger.info("purged %d expired anonymous construct(s) (ttl=%dh)", purged, ttl)
    return purged


def purge_expired_anonymous_all(db: Session) -> dict:
    """Both anonymous sweeps, in the order that lets constructs actually go:
    projects first (which removes the runs referencing them), constructs after."""
    projects = purge_expired_anonymous(db)
    constructs = purge_expired_anonymous_constructs(db)
    return {"projects": projects, "constructs": constructs}


def _loop(interval_seconds: int) -> None:
    while not _stop.wait(interval_seconds):
        db = SessionLocal()
        try:
            purge_expired_anonymous_all(db)
        except Exception:
            logger.exception("anonymous purge failed; will retry next cycle")
        finally:
            db.close()


def start_cleanup(interval_seconds: int = 3600) -> None:
    """Run one purge now, then hourly in a daemon thread. No-op if TTL is 0."""
    global _thread
    db = SessionLocal()
    try:
        purge_expired_anonymous(db)
    except Exception:
        logger.exception("startup anonymous purge failed")
    finally:
        db.close()
    if auth.anon_ttl_hours() > 0 and (_thread is None or not _thread.is_alive()):
        _stop.clear()
        _thread = threading.Thread(target=_loop, args=(interval_seconds,), daemon=True,
                                   name="ccr-retention")
        _thread.start()


def stop_cleanup() -> None:
    _stop.set()
