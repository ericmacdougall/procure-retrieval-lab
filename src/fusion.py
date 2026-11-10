"""Fusion of ranked lists: reciprocal rank fusion and weighted min-max score fusion (doc level)."""


def rrf(lists, k=60, weights=None):
    """lists: list of ranked [(doc_id, score)] (best first). Returns fused [(doc_id, score)]."""
    acc = dict()
    for li, lst in enumerate(lists):
        w = 1.0 if weights is None else weights[li]
        for r, (d, _) in enumerate(lst):
            acc[d] = acc.get(d, 0.0) + w / (k + r + 1)
    return sorted(acc.items(), key=lambda x: -x[1])


def minmax(lst):
    if not lst:
        return dict()
    s = [x[1] for x in lst]
    lo, hi = min(s), max(s)
    span = (hi - lo) or 1.0
    return dict((d, (v - lo) / span) for d, v in lst)


def weighted(lists, weights):
    """Weighted sum of per-list min-max normalised scores; a doc missing from a list scores 0 there."""
    acc = dict()
    for lst, w in zip(lists, weights):
        for d, v in minmax(lst).items():
            acc[d] = acc.get(d, 0.0) + w * v
    return sorted(acc.items(), key=lambda x: -x[1])
