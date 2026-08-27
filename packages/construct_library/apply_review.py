#!/usr/bin/env python3
"""Apply the 2026-08-25 construct library review to the YAML library (spec 0007).

Noor Skhiri reviewed all 525 items across the 94 constructs, checking wording,
reverse keying, subscale grouping, and citation for each. This script turns that
review file into library changes, deterministically and re-runnably.

What lands where is decided by the item hash (see validate_constructs.item_hash),
which covers language, version, item text, item order, and reverse flags:

  * a change to any of those creates a NEW version file (append-only, spec 0004) -
    the old version file is left byte-identical so runs that used it still resolve;
  * everything else (verification_status, citation, source_url, questionnaire,
    review provenance) is outside the hash and is edited in place.

Corrected item text and replacement URLs are hand-specified in the tables below
rather than parsed out of the reviewer's free-text notes: the notes mix the
correction with commentary, and a bad regex here would silently corrupt a
validated scale. The reverse-flag flips ARE read from the sheet, because that
column is a clean Y/N.

Usage:
    python packages/construct_library/apply_review.py            # dry run
    python packages/construct_library/apply_review.py --write    # rewrite YAML
Then: python packages/construct_library/validate_constructs.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import openpyxl
import yaml

HERE = Path(__file__).parent
CONSTRUCTS = HERE / "constructs"
REVIEW_XLSX = HERE / "reviews" / "CCR_construct_library_review_2026-08-25.xlsx"

REVIEWER = "Noor Skhiri"
REVIEW_DATE = "2026-08-25"

# Constructs whose remaining findings need a PI decision (spec 0007 Non-goals).
# They still receive their uncontroversial reverse-flag fixes; they just do not
# graduate to `verified`.
PENDING = {
    "ipip_50_item_big_five_factor_markers_agreeableness",
    "ipip_50_item_big_five_factor_markers_conscientiousness",
    "ipip_50_item_big_five_factor_markers_emotional_stability_neuroticism",
    "ipip_50_item_big_five_factor_markers_extraversion",
    "ipip_50_item_big_five_factor_markers_intellect_imagination",
    "k10",
}
PENDING_NOTE = {
    "k10": (
        "Items are stored as bare fragments; reviewer flags that each should carry the "
        "source stem 'During the last 30 days, about how often did you feel'. Pending PI "
        "decision (spec 0007)."
    ),
}
IPIP_NOTE = (
    "Reviewer confirms wording matches the source apart from the leading 'I' that CCR "
    "adds to IPIP item stems; whether to keep that prefix is pending a PI decision "
    "(spec 0007). Reverse-scoring corrections from the review are applied."
)

# item_id -> corrected text, transcribed from the reviewer's notes.
WORDING_FIX = {
    "adult_hope_scale_pathways_6":
        "I can think of many ways to get the things in life that are important to me.",
    "bas_2_8":
        "My behavior reveals my positive attitude toward my body; for example, I walk "
        "holding my head high and smiling.",
    "cage_questionnaire_1":
        "Have you ever felt you should Cut down on your drinking?",
    "hi_3":
        'I often do "my own thing."',
    "mfq_2_proportionality_3":
        "I think people who are more hardworking should end up with more money.",
    "fair_3":
        "Whether or not some people were treated differently from others.",
    "mspss_significant_other_2":
        "There is a special person with whom I can share joys and sorrows.",
    "shs_2":
        "Compared to most of my peers, I consider myself:",
    "team_psychological_safety_scale_4":
        "It is safe to take a risk in this team.",
}

# One item moves subscale per the SCS-SF coding key. It is renumbered into the
# destination construct's own id convention ({construct}_{source item number});
# it is still SCS-SF item 1, and the review file records where it came from.
SUBSCALE_MOVE = {
    "from": "scs_sf_self_judgment",
    "to": "scs_sf_over_identification",
    "item_id": "scs_sf_self_judgment_1",
    "new_item_id": "scs_sf_over_identification_1",
    "insert_at": 0,
}
SUBSCALE_MOVE_NOTE = (
    "SCS-SF item 1 ('When I fail at something important to me...') moves from "
    "Self-judgment to Over-identification per the source coding key, and is renumbered "
    "to match this construct's item ids (spec 0007)."
)

# Replacement source URLs supplied by the reviewer. PsycNET links arrived with an
# `auth_token` query parameter: that is a per-session credential which expires and
# must not be committed, so it is stripped and the base URL kept (the citation DOI
# stays the durable pointer).
SOURCE_URL_FIX = {
    "cbi_client_related_burnout": "https://emerge.ucsd.edu/r_2qfb6wi4uepyugd/",
    "cbi_personal_burnout": "https://emerge.ucsd.edu/r_2qfb6wi4uepyugd/",
    "cbi_work_related_burnout": "https://emerge.ucsd.edu/r_2qfb6wi4uepyugd/",
    "flourishing_scale": "https://eddiener.com/wp-content/uploads/2024/09/Flourishing-Scale.pdf",
    "grit_s_consistency_of_interests":
        "https://www.dropbox.com/scl/fi/5fw2nbvvswu6jfb/8-item-Grit-4.pdf?rlkey=htfr2ngc17y027uv9ebnj53zm&dl=0",
    "grit_s_perseverance_of_effort":
        "https://www.dropbox.com/scl/fi/5fw2nbvvswu6jfb/8-item-Grit-4.pdf?rlkey=htfr2ngc17y027uv9ebnj53zm&dl=0",
    "team_psychological_safety_scale":
        "https://novopsych.com/wp-content/uploads/2025/08/TPS-7-questionnaire.pdf",
    "dirty_dozen_machiavellianism": "https://psycnet.apa.org/fulltext/2010-10892-021.pdf",
    "dirty_dozen_narcissism": "https://psycnet.apa.org/fulltext/2010-10892-021.pdf",
    "dirty_dozen_psychopathy": "https://psycnet.apa.org/fulltext/2010-10892-021.pdf",
    "lot_r": "https://psycnet.apa.org/fulltext/1995-07978-001.pdf",
    "collectivism_horizontal": "https://psycnet.apa.org/fulltext/1997-38342-009.pdf",
    "individualism_horizontal": "https://psycnet.apa.org/fulltext/1997-38342-009.pdf",
}

# Citations the reviewer marked incomplete. Only the DOI she supplied verbatim is
# added; nothing is looked up or inferred.
CITATION_FIX = {
    "satisfaction_with_life":
        "Diener, E., Emmons, R. A., Larsen, R. J., & Griffin, S. (1985). The Satisfaction "
        "with Life Scale. Journal of Personality Assessment, 49(1), 71-75. "
        "https://doi.org/10.1207/s15327752jpa4901_13",
    "collectivism_horizontal":
        "Triandis, H. C., & Gelfand, M. J. (1998). Converging measurement of horizontal and "
        "vertical individualism and collectivism. Journal of Personality and Social "
        "Psychology, 74(1), 118-128. https://doi.org/10.1037/0022-3514.74.1.118",
    "individualism_horizontal":
        "Triandis, H. C., & Gelfand, M. J. (1998). Converging measurement of horizontal and "
        "vertical individualism and collectivism. Journal of Personality and Social "
        "Psychology, 74(1), 118-128. https://doi.org/10.1037/0022-3514.74.1.118",
}

QUESTIONNAIRE_FIX = {
    "collectivism_horizontal": "Horizontal and Vertical Individualism and Collectivism Scale",
    "individualism_horizontal": "Horizontal and Vertical Individualism and Collectivism Scale",
}

# Gaps the reviewer reported without a replacement: recorded, never guessed at.
REVIEW_NOTE = {
    "bas_2": "Reviewer could not reach the recorded source URL; wording checked against the "
             "publisher PDF. A working source link is still needed.",
    "cage_questionnaire": "Citation is correct but the recorded source URL is no longer "
                          "accessible; a working source link is still needed.",
    "mfq_care": "Citation is correct; no source URL on file yet.",
    "mfq_fairness": "Citation is correct; no source URL on file yet.",
    "lot_r": "The scale's 4 filler items are correctly excluded from this construct; they are "
             "not scored in the source.",
    "cbi_work_related_burnout": "Reviewer notes the source numbers these items 7 to 13.",
}


def load_review() -> dict:
    """Read the reviewer's sheet. Returns {item_id: should_be_reverse_scored}."""
    ws = openpyxl.load_workbook(REVIEW_XLSX, data_only=True)["Items"]
    hdr = [c.value for c in ws[1]]
    idx = {h: i for i, h in enumerate(hdr) if h}
    flags = {}
    for r in ws.iter_rows(min_row=2, values_only=True):
        if not r[0]:
            continue
        item_id = str(r[idx["item_id"]]).strip()
        flags[item_id] = str(r[idx["REVERSE-SCORED? (Y/N)"]] or "").strip().upper() == "Y"
    return flags


def dump(path: Path, data: dict, header: str) -> None:
    body = yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100,
                          default_flow_style=False)
    path.write_text(header + body)


def main() -> int:
    write = "--write" in sys.argv
    if not REVIEW_XLSX.exists():
        print(f"Review file not found: {REVIEW_XLSX}")
        return 1

    review_flags = load_review()
    files = sorted(CONSTRUCTS.glob("*.yaml"))
    plan = {"new_version": [], "in_place": [], "unchanged": []}

    for f in files:
        c = yaml.safe_load(f.read_text())
        cid = c["construct_id"]
        if int(c["version"]) != 1:
            continue  # already-versioned output from a previous run

        items = [dict(i) for i in c["items"]]

        # --- item-level changes (these move the hash, so they need a new version)
        changed_items = False
        for it in items:
            iid = it["item_id"]
            if iid in WORDING_FIX and it["text"] != WORDING_FIX[iid]:
                it["text"] = WORDING_FIX[iid]
                changed_items = True
            if iid in review_flags and bool(it.get("reverse_scored", False)) != review_flags[iid]:
                it["reverse_scored"] = review_flags[iid]
                changed_items = True

        src, dst = SUBSCALE_MOVE["from"], SUBSCALE_MOVE["to"]
        move_id, new_id = SUBSCALE_MOVE["item_id"], SUBSCALE_MOVE["new_item_id"]
        if cid == src and any(i["item_id"] == move_id for i in items):
            items = [i for i in items if i["item_id"] != move_id]
            changed_items = True
        elif cid == dst and not any(i["item_id"] == new_id for i in items):
            donor = yaml.safe_load((CONSTRUCTS / f"{src}.yaml").read_text())
            incoming = next(dict(i) for i in donor["items"] if i["item_id"] == move_id)
            incoming["reverse_scored"] = review_flags.get(move_id, incoming.get("reverse_scored", False))
            incoming["item_id"] = new_id
            items.insert(SUBSCALE_MOVE["insert_at"], incoming)
            changed_items = True

        # --- metadata (outside the hash: edited in place on whichever file is live)
        live = dict(c)
        if changed_items:
            live["version"] = 2
            live["items"] = items
        status = "needs_verification" if cid in PENDING else "verified"
        live["verification_status"] = status
        if cid in SOURCE_URL_FIX:
            live["source_url"] = SOURCE_URL_FIX[cid]
        if cid in CITATION_FIX:
            live["citation"] = CITATION_FIX[cid]
        if cid in QUESTIONNAIRE_FIX:
            live["questionnaire"] = QUESTIONNAIRE_FIX[cid]
        if "reverse_flags_source" in live or changed_items:
            live["reverse_flags_source"] = f"reviewed_{REVIEW_DATE}_{REVIEWER.lower().replace(' ', '_')}"

        note = REVIEW_NOTE.get(cid) or PENDING_NOTE.get(cid)
        if cid in PENDING and cid.startswith("ipip_"):
            note = IPIP_NOTE
        if cid in (src, dst):
            note = f"{note} {SUBSCALE_MOVE_NOTE}".strip() if note else SUBSCALE_MOVE_NOTE
        review = {"reviewer": REVIEWER, "date": REVIEW_DATE,
                  "outcome": "verified" if status == "verified" else "pending_pi_decision"}
        if note:
            review["notes"] = note
        live["review"] = review
        # keep `items` last for readability
        live["items"] = live.pop("items")

        if changed_items:
            plan["new_version"].append(cid)
            if write:
                # v1 stays byte-identical except for being marked superseded:
                # its items are the pre-review ones and must never read as verified.
                old = dict(c)
                old["verification_status"] = "archived"
                old["review"] = {"reviewer": REVIEWER, "date": REVIEW_DATE,
                                 "outcome": "superseded_by_version_2"}
                old["items"] = old.pop("items")
                dump(f, old,
                     "# Superseded by version 2 (spec 0007). Kept so runs that used this\n"
                     "# version still resolve; never edit a published version in place.\n")
                dump(CONSTRUCTS / f"{cid}_v2.yaml", live,
                     f"# Construct: versioned, append-only. Version 2 applies the "
                     f"{REVIEW_DATE} library review (spec 0007).\n")
        else:
            same = all(live.get(k) == c.get(k) for k in
                       ("verification_status", "source_url", "citation", "questionnaire"))
            (plan["unchanged"] if same and "review" in c else plan["in_place"]).append(cid)
            if write:
                dump(f, live,
                     "# Construct: versioned, append-only. Edits create a NEW version "
                     "(see registries rule).\n")

    live_total = len(plan["new_version"]) + len(plan["in_place"]) + len(plan["unchanged"])
    print(f"new version 2 files : {len(plan['new_version'])}")
    print(f"in-place metadata   : {len(plan['in_place'])}")
    print(f"already current     : {len(plan['unchanged'])}")
    print(f"\nlive constructs     : {live_total}")
    print(f"  verified          : {live_total - len(PENDING)}")
    print(f"  pending PI        : {len(PENDING)} -> {sorted(PENDING)}")
    if not write:
        print("\nDry run. Re-run with --write to apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
