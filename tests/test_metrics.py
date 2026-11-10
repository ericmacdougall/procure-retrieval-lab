"""Known-answer tests for metrics and the paired bootstrap. Each assertion has a hand-computed value."""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import metrics as m


def test_recall_and_mrr_known():
    ranked = ["a", "b", "c", "d", "e"]
    assert m.recall_at_k(ranked, ["c"], 1) == 0.0
    assert m.recall_at_k(ranked, ["c"], 3) == 1.0
    assert m.recall_at_k(ranked, ["a", "z"], 5) == 0.5
    assert m.mrr_at_k(ranked, ["c"]) == 1 / 3
    assert m.mrr_at_k(ranked, ["z"]) == 0.0
    assert m.mrr_at_k(ranked, ["c"], k=2) == 0.0
    assert m.recall_at_k(ranked, [], 5) is None


def test_ndcg_known():
    # gold at rank 2 only: dcg = 1/log2(3); ideal = 1
    v = m.ndcg_at_k(["x", "g", "y"], ["g"], 10)
    assert abs(v - 1 / math.log2(3)) < 1e-12
    # two gold docs at ranks 1 and 3: dcg = 1 + 1/log2(4) = 1.5, ideal = 1 + 1/log2(3)
    v2 = m.ndcg_at_k(["g1", "x", "g2"], ["g1", "g2"], 10)
    assert abs(v2 - 1.5 / (1 + 1 / math.log2(3))) < 1e-12
    assert m.ndcg_at_k(["g"], ["g"], 10) == 1.0


def test_wilson_known():
    lo, hi = m.wilson(5, 10)
    assert abs(lo - 0.2366) < 1e-3 and abs(hi - 0.7634) < 1e-3
    lo, hi = m.wilson(0, 10)
    assert lo == 0.0 or abs(lo) < 1e-12
    assert abs(hi - 0.2775) < 1e-3
    lo, hi = m.wilson(12, 12)
    assert abs(lo - 0.7575) < 1e-3 and hi > 0.999


def test_paired_bootstrap_detects_and_rejects():
    r = np.random.RandomState(1)
    base = r.binomial(1, 0.5, 400).astype(float)
    better = base.copy()
    flip = r.choice(np.where(base == 0)[0], 60, replace=False)
    better[flip] = 1.0                     # +60/400 = +0.15 exactly
    d, lo, hi, p = m.paired_bootstrap(better, base, n_boot=2000, seed=3)
    assert abs(d - 0.15) < 1e-12 and lo > 0.10 and hi < 0.20 and p < 0.01
    d, lo, hi, p = m.paired_bootstrap(base, base, n_boot=2000, seed=3)
    assert d == 0.0 and lo == 0.0 and hi == 0.0


def test_paired_bootstrap_is_paired_and_seeded():
    a = np.array([1, 0, 1, 0, 1, 1, 0, 0.0] * 10)
    b = np.array([0, 0, 1, 1, 1, 0, 0, 1.0] * 10)
    r1 = m.paired_bootstrap(a, b, n_boot=500, seed=7)
    r2 = m.paired_bootstrap(a, b, n_boot=500, seed=7)
    assert r1 == r2
    # swapping the systems negates the interval exactly (same indices are used for both)
    s = m.paired_bootstrap(b, a, n_boot=500, seed=7)
    assert abs(s[0] + r1[0]) < 1e-12 and abs(s[1] + r1[2]) < 1e-12 and abs(s[2] + r1[1]) < 1e-12


def test_bootstrap_ci_small_n_is_wide():
    x = np.array([1.0] * 8 + [0.0] * 4)      # 12-question benchmark at 2/3
    mean, lo, hi = m.bootstrap_ci(x, n_boot=5000, seed=0)
    assert abs(mean - 8 / 12) < 1e-12 and hi - lo > 0.4


def test_auroc_and_abstention():
    assert m.auroc([0.9, 0.8], [0.1, 0.2]) == 1.0
    assert m.auroc([0.1], [0.9]) == 0.0
    assert m.auroc([0.5], [0.5]) == 0.5
    res = m.abstention([0.1, 0.2, 0.9, 0.8], [False, False, True, True], 0.5)
    assert res["abstain_precision"] == 1.0 and res["abstain_recall"] == 1.0 and res["answerable_coverage"] == 1.0
    assert 0.2 < m.best_tau([0.1, 0.2, 0.9, 0.8], [False, False, True, True]) <= 0.8
