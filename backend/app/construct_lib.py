"""Construct library loader - seeds the DB from packages/construct_library/constructs/.

Source of truth is the versioned YAML files (spec 0004, design doc §10.1). Rules:
  * append-only: (construct_id, version) is immutable - same version with changed
    items is a hard error, never a silent update;
  * item_hash uses the REFERENCE implementation from validate_constructs.py (loaded
    by file path) so validator, seeder, and metadata always agree;
  * verification_status flows to the UI - unverified wording is visibly flagged.
    It, and the other fields outside the hash, re-sync onto an existing row: a
    library review that verifies wording changes status without changing items,
    and that has to reach databases seeded before the review (spec 0007).

New questionnaires from the lab land as new YAML files; `python packages/construct_library/
validate_constructs.py` first, then restart the app (or call sync) to pick them up.
"""

from __future__ import annotations

import importlib.util
import json
import logging
from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from .models import Construct

logger = logging.getLogger("ccr.constructs")

REPO_ROOT = Path(__file__).resolve().parents[2]
CONSTRUCTS_DIR = REPO_ROOT / "packages" / "construct_library" / "constructs"
_VALIDATOR_PY = REPO_ROOT / "packages" / "construct_library" / "validate_constructs.py"


def _reference_item_hash():
    spec = importlib.util.spec_from_file_location("ccr_construct_validator", _VALIDATOR_PY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.item_hash


def load_yaml_constructs() -> list[dict]:
    files = sorted(CONSTRUCTS_DIR.glob("*.yaml"))
    out = []
    for f in files:
        data = yaml.safe_load(f.read_text())
        data["_file"] = f.name
        out.append(data)
    return out


# Fields that do NOT feed item_hash, so they can change without a new version.
# The YAML library is the durable source of truth and the DB row is the
# operational overlay (see admin.py), which is what makes re-syncing safe.
_MUTABLE_FIELDS = {
    "verification_status": lambda c: c.get("verification_status", "needs_verification"),
    "name": lambda c: c["name"],
    "description": lambda c: c.get("description", ""),
    "reference": lambda c: c.get("citation", ""),
    "category": lambda c: c.get("category", ""),
}


def sync_library(db: Session) -> dict:
    """Idempotent seed/update of library constructs. Returns a small report."""
    item_hash = _reference_item_hash()
    report = {"inserted": 0, "updated": 0, "unchanged": 0, "errors": []}

    for c in load_yaml_constructs():
        slug, version = c["construct_id"], int(c["version"])
        computed_hash = item_hash(c)

        existing = (
            db.query(Construct)
            .filter_by(construct_slug=slug, version=version, is_seed=True)
            .one_or_none()
        )
        if existing:
            if existing.item_hash != computed_hash:
                # Append-only violation: same version, different wording. Refuse loudly.
                report["errors"].append(
                    f"{c['_file']}: items changed under existing version {version} "
                    f"(hash {existing.item_hash[:12]} -> {computed_hash[:12]}). "
                    "Create a NEW version instead of editing this one."
                )
                continue
            # Items are identical, so only non-hash metadata can have moved. Sync it:
            # a verification pass that promotes a construct to `verified` in YAML has
            # to reach databases that were seeded before the pass, and inserting is
            # not an option (the version is unchanged, by design).
            changed = [
                f for f, read in _MUTABLE_FIELDS.items() if getattr(existing, f) != read(c)
            ]
            for f in changed:
                new = _MUTABLE_FIELDS[f](c)
                if f == "verification_status":
                    # A maintainer can set this from /admin, and YAML wins on the
                    # next restart. Say so out loud: an RA who un-verifies a
                    # construct should be able to find out why it came back.
                    logger.warning(
                        "construct %s v%s: verification_status %s -> %s (from YAML %s)",
                        slug, version, existing.verification_status, new, c["_file"],
                    )
                setattr(existing, f, new)
            if changed:
                report["updated"] += 1
                report.setdefault("updated_detail", []).append(f"{slug}: {', '.join(changed)}")
            else:
                report["unchanged"] += 1
            continue

        db.add(
            Construct(
                name=c["name"],
                description=c.get("description", ""),
                reference=c.get("citation", ""),
                items_json=json.dumps([str(i["text"]) for i in c["items"]]),
                reverse_flags_json=json.dumps([bool(i.get("reverse_scored", False)) for i in c["items"]]),
                is_seed=True,
                construct_slug=slug,
                version=version,
                item_hash=computed_hash,
                verification_status=c.get("verification_status", "needs_verification"),
                language=c.get("language", "en"),
                category=c.get("category", ""),
            )
        )
        report["inserted"] += 1

    db.commit()
    if report["errors"]:
        for e in report["errors"]:
            logger.error("construct library: %s", e)
        raise RuntimeError(
            "Construct library append-only violation(s): " + " | ".join(report["errors"])
        )
    logger.info("construct library sync: %s", report)
    return report


def construct_snapshot(construct: Construct) -> dict:
    """Immutable snapshot embedded in every run's metadata (design §10.1)."""
    items = json.loads(construct.items_json)
    flags = json.loads(construct.reverse_flags_json or "[]") or [False] * len(items)
    generation_raw = getattr(construct, "generation_json", "") or ""
    if construct.is_seed:
        source_type = "predefined"
    elif generation_raw:
        source_type = "llm_generated"  # AI-drafted, researcher-reviewed (ITEM_GENERATION.md)
    else:
        source_type = "user_custom"
    snapshot = {
        "construct_id": construct.construct_slug or f"custom_{construct.id[:8]}",
        "version": construct.version or 1,
        "name": construct.name,
        "language": construct.language or "en",
        "items": [
            {"text": t, "reverse_scored": bool(f)} for t, f in zip(items, flags)
        ],
        "item_hash": construct.item_hash or "",
        "citation": construct.reference or "",
        "verification_status": construct.verification_status or "draft",
        "source_type": source_type,
    }
    if generation_raw:
        # Cautionary provenance travels with every run, export, and repro
        # script that uses this construct (PI-approved wording lives in the
        # UI; this is the machine-readable half).
        snapshot["generation"] = json.loads(generation_raw)
        snapshot["items_source_note"] = (
            "Items were AI-generated (drafted by the model on the recorded date, "
            "then reviewed and saved by the researcher). They are not from a "
            "validated questionnaire; interpret scores accordingly."
        )
    return snapshot
