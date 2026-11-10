"""Metrics and statistics: document-level recall@k, MRR@10, nDCG@10, abstention, paired bootstrap, Wilson."""
import math
import numpy as np

KS = (1, 5, 10, 20)


def recall_at_k(ranked, gold, k):
    """Fraction of gold documents found in the top k (single gold: hit rate)."""
    g = set(gold)
    if not g:
        return None
    return len(g.intersection(ranked[:k])) / len(g)


def mrr_at_k(ranked, gold, k=10):
    g = set(gold)
    if not g:
        return None
    for i, d in enumerate(ranked[:k]):
        if d in g:
            return 1.0 / (i + 1)
    return 0.0


def ndcg_at_k(ranked, gold, k=10):
    g = set(gold)
    if not g:
        return None
    dcg = sum(1.0 / math.log2(i + 2) for i, d in enumerate(ranked[:k]) if d in g)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(min(len(g), k)))
    return dcg / idcg


def per_query(ranked, gold):
    out = dict()
    for k in KS:
        out["recall@%d" % k] = recall_at_k(ranked, gold, k)
    out["mrr@10"] = mrr_at_k(ranked, gold, 10)
    out["ndcg@10"] = ndcg_at_k(ranked, gold, 10)
    return out


def wilson(successes, n, z=1.959964):
    if n == 0:
        return (float("nan"), float("nan"))
    p = successes / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (centre - half, centre + half)


def bootstrap_ci(x, n_boot=10000, seed=0, alpha=0.05):
    """Percentile bootstrap CI of the mean of x."""
    x = np.asarray(x, dtype=np.float64)
    r = np.random.RandomState(seed)
    idx = r.randint(0, len(x), size=(n_boot, len(x)))
    means = x[idx].mean(axis=1)
    return (float(x.mean()), float(np.percentile(means, 100 * alpha / 2)), float(np.percentile(means, 100 * (1 - alpha / 2))))


def paired_bootstrap(a, b, n_boot=10000, seed=0, alpha=0.05):
    """Paired percentile bootstrap of mean(a - b): same resampled indices for both systems.
    Returns (mean diff, lo, hi, two-sided p ~ share of resamples crossing zero)."""
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    assert a.shape == b.shape
    d = a - b
    r = np.random.RandomState(seed)
    idx = r.randint(0, len(d), size=(n_boot, len(d)))
    means = d[idx].mean(axis=1)
    lo, hi = np.percentile(means, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    p = 2 * min((means <= 0).mean(), (means >= 0).mean())
    return (float(d.mean()), float(lo), float(hi), float(min(1.0, p)))


def auroc(pos, neg):
    """P(score_pos > score_neg) with ties 0.5. pos = answerable top scores, neg = no-answer top scores."""
    pos = np.asarray(pos, dtype=np.float64)
    neg = np.asarray(neg, dtype=np.float64)
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    gt = (pos[:, None] > neg[None, :]).mean()
    eq = (pos[:, None] == neg[None, :]).mean()
    return float(gt + 0.5 * eq)


def abstention(top_scores, answerable, tau):
    """Abstain when top score < tau. Returns precision/recall of abstaining on no-answer questions
    plus the answer-rate (coverage) on answerable ones."""
    s = np.asarray(top_scores, dtype=np.float64)
    a = np.asarray(answerable, dtype=bool)
    ab = s < tau
    tp = int((ab & ~a).sum())
    prec = tp / max(1, int(ab.sum()))
    rec = tp / max(1, int((~a).sum()))
    cov = float((~ab[a]).mean()) if a.any() else float("nan")
    return dict(abstain_precision=prec, abstain_recall=rec, answerable_coverage=cov, tau=float(tau))


def best_tau(top_scores, answerable):
    """Dev-only threshold: maximise balanced accuracy of the abstain decision."""
    s = np.asarray(top_scores, dtype=np.float64)
    a = np.asarray(answerable, dtype=bool)
    best = (-1.0, None)
    for t in np.unique(s):
        ab = s < t
        tpr = (ab & ~a).sum() / max(1, (~a).sum())
        tnr = (~ab & a).sum() / max(1, a.sum())
        ba = 0.5 * (tpr + tnr)
        if ba > best[0]:
            best = (ba, float(t))
    return best[1]
