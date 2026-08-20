"""Engine tests for anchor-vector (bipolar construct) scoring (spec 0006).

Runs the engine directly on the deterministic hash embedder, so the algebraic
identities (dot == pole difference, cosine == dot / ||AV||, pole-swap sign
flip, degenerate poles) are checked without torch.
"""

import numpy as np
import pytest

from app.ccr import HashEmbeddingBackend, run_ccr_anchored

TEXTS = [
    "I feel joyful and full of hope today",
    "everything is bleak and I am miserable",
    "a neutral sentence about the weather report",
    "pure delight and happiness surround me",
]
TARGET = ["I am happy", "life brings me joy", "I feel cheerful"]
OPPOSITE = ["I am sad", "life brings me sorrow", "I feel gloomy"]


def be():
    return HashEmbeddingBackend()


def test_dot_metric_equals_pole_difference():
    r = run_ccr_anchored(TEXTS, TARGET, OPPOSITE, be(), metric="dot")
    # T·AV = T·C - T·C_opp = target_score - opposite_score, exactly.
    assert np.allclose(r.anchor_scores, r.target_scores - r.opposite_scores, atol=1e-6)
    assert r.target_similarities.shape == (len(TEXTS), len(TARGET))
    assert r.opposite_similarities.shape == (len(TEXTS), len(OPPOSITE))
    assert r.metadata["similarity"] == "dot"
    assert r.metadata["n_target_items"] == 3 and r.metadata["n_opposite_items"] == 3


def test_cosine_is_dot_over_av_norm():
    dot = run_ccr_anchored(TEXTS, TARGET, OPPOSITE, be(), metric="dot")
    cos = run_ccr_anchored(TEXTS, TARGET, OPPOSITE, be(), metric="cosine")
    av_norm = cos.metadata["anchor_vector_norm"]
    assert av_norm > 0
    assert np.allclose(cos.anchor_scores * av_norm, dot.anchor_scores, atol=1e-4)
    # cosine of a unit vector with anything is bounded.
    assert np.all(cos.anchor_scores <= 1.0 + 1e-6)
    assert np.all(cos.anchor_scores >= -1.0 - 1e-6)


def test_swapping_poles_flips_sign():
    fwd = run_ccr_anchored(TEXTS, TARGET, OPPOSITE, be(), metric="dot")
    rev = run_ccr_anchored(TEXTS, OPPOSITE, TARGET, be(), metric="dot")
    assert np.allclose(fwd.anchor_scores, -rev.anchor_scores, atol=1e-6)
    cf = run_ccr_anchored(TEXTS, TARGET, OPPOSITE, be(), metric="cosine")
    cr = run_ccr_anchored(TEXTS, OPPOSITE, TARGET, be(), metric="cosine")
    assert np.allclose(cf.anchor_scores, -cr.anchor_scores, atol=1e-6)


def test_degenerate_poles_flagged_no_crash():
    r = run_ccr_anchored(TEXTS, TARGET, list(TARGET), be(), metric="cosine")
    assert r.degenerate is True
    assert r.metadata["degenerate_poles"] is True
    assert np.allclose(r.anchor_scores, 0.0)  # cosine falls back to 0 when AV ~ 0
    d = run_ccr_anchored(TEXTS, TARGET, list(TARGET), be(), metric="dot")
    assert np.allclose(d.anchor_scores, 0.0, atol=1e-6)  # target - target ~ 0


def test_unknown_metric_rejected():
    with pytest.raises(ValueError):
        run_ccr_anchored(TEXTS, TARGET, OPPOSITE, be(), metric="euclidean")


def test_empty_item_sets_rejected():
    with pytest.raises(ValueError):
        run_ccr_anchored(TEXTS, [], OPPOSITE, be())
    with pytest.raises(ValueError):
        run_ccr_anchored(TEXTS, TARGET, [], be())
